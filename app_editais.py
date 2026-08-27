import os, time, requests, json, webbrowser, datetime, threading, traceback, re, unicodedata, sys, pytesseract
import tkinter as tk
from tkinter import ttk, messagebox
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google import genai
from google.genai import types

# =====================================================================
# CONFIGURAÇÕES UNIFICADAS DO SISTEMA E IA (ESCOPO GLOBAL BLINDADO)
# =====================================================================
API_KEY_GEMINI = ""
client = genai.Client(api_key=API_KEY_GEMINI)

PALAVRAS_CHAVE = [
    "motor", "diesel", "combustível", "combustíveis", "veículo", "veículos",
    "mobilidade elétrica", "Sistemas de navegação autônomos", "Eficiência energética",
    "Redução de emissões", "Biocombustíveis", "Dinâmica veicular", "Autotrônica",
    "Sistemas embarcados automotivos", "Captura de CO2", "Catalisadores",
    "Automotivo", "Automotiva", "Mecânico", "Mecânica"
]

if getattr(sys, 'frozen', False):
    DIRETORIO_PAI = os.path.dirname(sys.executable)
else:
    DIRETORIO_PAI = os.path.dirname(os.path.abspath(__file__))

DIRETORIO_PDFS = os.path.join(DIRETORIO_PAI, "editais_baixados")
os.makedirs(DIRETORIO_PDFS, exist_ok=True)
CAMINHO_JSON_HISTORICO = os.path.join(DIRETORIO_PAI, "resultados_editais.json")

PROMPT_BASE_IA = """
Você é um especialista em editais e projetos. Extraia estritamente do texto abaixo:
1. Data de Submissão (Prazo final ou vigência de início e término previsto).
2. Linha de Pesquisa (Áreas temáticas envolvidas).
3. Resumo do Escopo Técnico (Resumo explicativo do objetivo prático do edital).
4. Linha de Subvenção (Valores financeiros, bolsas ou órgãos Financiadores envolvidos).
5. prazo_ISO (Data limite convertida para o formato estrito 'AAAA-MM-DD HH:MM'. Se fluxo contínuo ou sem prazo, retorne '9999-12-31 23:59').

Responda estritamente no formato JSON válido com as chaves exatas: 
"Data de Submissão", "Linha de Pesquisa", "Resumo do Escopo", "Linha de Subvenção", "prazo_ISO".
"""

SITES_ESTATICOS = {"CNPq - Chamadas Abertas": {"url": "https://www.gov.br", "tag_titulo": "h2", "ignorar_links": ["carta-de-servicos", "faq"]}}
SITES_DINAMICOS = {
    "Fundep - Projetos": {"url": "https://ufmg.br", "tag_titulo": "h3", "max_paginas": 10, "ignorar_links": ["manual", "tutorial"], "seletor_paginacao": "mui"},
    "Finep - Oportunidades": {"url": "https://finep.gov.br", "seletor_card": ".produto-card", "seletor_link": ".link-interna a", "tag_titulo": "body", "max_paginas": 10, "ignorar_links": ["manual", "formulario", "orientacoes"], "seletor_paginacao": "finep"}
}

def remover_acentos(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

# =====================================================================
# INTERFACE GRÁFICA DESKTOP (MÓDULO DE SELETOR E OPERAÇÃO VISUAL)
# =====================================================================
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, background="#f0f2f5")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, background="#f0f2f5")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    def atualizar_largura(self):
        self.canvas.update_idletasks()
        self.canvas.itemconfigure(1, width=self.canvas.winfo_width())

