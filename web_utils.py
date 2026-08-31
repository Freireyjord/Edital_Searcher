import os, json, requests, re, threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import processador
import config

banco_dados_lock = threading.Lock()

def extrair_data_texto(texto):
    if re.search(r"Inscrição:\s*Encerrada", texto, re.IGNORECASE):
        return datetime(2000, 1, 1)
    linhas_prazo = re.findall(r"(?:prazo|envio\s+de\s+propostas|limite|submissao).*?(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})", texto, re.IGNORECASE)
    prazos = []
    for dt_str in linhas_prazo:
        try:
            if "-" in dt_str: prazos.append(datetime.strptime(dt_str, "%Y-%m-%d"))
            else: prazos.append(datetime.strptime(dt_str, "%d/%m/%Y"))
        except: pass
    return max(prazos) if prazos else None

def verificar_se_ja_existe(url_alvo):
    """Verifica se o link já foi mapeado (seja pendente ou concluído)."""
    arq = config.CAMINHO_JSON_HISTORICO
    if not os.path.exists(arq): return False
    try:
        with open(arq, "r", encoding="utf-8") as f: hist = json.load(f)
        return any(i["url"] == url_alvo for i in hist)
    except: return False

def processar_pagina_interna(url_edital, ignorar_links, nome_portal, log_func, termo_ativado):
    if verificar_se_ja_existe(url_edital): 
        log_func(f"        [🛑 SKIPPED] Link '{url_edital}' já mapeado no sistema.")
        return True

    try:
        resp = requests.get(url_edital, timeout=15)
        html = BeautifulSoup(resp.text, "html.parser")
        links = html.find_all("a")
        txt_bruto, pdf_proc, nome_pdf = "", False, ""
        
        for l in links:
            href = l.get("href", "")
            txt_l = l.get_text().lower()
            if ".pdf" in href.lower() and any(k in txt_l for k in ["chamada", "edital", "regulamento", ".pdf"]):
                url_pdf = urljoin(url_edital, href)
                nome_pdf = url_pdf.split("/")[-1]
                if not nome_pdf.endswith(".pdf"): nome_pdf += ".pdf"
                log_func(f"        [Documento] Baixando PDF para fila: {nome_pdf}")
                txt_bruto = processador.baixar_e_ler_pdf(url_pdf, nome_pdf, ignorar_links)
                if txt_bruto.strip():
                    pdf_proc = True
                    break
                    
        if not pdf_proc:
            log_func("        [Texto Web] Coletando conteúdo textual da página para fila...")
            for s in html(["script", "style", "nav", "footer", "header"]): s.decompose()
            txt_bruto = html.get_text(separator="\n")
            
        if txt_bruto.strip():
            data_limite = extrair_data_texto(txt_bruto)
            if data_limite and data_limite.date() < datetime.now().date():
                log_func(f"        [⏩ DESCARTADO] Edital com prazo vencido em ({data_limite.strftime('%d/%m/%Y')}).")
                return True 
            
            # ENFILEIRAMENTO: Salva no JSON com a flag especial de IA pendente
            with banco_dados_lock:
                # Armazena o texto bruto coletado temporariamente dentro do JSON para a IA ler depois
                # Dentro do web_utils.py (função processar_pagina_interna):
                dados_provisorios = {
                    "portal": nome_portal, 
                    "url": url_edital, 
                    "pdf": f"editais_baixados/{nome_pdf}" if pdf_proc else "",
                    "datas": "Aguardando fila de IA...", 
                    "pesquisa": "Aguardando processamento...",
                    "subvencao": "Aguardando processamento...", 
                    "escopo": "Processando na Fila...",
                    "prazo_ISO": "9999-12-31 23:59",
                    "status_ia": "pendente",
                    "texto_extracao": txt_bruto,
                    "palavra_chave": termo_ativado # <--- CERTIFIQUE-SE DE ESTAR SALVANDO O TERMO AQUI!
                }

                
                arq = config.CAMINHO_JSON_HISTORICO
                hist = []
                if os.path.exists(arq):
                    try:
                        with open(arq, "r", encoding="utf-8") as f: hist = json.load(f)
                    except: pass
                hist.append(dados_provisorios)
                with open(arq, "w", encoding="utf-8") as f: json.dump(hist, f, indent=4, ensure_ascii=False)
                
            log_func(f"        [✓] Edital adicionado com sucesso na Fila de Processamento!")
            return True
    except Exception as e: 
        log_func(f"        [X] Falha na extração de dados da página: {e}")
    return False
