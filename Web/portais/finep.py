import time, sys, re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import config, web_utils

NOME_PORTAL = "Finep - Oportunidades"
URL_BASE = "https://www.finep.gov.br/oportunidades"
MAX_PAGINAS = 10
IGNORAR_LINKS = ["/duvidas-frequentes", "/contato", "/login", "/noticias"]

def normalizar_href(valor_href):
    """Recebe o atributo href e devolve somente uma URL válida."""
    if not valor_href: return ""
    href = str(valor_href).strip()
    if "<a " in href.lower():
        correspondencia = re.search(r'href=["\']([^"\']+)["\']', href, flags=re.IGNORECASE)
        if correspondencia: href = correspondencia.group(1)
    return href

def varrer(log, atualizar_tabela_func):
    log(f"\n===> Verificando portal dinâmico: {NOME_PORTAL}")
    nav = None
    try:
        opt_chrome = webdriver.ChromeOptions()
        opt_chrome.add_argument("--headless=new")
        opt_chrome.add_argument("--no-sandbox")
        opt_chrome.add_argument("--disable-dev-shm-usage")
        opt_chrome.add_argument("--disable-gpu")
        opt_chrome.add_argument("--window-size=1920,1080")
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
        nav.get(URL_BASE)
        time.sleep(6)

        for p_at in range(1, MAX_PAGINAS + 1):
            log(f"    -> Analisando e lendo a página {p_at} de {NOME_PORTAL}...")

            # Rolagem para forçar lazy loading
            nav.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            nav.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            soup = BeautifulSoup(nav.page_source, "html.parser")
            links_a = soup.find_all("a", href=True)
            urls_encontradas = set()

            for a in links_a:
                href = normalizar_href(a.get("href"))
                if not href: continue

                href_lower = href.lower()
                if any(ign in href_lower for ign in IGNORAR_LINKS) or href in ["#", ""] or href.startswith("javascript:"):
                    continue

                # Captura ampla de editais, chamadas ou matérias internas
                eh_edital = ("chamada" in href_lower or "oportunidade" in href_lower or "edital" in href_lower or "/materia/" in href_lower)

                if eh_edital:
                    url_completa = urljoin("https://finep.gov.br", href)
                    if not url_completa.startswith(("http://", "https://")) or "<" in url_completa or ">" in url_completa:
                        continue
                    if url_completa.rstrip("/") != URL_BASE.rstrip("/"):
                        urls_encontradas.add((url_completa, "Busca Ampla"))

            log(f"    [+] Encontrados {len(urls_encontradas)} links potenciais na página {p_at}.")

            for url_u, termo in urls_encontradas:
                web_utils.processar_pagina_interna(url_u, IGNORAR_LINKS, NOME_PORTAL, log, termo, None)

            if p_at < MAX_PAGINAS:
                try:
                    pagina_seguinte = p_at + 1
                    url_antes = nav.current_url
                    html_antes = nav.page_source

                    # Procura o botão numérico da próxima página
                    seletor = (By.XPATH, f"//a[normalize-space()='{pagina_seguinte}'] | //button[normalize-space()='{pagina_seguinte}']")
                    elementos = nav.find_elements(*seletor)
                    
                    botao_proximo = None
                    for elemento in elementos:
                        if elemento.is_displayed() and elemento.is_enabled():
                            botao_proximo = elemento
                            break

                    if not botao_proximo: break

                    nav.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_proximo)
                    time.sleep(1)
                    nav.execute_script("arguments[0].click();", botao_proximo)

                    WebDriverWait(nav, 20).until(lambda d: d.current_url != url_antes or d.page_source != html_antes)
                    time.sleep(3)
                except:
                    break
    finally:
        if nav: nav.quit()