class AppEditais(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monitor Inteligente de Editais e Chamadas Públicas")
        self.geometry("980x820")
        self.configure(background="#f0f2f5")
        self.lista_contadores = []
        
        header = tk.Frame(self, background="#1e3d59", pady=10)
        header.pack(fill="x", side="top")
        tk.Label(header, text="Editais e Projetos Mapeados por Inteligência Artificial", font=("Segoe UI", 16, "bold"), foreground="#ffffff", background="#1e3d59").pack(pady=5)
        
        self.btn_sincronizar = tk.Button(
            header, text="🔄 Sincronizar Portais e Atualizar Cards", font=("Segoe UI", 10, "bold"),
            background="#ff6f3c", foreground="#ffffff", relief="flat", padx=20, pady=6, cursor="hand2",
            command=self.disparar_sincronizacao
        )
        self.btn_sincronizar.pack(pady=5)
        
        self.container_cards = ScrollableFrame(self)
        self.container_cards.pack(fill="both", expand=True, padx=20, pady=5)
        
        log_frame = tk.Frame(self, background="#ffffff", height=150, highlightbackground="#e0e0e0", highlightthickness=1)
        log_frame.pack(fill="x", side="bottom", padx=20, pady=10)
        tk.Label(log_frame, text="💻 Console de Diagnóstico (Debug em tempo real):", font=("Segoe UI", 9, "bold"), background="#ffffff", foreground="#555555").pack(anchor="w", padx=10, pady=2)
        
        self.txt_log = tk.Text(log_frame, height=6, bg="#1e1e1e", fg="#ffffff", font=("Consolas", 9), relief="flat", padx=8, pady=4)
        self.txt_log.pack(fill="x", padx=10, pady=(0, 5))
        
        self.carregar_cards()
        self.atualizar_cronometros_em_tempo_real()

    def log(self, msg):
        self.txt_log.insert(tk.END, f"{msg}\n")
        self.txt_log.see(tk.END)
        self.update_idletasks()

    def carregar_cards(self):
        self.lista_contadores.clear()
        for w in self.container_cards.scrollable_frame.winfo_children(): w.destroy()
        if os.path.exists(CAMINHO_JSON_HISTORICO):
            try:
                with open(CAMINHO_JSON_HISTORICO, "r", encoding="utf-8") as f: dados = json.load(f)
                if not dados:
                    self.mostrar_aviso_vazio("O histórico está vazio. Sincronize os portais.")
                    return
                for item in dados: self.criar_card(item)
                self.container_cards.atualizar_largura()
            except Exception as e: self.mostrar_aviso_vazio(f"Erro ao ler banco de dados: {e}")
        else: self.mostrar_aviso_vazio("Nenhum edital capturado. Sincronize os portais.")

    def mostrar_aviso_vazio(self, msg):
        tk.Label(self.container_cards.scrollable_frame, text=msg, font=("Segoe UI", 12), background="#f0f2f5", foreground="#666666", justify="center").pack(pady=80, fill="x")

    def disparar_sincronizacao(self):
        self.btn_sincronizar.configure(state="disabled", text="⏳ Buscando nos portais... Aguarde...", background="#888888")
        self.mostrar_aviso_vazio("🕵️ Varrer portais ativos em execução de thread nativa...")
        # CORREÇÃO CRÍTICA: Força a injeção imediata da primeira mensagem de log na interface
        self.log("[Interface] Solicitando inicialização de subprocesso em Thread segura...")
        threading.Thread(target=self.executar_robos_nativos, daemon=True).start()

    def executar_robos_nativos(self):
        try:
            self.log("[Robô] Varredura nativa unificada iniciada!")
            p_limpas = [remover_acentos(p) for p in PALAVRAS_CHAVE]

            # --- ESTÁTICOS (CNPq) ---
            for nome, cfg in SITES_ESTATICOS.items():
                self.log(f"===> Analisando portal estático: {nome}")
                try:
                    resp = requests.get(cfg["url"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                    html = BeautifulSoup(resp.text, "html.parser")
                    chamadas = html.find_all(cfg["tag_titulo"])
                    self.log(f"    -> {len(chamadas)} chamadas estruturais encontradas na home.")
                    for ch in chamadas:
                        txt = remover_acentos(ch.get_text() + " " + (ch.find_next("p").get_text() if ch.find_next("p") else ""))
                        for i, pl in enumerate(p_limpas):
                            if pl in txt:
                                self.log(f"    [✓] Termo encontrado no CNPq: '{PALAVRAS_CHAVE[i]}'")
                                link = ch.find("a") if ch.name == cfg["tag_titulo"] else ch.find_next("a")
                                if link and link.has_attr("href"):
                                    self.processar_link_ia(urljoin(cfg["url"], link["href"]), cfg["ignorar_links"], nome)
                except Exception as e: self.log(f"    [X] Erro estático {nome}: {e}")

                        # --- DINÂMICOS (SELENIUM - FUNDEP E FINEP) ---
            for nome, cfg in SITES_DINAMICOS.items():
                self.log(f"===> Analisando portal dinâmico com Selenium: {nome}")
                opt = webdriver.ChromeOptions()
                opt.add_argument("--headless"); opt.add_argument("--no-sandbox"); opt.add_argument("--disable-dev-shm-usage")
                opt.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                nav = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
                wait = WebDriverWait(nav, 20); ant = []
                try:
                    nav.get(cfg["url"])
                    for p_at in range(1, cfg["max_paginas"] + 1):
                        self.log(f"    -> Lendo a página {p_at} de {nome}...")
                        sel = (By.CSS_SELECTOR, cfg["seletor_card"]) if "seletor_card" in cfg else (By.TAG_NAME, cfg["tag_titulo"])
                        try:
                            wait.until(EC.presence_of_element_located(sel)); time.sleep(3)
                            cards = nav.find_elements(*sel)
                        except: cards = nav.find_elements(By.XPATH, "//div[contains(@class, 'card')] | //h4 | //tr") if nome == "Finep - Oportunidades" else []
                        atuais = [c.text.strip() for c in cards if c.text.strip()]
                        if p_at > 1 and (not atuais or atuais == ant): break
                        ant = atuais
                        for card in cards:
                            if not card.text: continue
                            txt_c = remover_acentos(card.text)
                            for i, pl in enumerate(p_limpas):
                                if pl in txt_c:
                                    self.log(f"    [✓] Termo encontrado em card: '{PALAVRAS_CHAVE[i]}'")
                                    try:
                                        url = card.find_element(By.CSS_SELECTOR, cfg["seletor_link"]).get_attribute("href") if "seletor_link" in cfg else None
                                        if not url: url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                                        if url: self.processar_link_ia(url, cfg["ignorar_links"], nome)
                                    except: pass
                        if p_at < cfg["max_paginas"]:
                            prox = p_at + 1; clicado = False
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                ac = ActionChains(nav)
                                if cfg.get("seletor_paginacao") == "finep":
                                    btns = nav.find_elements(By.CSS_SELECTOR, "ul.pagination button.page-link, ul.pagination a")
                                    for b in btns:
                                        if b.text.strip() == str(prox): ac.move_to_element(b).perform(); time.sleep(1); nav.execute_script("arguments[0].click();", b); clicado = True; break
                                else:
                                    btns = nav.find_elements(By.XPATH, "//ul[contains(@class, 'MuiPagination-ul')]//button")
                                    for b in btns:
                                        if b.text.strip() == str(prox) or f"page {prox}" in (b.get_attribute("aria-label") or "").lower(): ac.move_to_element(b).perform(); time.sleep(1); nav.execute_script("arguments[0].click();", b); clicado = True; break
                            except: pass
                            if not clicado:
                                try:
                                    seta = nav.find_element(By.XPATH, "//ul[contains(@class, 'pagination')]//button[contains(@aria-label, 'next')] | //ul[contains(@class, 'MuiPagination-ul')]//button[contains(@aria-label, 'next')]")
                                    dis = seta.get_attribute("disabled") or seta.get_attribute("aria-disabled")
                                    if dis and (dis == "true" or dis is True): break
                                    ac.move_to_element(seta).perform(); time.sleep(1)
                                    nav.execute_script("arguments[0].click();", seta)
                                    clicado = True
                                except: pass
                            if not clicado: break
                except Exception as e: self.log(f"    [X] Erro no Selenium: {e}")
                finally: nav.quit()
        except: self.log(traceback.format_exc())
        self.after(0, self.finalizar_sincronizacao)

    def processar_link_ia(self, url, ignorar, nome_p):
        if os.path.exists(CAMINHO_JSON_HISTORICO):
            try:
                with open(CAMINHO_JSON_HISTORICO, "r", encoding="utf-8") as f:
                    if any(i["url"] == url for i in json.load(f)): return
            except: pass
        self.log(f"        [✨] Enviando edital para inteligência artificial: {url}")
        try:
            resp = requests.get(url, timeout=15)
            html = BeautifulSoup(resp.text, "html.parser")
            txt_ia, pdf_proc, nome_pdf = "", False, ""
            for l in html.find_all("a"):
                href = l.get("href", "")
                if ".pdf" in href.lower() and any(k in l.get_text().lower() for k in ["chamada", "edital", "regulamento"]):
                    url_pdf = urljoin(url, href)
                    nome_pdf = url_pdf.split("/")[-1]
                    if not nome_pdf.endswith(".pdf"): nome_pdf += ".pdf"
                    caminho = os.path.join(DIRETORIO_PDFS, nome_pdf)
                    with open(caminho, 'wb') as f: f.write(requests.get(url_pdf).content)
                    try:
                        from pypdf import PdfReader
                        for p in PdfReader(caminho).pages: txt_ia += p.extract_text() or ""
                    except: pass
                    if len(txt_ia.strip()) < 50:
                        try:
                            from pdf2image import convert_from_path
                            for img in convert_from_path(caminho, dpi=100): txt_ia += pytesseract.image_to_string(img, lang='por') + "\n"
                        except: pass
                    pdf_proc = True; break
            if not pdf_proc:
                for s in html(["script", "style", "nav", "footer", "header"]): s.decompose()
                txt_ia = html.get_text(separator="\n")
            if txt_ia.strip():
                ans = client.models.generate_content(model='gemini-3.6-flash', contents=f"{PROMPT_BASE_IA}\n\n{txt_ia}", config=types.GenerateContentConfig(response_mime_type="application/json"))
                dados_ia = json.loads(ans.text)
                hist = []
                if os.path.exists(CAMINHO_JSON_HISTORICO):
                    with open(CAMINHO_JSON_HISTORICO, "r", encoding="utf-8") as f: hist = json.load(f)
                prazo = dados_ia.get("prazo_ISO", "")
                if not prazo or "não" in prazo.lower(): prazo = "9999-12-31 23:59"
                hist.append({"portal": nome_p, "url": url, "pdf": f"editais_baixados/{nome_pdf}" if pdf_proc else "", "datas": dados_ia.get("Data de Submissão"), "pesquisa": dados_ia.get("Linha de Pesquisa"), "subvencao": dados_ia.get("Linha de Subvenção"), "escopo": dados_ia.get("Resumo do Escopo"), "prazo_ISO": prazo})
                with open(CAMINHO_JSON_HISTORICO, "w", encoding="utf-8") as f: json.dump(hist, f, indent=4, ensure_ascii=False)
        except Exception as e: self.log(f"        [X] Erro IA no link {url}: {e}")

    def finalizar_sincronizacao(self):
        self.btn_sincronizar.configure(state="normal", text="🔄 Sincronizar Portais e Atualizar Cards", background="#ff6f3c")
        self.carregar_cards()
        messagebox.showinfo("Sucesso", "Monitoramento concluído!")

    def criar_card(self, item):
        card = tk.Frame(self.container_cards.scrollable_frame, background="#ffffff", highlightbackground="#e0e0e0", highlightthickness=1)
        card.pack(fill="x", padx=15, pady=8, ipady=5)
        cor_portal = "#17b978" if "Finep" in item['portal'] else ("#00bcd4" if "CNPq" in item['portal'] else "#ff6f3c")
        tk.Frame(card, background=cor_portal, width=5).pack(side="left", fill="y")
        conteudo = tk.Frame(card, background="#ffffff", padx=15, pady=6)
        conteudo.pack(side="left", fill="both", expand=True)
        
        topo = tk.Frame(conteudo, background="#ffffff")
        topo.pack(fill="x", pady=(0,2))
        tk.Label(topo, text=f"🏢 ORIGEM: {item['portal'].upper()}", font=("Segoe UI", 11, "bold"), foreground=cor_portal, background="#ffffff").pack(side="left")
        lbl_relogio = tk.Label(topo, text="⏳ Calculando...", font=("Segoe UI", 10, "bold"), background="#ffffff", foreground="#555555")
        lbl_relogio.pack(side="right")
        self.lista_contadores.append({"label": lbl_relogio, "prazo_ISO": item.get("prazo_ISO", "")})
        
        self.adicionar_campo(conteudo, "📅 Referência/Datas: ", item.get("datas"))
        self.adicionar_campo(conteudo, "🔬 Linha de Pesquisa/Eixos: ", item.get("pesquisa"))
        self.adicionar_campo(conteudo, "💰 Financiamento/Subvenção: ", item.get("subvencao"))
        
        txt = tk.Text(conteudo, font=("Segoe UI", 10), background="#f8f9fa", relief="flat", height=3, wrap="word", padx=8, pady=4)
        txt.insert("1.0", item.get("escopo", "Não encontrado")); txt.configure(state="disabled"); txt.pack(fill="x", pady=(4, 6))
        
        btns = tk.Frame(conteudo, background="#ffffff")
        btns.pack(anchor="w")
        tk.Button(btns, text="🌐 Ir para Fonte Web", font=("Segoe UI", 9, "bold"), background="#1e3d59", foreground="#ffffff", relief="flat", padx=12, pady=4, cursor="hand2", command=lambda: webbrowser.open(item["url"])).pack(side="left", padx=(0, 8))
        if item.get("pdf"):
            p_pdf = os.path.join(DIRETORIO_PAI, item.get("pdf"))
            if os.path.exists(p_pdf): tk.Button(btns, text="📄 Abrir Edital PDF", font=("Segoe UI", 9, "bold"), background="#ff6f3c", foreground="#ffffff", relief="flat", padx=12, pady=4, cursor="hand2", command=lambda p=p_pdf: os.startfile(p) if os.name == "nt" else webbrowser.open(p)).pack(side="left")

    def adicionar_campo(self, container, label, texto):
        f = tk.Frame(container, background="#ffffff")
        f.pack(anchor="w", fill="x", pady=1)
        tk.Label(f, text=label, font=("Segoe UI", 9, "bold"), background="#ffffff", foreground="#555555").pack(side="left", anchor="nw")
        tk.Label(f, text=texto, font=("Segoe UI", 9), background="#ffffff", foreground="#222222", justify="left", wraplength=730).pack(side="left", anchor="nw", fill="x", expand=True)

    def atualizar_cronometros_em_tempo_real(self):
        agora = datetime.datetime.now()
        for c in self.lista_contadores:
            prazo_str = c["prazo_ISO"]
            if not prazo_str or "9999" in prazo_str:
                c["label"].configure(text="♾️ Fluxo Contínuo / Sem Prazo", foreground="#666666"); continue
            try:
                prazo_dt = datetime.datetime.strptime(prazo_str, "%Y-%m-%d %H:%M")
                if agora > prazo_dt: c["label"].configure(text="🚨 EXPIRADO", foreground="#d9534f")
                else:
                    diff = prazo_dt - agora
                    dias = diff.days
                    horas, rem = divmod(diff.seconds, 3600)
                    mins, _ = divmod(rem, 60)
                    c["label"].configure(text=f"⏳ Restam: {dias}d {horas:02d}h {mins:02d}m", foreground="#f0ad4e" if dias < 3 else "#5cb85c")
            except: c["label"].configure(text="⏳ Erro formato")
        self.after(1000, self.atualizar_cronometros_em_tempo_real)

if __name__ == "__main__":
    app = AppEditais()
    app.mainloop()
