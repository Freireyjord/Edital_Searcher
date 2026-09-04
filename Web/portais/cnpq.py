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
        # Faz a requisição HTTP direta para a página de submissões do CNPq
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(URL_BASE, timeout=15, headers=headers)
        
        if resp.status_code != 200:
            log(f"    [X] Erro de conexão com o portal CNPq. Status: {resp.status_code}")
            return
            
        html = BeautifulSoup(resp.text, "html.parser")
        chamadas = html.find_all(TAG_TITULO)
        
        log(f"    [+] Total de chamadas localizadas no HTML: {len(chamadas)}")
        
        # Como o robô agora faz busca ampla, varremos todas as chamadas sem restrição de palavras-chave rígidas
        for ch in chamadas:
            # Localiza o link associado à chamada aberta
            link = ch.find("a") if ch.name == TAG_TITULO else ch.find_next("a")
            
            if link and link.has_attr("href"):
                url_completa = urljoin(URL_BASE, link["href"])
                
                # Envia o edital localizado para a rotina central de extração e salvamento
                web_utils.processar_pagina_interna(
                    url_completa, 
                    IGNORAR_LINKS, 
                    NOME_PORTAL, 
                    log, 
                    "Busca Ampla", 
                    None
                )
                
    except Exception as e:
        log(f"    [X] Erro crítico no processamento do portal {NOME_PORTAL}: {e}")
