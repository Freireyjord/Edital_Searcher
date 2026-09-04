import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import config
import web_utils

NOME_PORTAL = "Finep - Oportunidades"
URL_BASE = "https://www.finep.gov.br/oportunidades"
MAX_PAGINAS = 10
IGNORAR_LINKS = ["/duvidas-frequentes", "/contato", "/login", "/noticias"]


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
        opt_chrome.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        from selenium.webdriver.chrome.service import Service as ChromeService
        servico = ChromeService()
        if getattr(sys, 'frozen', False):
            servico.creation_flags = 0x08000000
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
            opt_edge.add_argument("--window-size=1920,1080")
            servico_edge = EdgeService()
            if getattr(sys, 'frozen', False):
                servico_edge.creation_flags = 0x08000000
            nav = webdriver.Edge(options=opt_edge, service=servico_edge)
        except Exception as e:
            log(f"    [X] Nenhum navegador localizado: {e}")
            return

    try:
        nav.get(URL_BASE)
        # Pausa inicial maior para garantir que os scripts dinâmicos da FINEP sejam executados
        time.sleep(6)

        palavras_chave = getattr(config, "PALAVRAS_CHAVE", [""])
        if not palavras_chave:
            palavras_chave = [""]

        for p_at in range(1, MAX_PAGINAS + 1):
            log(f"    -> Analisando e lendo a página {p_at} de {NOME_PORTAL}...")

            # Rolagem progressiva para forçar o carregamento dinâmico (lazy loading)
            nav.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
            time.sleep(1)
            nav.execute_script("window.scrollTo(0, (document.body.scrollHeight / 3) * 2);")
            time.sleep(1)
            nav.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Extração do HTML
            soup = BeautifulSoup(nav.page_source, "html.parser")
            links_a = soup.find_all("a", href=True)
            urls_encontradas = set()

            # LOG DE DEPURAÇÃO: Imprime as primeiras 15 URLs encontradas na página
            todos_hrefs = [a["href"] for a in links_a if a["href"].strip()]
            log(f"    [DEBUG] Total de tags <a> encontradas: {len(links_a)}")
            log(f"    [DEBUG] Amostra de hrefs: {todos_hrefs[:10]}")

            for a in links_a:
                href = a["href"].strip()
                texto_link = a.get_text(strip=True).lower()
                href_lower = href.lower()

                if any(ign in href_lower for ign in IGNORAR_LINKS) or href in ["#", ""] or href.startswith("javascript:"):
                    continue

                # Padrão amplo para capturar qualquer link de edital/chamada
                eh_edital = (
                    "chamada" in href_lower 
                    or "oportunidade" in href_lower 
                    or "edital" in href_lower
                    or "/materia/" in href_lower
                )

                if eh_edital:
                    url_completa = urljoin("https://www.finep.gov.br", href)
                    
                    # Evita adicionar a própria página de listagem
                    if url_completa.rstrip("/") != URL_BASE.rstrip("/"):
                        urls_encontradas.add((url_completa, "Geral"))

                    for palavra in palavras_chave:
                        termo = palavra.strip()
                        termo_lower = termo.lower()

                        if not termo or termo_lower in ["todos", "tudo"] or termo_lower in texto_link or termo_lower in url_completa.lower():
                            urls_encontradas.add((url_completa, termo if termo else "Geral"))
                            break
                        else:
                            urls_encontradas.add((url_completa, termo))

            if not urls_encontradas:
                log(f"    [i] Nenhum edital localizado na página {p_at}.")
                if p_at > 1:
                    break
            else:
                log(f"    [+] Encontrados {len(urls_encontradas)} links de editais na página {p_at}.")

            # Envia para sanitização e salvamento no Supabase
            for url_u, termo in urls_encontradas:
                web_utils.processar_pagina_interna(
                    url_u,
                    IGNORAR_LINKS,
                    NOME_PORTAL,
                    log,
                    termo,
                    atualizar_tabela_func
                )

            # Paginação via Selenium
            if p_at < MAX_PAGINAS:
                try:
                    botoes_prox = nav.find_elements(
                        By.XPATH,
                        f"//a[text()='{p_at + 1}'] | //a[contains(text(), 'Próx')] | //li[contains(@class, 'next')]/a | //button[contains(@class, 'next')]"
                    )

                    if botoes_prox and botoes_prox[0].is_displayed():
                        nav.execute_script("arguments[0].click();", botoes_prox[0])
                        time.sleep(4)
                    else:
                        log(f"    [i] Fim das páginas alcançado na página {p_at}.")
                        break
                except Exception as e_pag:
                    log(f"    [X] Fim da paginação: {e_pag}")
                    break
    finally:
        if nav:
            nav.quit()