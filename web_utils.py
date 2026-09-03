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
    pats = r"(?:prazo|envio\s+de\s+propostas|limite|submissao).*?(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})"
    linhas_prazo = re.findall(pats, texto, re.IGNORECASE)
    prazos = []
    for dt_str in linhas_prazo:
        try:
            if "-" in dt_str: 
                prazos.append(datetime.strptime(dt_str, "%Y-%m-%d"))
            else: 
                prazos.append(datetime.strptime(dt_str, "%d/%m/%Y"))
        except: pass
    return max(prazos) if prazos else None

def verificar_se_ja_existe(url_alvo):
    arq = config.CAMINHO_JSON_HISTORICO
    if not os.path.exists(arq): return False
    try:
        with open(arq, "r", encoding="utf-8") as f: hist = json.load(f)
        return any(i["url"] == url_alvo for i in hist)
    except: return False

def processar_pagina_interna(url_edital, ignorar_links, nome_portal, log_func, termo_ativado, atualizar_tabela_func=None):
    if verificar_se_ja_existe(url_edital): 
        log_func(f"        [🛑 SKIPPED] Link '{url_edital}' já mapeado.")
        return True

    try:
        resp = requests.get(url_edital, timeout=15)
        html = BeautifulSoup(resp.text, "html.parser")
        links = html.find_all("a")
        txt_bruto, pdf_proc, nome_pdf = "", False, ""
        
        # 1. LOOP DE PROCURA E EXTRAÇÃO DE PDF
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
                    
        # 2. FALLBACK CASO NÃO ACHE PDF (Coleta texto direto da página)
        if not pdf_proc:
            log_func("        [Texto Web] Coletando conteúdo textual...")
            for s in html(["script", "style", "nav", "footer", "header"]): s.decompose()
            txt_bruto = html.get_text(separator="\n")
            
        # 3. FILTRO PRÉVIO DE PRAZO CRONOLÓGICO LOCAL
        if txt_bruto.strip():
            data_limite = extrair_data_texto(txt_bruto)
            if data_limite and data_limite.date() < datetime.now().date():
                log_func(f"        [⏩ DESCARTADO] Prazo vencido ({data_limite.strftime('%d/%m/%Y')}).")
                return True 

            # >>> LOCAL CORRETO: Fora de qualquer laço, após validar o texto completo <<<
            try:
                dados_provisorios = {
                    "portal": nome_portal, 
                    "url": url_edital, 
                    "pdf": f"editais_baixados/{nome_pdf}" if pdf_proc else "",
                    "datas": "⏳ Carregando Prazo...", 
                    "pesquisa": "Aguardando processamento...",
                    "subvencao": "Aguardando processamento...", 
                    "escopo": "Coletado com sucesso! Aguardando resumo do Gemini...",
                    "prazo_ISO": "9999-12-31 23:59", 
                    "status_ia": "pendente",
                    "texto_extracao": txt_bruto, 
                    "palavra_chave": termo_ativado
                }
                
                # Executa a gravação atômica diretamente no Banco SQL do Supabase
                config.supabase.table("editais").upsert(dados_provisorios).execute()
                log_func(f"        [✓] Edital adicionado com sucesso na Fila SQL Nuvem!")
                
                if atualizar_tabela_func:
                    atualizar_tabela_func()
                return True
            except Exception as e_sql:
                log_func(f"        [X] Erro ao enviar para o banco Supabase: {e_sql}")
                return False
                
    except Exception as e: 
        log_func(f"        [X] Falha na extração de dados da página: {e}")
    return False
