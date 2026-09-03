import time, sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import config, web_utils

NOME_PORTAL = "Finep - Oportunidades"
URL_BASE = "https://www.finep.gov.br/oportunidades"
SELETOR_CARD = "tr"
MAX_PAGINAS = 10
IGNORAR_LINKS = []


def varrer(log, atualizar_tabela_func):
    log(f"\n===> Verificando portal dinâmico: {NOME_PORTAL}")
    
    nav = None
    try:
        opt_chrome = webdriver.ChromeOptions()
        opt_chrome.add_argument("--headless=new")
        opt_chrome.add_argument("--no-sandbox")
        opt_chrome.add_argument("--disable-dev-shm-usage")
        opt_chrome.add_argument("--disable-gpu")
        opt_chrome.add_argument("--remote-allow-origins=*")
        opt_chrome.add_argument("user-agent=Mozilla/5.0")
        
        from selenium.webdriver.chrome.service import Service as ChromeService
        servico = ChromeService()
        if getattr(sys, 'frozen', False): servico.creation_flags = 0x08000000
        nav = webdriver.Chrome(options=opt_chrome, service=servico)
    except Exception as err:
        log(f"    [⚠️] Falha Chrome: {err}. Tentando Edge...")
        try:
            from selenium.webdriver.edge.options import Options as EdgeOptions
            from selenium.webdriver.edge.service import Service as EdgeService
            opt_edge = EdgeOptions()
            opt_edge.add_argument("--headless=new")
            opt_edge.add_argument("--no-sandbox")
            opt_edge.add_argument("--disable-gpu")
            servico_edge = EdgeService()
            if getattr(sys, 'frozen', False): servico_edge.creation_flags = 0x08000000
            nav = webdriver.Edge(options=opt_edge, service=servico_edge)
        except Exception as e:
            log(f"    [X] Nenhum navegador localizado: {e}")
            return

    try:
        wait = WebDriverWait(nav, 30)
        ant = []
        nav.get(URL_BASE)
        
        for p_at in range(1, MAX_PAGINAS + 1):
            log(f"    -> Analisando e lendo a página {p_at} de {NOME_PORTAL}...")
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, SELETOR_CARD)))
                time.sleep(5)
                cards = nav.find_elements(By.XPATH, f"//{SELETOR_CARD}")
            except: break
            
            atuais = [c.text.strip() for c in cards if c.text.strip()]
            if p_at > 1 and (not atuais or atuais == ant): break
            ant = atuais
            
            urls_validas = {}
            for card in cards:
                try:
                    texto_card = card.text
                    if not texto_card: continue
                    for palavra in config.PALAVRAS_CHAVE:
                        radical = palavra.lower()[:-1] if len(palavra) > 5 else palavra.lower()
                        if radical in texto_card.lower():
                            link = card.find_element(By.TAG_NAME, "a")
                            url = link.get_attribute("href")
                            if url: urls_validas[urljoin(URL_BASE, url)] = palavra
                except: continue
                
            for url_u, termo in urls_validas.items():
                web_utils.processar_pagina_interna(url_u, IGNORAR_LINKS, NOME_PORTAL, log, termo, atualizar_tabela_func)
                
            if p_at < MAX_PAGINAS:
                try:
                    nav.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    selectors = ["ul.pagination button.page-link", "ul.pagination a", ".pagination li a"]
                    clicado = False
                    for sel_str in selectors:
                        botoes = nav.find_elements(By.CSS_SELECTOR, sel_str)
                        for b in botoes:
                            if b.text.strip() == str(p_at + 1):
                                nav.execute_script("arguments[0].click();", b)
                                clicado = True; break
                        if clicado: break
                    if not clicado: break
                    time.sleep(5)
                except: break
    finally:
        if nav: nav.quit()