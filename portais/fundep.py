import time, sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import config, web_utils

def varrer(log, atualizar_tabela_func):
    nome = "Fundep - Projetos"
    cfg = config.SITES_DINAMICOS[nome]
    log(f"\n===> Verificando portal dinâmico: {nome}")
    
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
        nav.get(cfg["url"])
        
        for p_at in range(1, cfg["max_paginas"] + 1):
            log(f"    -> Analisando e lendo a página {p_at} de {nome}...")
            sel = (By.CSS_SELECTOR, cfg["seletor_card"])
            try:
                wait.until(EC.presence_of_element_located(sel))
                time.sleep(5)
                cards = nav.find_elements(*sel)
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
                            if url: urls_validas[urljoin(cfg["url"], url)] = palavra
                except: continue
                
            for url_u, termo in urls_validas.items():
                web_utils.processar_pagina_interna(url_u, cfg["ignorar_links"], nome, log, termo, atualizar_tabela_func)
                
            if p_at < cfg["max_paginas"]:
                try:
                    nav.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    xpath = f"//ul[contains(@class, 'MuiPagination-ul')]//button[text()='{p_at + 1}']"
                    btn = nav.find_element(By.XPATH, xpath)
                    nav.execute_script("arguments[0].click();", btn)
                    time.sleep(5)
                except: break
    finally:
        if nav: nav.quit()
