import requests
from bs4 import BeautifulSoup
import re
import os
import time
import zipfile
from flask import Flask, send_file

# CONFIGURAÇÕES
usuario = "teste"  # Altere aqui o nome do usuário do Twitter
base_url = f"https://twitter.com/{usuario}"
imagem_regex = r"https://web\\.archive\\.org/web/\\d+im_/https://pbs\\.twimg\\.com/media/[^\"'\\s>]+"
output_folder = f"imagens_{usuario}"
zip_filename = f"imagens_{usuario}.zip"
sleep_time = 1
max_retentativas = 3
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Cria pasta se não existir
os.makedirs(output_folder, exist_ok=True)

app = Flask(__name__)

def buscar_capturas(url):
    cdx_url = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp,original,mimetype",
        "filter": "statuscode:200",
        "matchType": "prefix"
    }
    try:
        resposta = requests.get(cdx_url, params=params, headers=headers)
        resposta.raise_for_status()
        linhas = resposta.json()[1:]
        return [f"https://web.archive.org/web/{linha[0]}/{linha[1]}" for linha in linhas if "html" in linha[2]]
    except Exception as e:
        print(f"Erro na API CDX: {e}")
        return []

def extrair_links_imagem(html):
    return set(re.findall(imagem_regex, html))

def baixar_imagem(url, nome_arquivo):
    for tentativa in range(max_retentativas):
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            if resp.status_code == 200:
                with open(nome_arquivo, "wb") as f:
                    f.write(resp.content)
                print(f"Imagem salva: {nome_arquivo}")
                return
        except Exception as e:
            print(f"Tentativa {tentativa+1} falhou: {e}")
        time.sleep(2)
    print(f"Falha ao baixar imagem: {url}")

def coletar_e_salvar():
    capturas = buscar_capturas(base_url)
    imagens_encontradas = set()
    for url in capturas:
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            if resp.status_code == 200:
                novas = extrair_links_imagem(resp.text) - imagens_encontradas
                imagens_encontradas.update(novas)
        except Exception as e:
            print(f"Erro processando captura: {e}")
        time.sleep(sleep_time)

    for idx, img_url in enumerate(sorted(imagens_encontradas), 1):
        nome_arquivo = os.path.join(output_folder, f"imagem_{idx}.jpg")
        if not os.path.exists(nome_arquivo):
            baixar_imagem(img_url, nome_arquivo)
            time.sleep(sleep_time)

    # Gera ZIP
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, _, files in os.walk(output_folder):
            for file in files:
                path = os.path.join(root, file)
                zipf.write(path, arcname=file)
    print("ZIP gerado.")

@app.route("/download")
def download():
    return send_file(zip_filename, as_attachment=True)

if __name__ == "__main__":
    coletar_e_salvar()
    app.run(host="0.0.0.0", port=8000)
