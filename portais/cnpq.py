import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import config, web_utils

def varrer(log, atualizar_tabela_func):
    nome = "CNPq - Chamadas Abertas"
    cfg = config.SITES_ESTATICOS[nome]
    log(f"===> Verificando portal estático: {nome}")
    
    try:
        resp = requests.get(cfg["url"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        html = BeautifulSoup(resp.text, "html.parser")
        chamadas = html.find_all(cfg["tag_titulo"])
        log(f"    -> Encontrados {len(chamadas)} itens na página base.")
        
        for ch in chamadas:
            txt_bruto = ch.get_text()
            paragrafo = ch.find_next("p")
            if paragrafo: 
                txt_bruto += " " + paragrafo.get_text()
            txt_normalizado = txt_bruto.lower()
            
            for palavra in config.PALAVRAS_CHAVE:
                palavra_limpa = palavra.lower()
                radical = palavra_limpa[:-1] if len(palavra_limpa) > 5 else palavra_limpa
                
                if radical in txt_normalizado:
                    log(f"    [✓] Termo '{palavra}' casou no CNPq!")
                    link = ch.find("a") if ch.name == cfg["tag_titulo"] else ch.find_next("a")
                    if link and link.has_attr("href"):
                        url_completa = urljoin(cfg["url"], link["href"])
                        log(f"        Acessando edital: {url_completa}")
                        if web_utils.processar_pagina_interna(url_completa, cfg["ignorar_links"], nome, log, palavra, atualizar_tabela_func):
                            break
    except Exception as e:
        log(f"    [X] Erro estatico {nome}: {e}")
