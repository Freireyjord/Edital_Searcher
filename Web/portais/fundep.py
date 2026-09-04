import time, sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import config, web_utils

NOME_PORTAL = "Fundep - Projetos"
URL_BASE = "https://fundep.ufmg.br/projetos"
SELETOR_CARD = "div[class*='MuiGrid-item'], .MuiGrid-item, div.MuiBox-root div[role='group']"
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
            sel = (By.CSS_SELECTOR, SELETOR_CARD)

            try:
                wait.until(EC.presence_of_element_located(sel))
                time.sleep(5)
                cards = nav.find_elements(*sel)
            except Exception as erro_cards:
                log(f"    [X] Erro ao localizar os cards da página {p_at}: {erro_cards}")
                break

            atuais = [card.text.strip() for card in cards if card.text.strip()]
            if p_at > 1 and (not atuais or atuais == ant):
                break
            ant = atuais
            
            urls_validas = {}
            for card in cards:
                try:
                    if not card.text.strip(): continue
                    link = card.find_element(By.TAG_NAME, "a")
                    url = link.get_attribute("href")
                    if url: 
                        urls_validas[urljoin(URL_BASE, url)] = "Busca Ampla"
                except: 
                    continue
                
            log(f"    [+] Encontrados {len(urls_validas)} links de editais na página {p_at}.")

            for url_u, termo in urls_validas.items():
                web_utils.processar_pagina_interna(url_u, IGNORAR_LINKS, NOME_PORTAL, log, termo, None)
                
            if p_at < MAX_PAGINAS:
                try:
                    pagina_seguinte = p_at + 1
                    nav.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)

                    seletor_btn = (By.XPATH, f"//button[normalize-space()='{pagina_seguinte}'] | //button[@aria-label='Ir para a página {pagina_seguinte}']")
                    elementos = nav.find_elements(*seletor_btn)
                    
                    botao_proximo = None
                    for elemento in elementos:
                        if elemento.is_displayed() and elemento.is_enabled():
                            botao_proximo = elemento
                            break

                    if not botao_proximo: break

                    nav.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_proximo)
                    time.sleep(1)
                    nav.execute_script("arguments[0].click();", botao_proximo)
                    time.sleep(3)
                except:
                    break
    finally:
        if nav: nav.quit()
