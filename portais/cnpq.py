import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import config, web_utils

NOME_PORTAL = "CNPq - Chamadas Abertas"
URL_BASE = "https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao"
TAG_TITULO = "h4"
IGNORAR_LINKS = []

def varrer(log, atualizar_tabela_func):
    log(f"===> Verificando portal estático: {NOME_PORTAL}")
    try:
        resp = requests.get(URL_BASE, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        html = BeautifulSoup(resp.text, "html.parser")
        chamadas = html.find_all(TAG_TITULO)
        
        for ch in chamadas:
            txt_bruto = ch.get_text()
            paragrafo = ch.find_next("p")
            if paragrafo: 
                txt_bruto += " " + paragrafo.get_text()
            txt_normalizado = txt_bruto.lower()
            
            for palavra in config.PALAVRAS_CHAVE:
                radical = palavra.lower()[:-1] if len(palavra) > 5 else palavra.lower()
                if radical in txt_normalizado:
                    link = ch.find("a") if ch.name == TAG_TITULO else ch.find_next("a")
                    if link and link.has_attr("href"):
                        url_completa = urljoin(URL_BASE, link["href"])
                        web_utils.processar_pagina_interna(
                            url_completa, IGNORAR_LINKS, NOME_PORTAL, log, palavra, atualizar_tabela_func
                        )
                        break
    except Exception as e:
        log(f"    [X] Erro no portal {NOME_PORTAL}: {e}")