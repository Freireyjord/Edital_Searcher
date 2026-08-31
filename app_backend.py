import time, requests, traceback, unicodedata, sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config, web_utils, processador

def remover_acentos(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def rodar_automacao_unificada(callback_fim, log):
    try:
        log("[App Backend] Iniciando varredura nativa unificada de portais...")

        # --- PARTE 1: PORTAIS ESTÁTICOS (CNPq) ---
        for nome, cfg in config.SITES_ESTATICOS.items():
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
                                
                                # >>> CORREÇÃO AQUI: Passando a variável 'palavra' no final <<<
                                if web_utils.processar_pagina_interna(url_completa, cfg["ignorar_links"], nome, log, palavra): 
                                    break

            except Exception as e: 
                log(f"    [X] Erro estatico {nome}: {e}")


                # --- PARTE 2: PORTAIS DINÂMICOS (Fundep e Finep) ---
        for nome, cfg in config.SITES_DINAMICOS.items():
            log(f"\n===> Verificando portal dinâmico: {nome}")
            nav = None
            
            try:
                # 🌐 TENTATIVA 1: CONFIGURAÇÃO E EXECUÇÃO DO GOOGLE CHROME
                opt_chrome = webdriver.ChromeOptions()
                opt_chrome.add_argument("--headless=new")
                opt_chrome.add_argument("--no-sandbox")
                opt_chrome.add_argument("--disable-dev-shm-usage")
                opt_chrome.add_argument("--disable-gpu")
                opt_chrome.add_argument("--remote-allow-origins=*")
                opt_chrome.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                
                # Injeta a proteção de janela para evitar travamentos com --windowed
                from selenium.webdriver.chrome.service import Service as ChromeService
                servico_chrome = ChromeService()
                if getattr(sys, 'frozen', False):
                    servico_chrome.creation_flags = 0x08000000
                
                nav = webdriver.Chrome(options=opt_chrome, service=servico_chrome)
                log("    [🌐] Navegador Google Chrome iniciado com sucesso.")
                
            except Exception as err_chrome:
                log(f"    [⚠️] Não foi possível iniciar o Chrome. Motivo: {err_chrome}")
                log("    [🔄] Acionando contingência: Tentando abrir com Microsoft Edge...")
                
                try:
                    # 🌐 TENTATIVA 2: CONFIGURAÇÃO E EXECUÇÃO DO MICROSOFT EDGE (CORRIGIDO)
                    from selenium.webdriver.edge.options import Options as EdgeOptions
                    from selenium.webdriver.edge.service import Service as EdgeService
                    
                    opt_edge = EdgeOptions()
                    opt_edge.add_argument("--headless=new") # Força execução oculta estável
                    opt_edge.add_argument("--no-sandbox")
                    opt_edge.add_argument("--disable-dev-shm-usage")
                    opt_edge.add_argument("--disable-gpu")
                    opt_edge.add_argument("--remote-allow-origins=*")
                    opt_edge.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                    
                    # CORREÇÃO ESSENCIAL: Cria o serviço nativo ocultando a janela invisível do Edge Driver
                    servico_edge = EdgeService()
                    if getattr(sys, 'frozen', False):
                        servico_edge.creation_flags = 0x08000000 # Impede o msedgedriver.exe de quebrar
                        
                    nav = webdriver.Edge(options=opt_edge, service=servico_edge)
                    log("    [🌐] Navegador Microsoft Edge iniciado com sucesso de forma portátil.")
                    
                except Exception as err_edge:
                    log(f"    [X] Erro Crítico: Nenhum navegador compatível (Chrome/Edge) pôde ser inicializado nesta máquina. {err_edge}")
                    continue 

            wait = WebDriverWait(nav, 30)
            ant = []
            try:
                nav.get(cfg["url"])
                for p_at in range(1, cfg["max_paginas"] + 1):
                    log(f"    -> Analisando e lendo a página {p_at} de {nome}...")
                    
                    sel = (By.CSS_SELECTOR, cfg["seletor_card"]) if "seletor_card" in cfg else (By.TAG_NAME, cfg["tag_titulo"])
                    
                    try:
                        wait.until(EC.presence_of_element_located(sel))
                        time.sleep(5)  
                        cards = nav.find_elements(*sel)
                    except:
                        cards = nav.find_elements(By.XPATH, "//div[contains(@class, 'card')] | //h4 | //tr") if nome == "Finep - Oportunidades" else []
                    
                    atuais = [c.text.strip() for c in cards if c.text.strip()]
                    if p_at > 1 and (not atuais or atuais == ant):
                        log("       [🛑] O conteúdo se repetiu ou está vazio. Fim das páginas atingido.")
                        break
                    ant = atuais
                    
                    urls_validas_pagina = {}
                    
                    for card in cards:
                        try:
                            texto_card = card.text
                            if not texto_card: continue
                            txt_card_normalizado = texto_card.lower()
                            
                            for palavra in config.PALAVRAS_CHAVE:
                                palavra_limpa = palavra.lower()
                                radical = palavra_limpa[:-1] if len(palavra_limpa) > 5 else palavra_limpa
                                
                                if radical in txt_card_normalizado:
                                    try:
                                        url = None
                                        if "seletor_link" in cfg:
                                            try: url = card.find_element(By.CSS_SELECTOR, cfg["seletor_link"]).get_attribute("href")
                                            except: pass
                                        if not url:
                                            link = card.find_element(By.TAG_NAME, "a") if card.find_elements(By.TAG_NAME, "a") else card.find_element(By.XPATH, "./..").find_element(By.TAG_NAME, "a")
                                            url = link.get_attribute("href")
                                        
                                        if url:
                                            url_completa = urljoin(cfg["url"], url)
                                            if url_completa not in urls_validas_pagina:
                                                urls_validas_pagina[url_completa] = palavra
                                    except:
                                        pass
                        except:
                            continue
                    
                    # Processa as URLs únicas coletadas nesta página específica
                    if urls_validas_pagina:
                        log(f"    [~] Detectados {len(urls_validas_pagina)} editais compatíveis na página {p_at}. Filtrando histórico...")
                        
                        # O loop abaixo extrai a URL e o termo guardado dentro do dicionário
                        for url_unica, termo_ativado in urls_validas_pagina.items():
                            log(f"    [✓] Termo gatilho: '{termo_ativado}' -> Avaliando: {url_unica}")
                            
                            # >>> CORREÇÃO AQUI: Passando 'termo_ativado' no final do método <<<
                            web_utils.processar_pagina_interna(url_unica, cfg["ignorar_links"], nome, log, termo_ativado)

                    if p_at < cfg["max_paginas"]:
                        prox = p_at + 1
                        clicado = False
                        try:
                            # Executa uma rolagem total até o fim da página para garantir que o rodapé/paginação carregue
                            nav.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(2)
                            
                            if cfg.get("seletor_paginacao") == "finep":
                                selectors = [
                                    "ul.pagination button.page-link", 
                                    "ul.pagination a", 
                                    ".pagination li a",
                                    "//ul[contains(@class, 'pagination')]//a[text()='" + str(prox) + "']"
                                ]
                                for sel_str in selectors:
                                    try:
                                        if sel_str.startswith("//"):
                                            botoes = nav.find_elements(By.XPATH, sel_str)
                                        else:
                                            botoes = nav.find_elements(By.CSS_SELECTOR, sel_str)
                                        for b in botoes:
                                            if b.text.strip() == str(prox):
                                                nav.execute_script("arguments[0].scrollIntoView({block: 'center'});", b)
                                                time.sleep(1)
                                                nav.execute_script("arguments[0].click();", b)
                                                clicado = True; break
                                    except: continue
                                    if clicado: break
                            else:
                                # Estratégia Fundep (Componentes Mui com XPaths flexíveis)
                                xpaths_fundep = [
                                    "//ul[contains(@class, 'MuiPagination-ul')]//button[text()='" + str(prox) + "']",
                                    "//button[contains(@aria-label, 'page " + str(prox) + "')]",
                                    "//button[contains(@aria-label, 'página " + str(prox) + "')]",
                                    "//ul[contains(@class, 'MuiPagination-ul')]//button"
                                ]
                                for xpath in xpaths_fundep:
                                    try:
                                        botoes = nav.find_elements(By.XPATH, xpath)
                                        for b in botoes:
                                            if b.text.strip() == str(prox) or f"page {prox}" in (b.get_attribute("aria-label") or "").lower():
                                                nav.execute_script("arguments[0].scrollIntoView({block: 'center'});", b)
                                                time.sleep(1)
                                                nav.execute_script("arguments[0].click();", b)
                                                clicado = True; break
                                    except: continue
                                    if clicado: break
                                        
                            # FALLBACK DA SETA AVANÇAR (Se os números diretos falharem)
                            if not clicado:
                                xpaths_setas = [
                                    "//ul[contains(@class, 'pagination')]//button[contains(@aria-label, 'next')]",
                                    "//ul[contains(@class, 'MuiPagination-ul')]//button[contains(@aria-label, 'next')]",
                                    "//button[contains(@aria-label, 'Go to next page')]",
                                    "//button[contains(@aria-label, 'Próxima')]",
                                    "//li[contains(@class, 'next')]/a",
                                    "//button[text()='>']"
                                ]
                                for xpath_seta in xpaths_setas:
                                    try:
                                        seta = nav.find_element(By.XPATH, xpath_seta)
                                        dis = seta.get_attribute("disabled") or seta.get_attribute("aria-disabled")
                                        if dis and (dis == "true" or dis is True): 
                                            continue
                                        nav.execute_script("arguments[0].scrollIntoView({block: 'center'});", seta)
                                        time.sleep(1)
                                        nav.execute_script("arguments[0].click();", seta)
                                        clicado = True; break
                                    except: continue
                        except: 
                            pass
                        
                        if not clicado: 
                            log("       [🛑] Não foi possível avançar para a próxima página. Encerrando.")
                            break
                        
                        time.sleep(5) # Delay estendido pós-clique para estabilização completa do DOM
            except Exception as e: 
                log(f"    [X] Erro operacional no motor Selenium: {e}")
            finally: 
                try: nav.quit()
                except: pass
                
        # >>> ADICIONE ESTA LINHA AQUI, NO FINAL DE TODAS AS VARREDURAS DE SITES <<<
        processador.consumir_fila_pendente_ia(log)

    except Exception as e: 
        traceback.print_exc()
    
    log("\n[App Backend] Sincronização e triagem concluídas!")
    callback_fim()
