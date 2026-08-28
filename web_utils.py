import os, json, requests, re, threading, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import processador
import config

# Trava de segurança global de leitura/escrita para evitar corromper o arquivo
banco_dados_lock = threading.Lock()

def extrair_data_texto(texto):
    """Foca especificamente na linha de prazo final de envio para evitar falsos descartes."""
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

def verificar_bloqueio_token(url_alvo, log_func):
    """Verifica o status da URL no JSON. Se tiver erro, libera para tentar de novo."""
    arq = config.CAMINHO_JSON_HISTORICO
    
    with banco_dados_lock:
        if not os.path.exists(arq): 
            return False
        try:
            with open(arq, "r", encoding="utf-8") as f: 
                hist = json.load(f)
            for i in hist:
                if i["url"] == url_alvo:
                    escopo = str(i.get("escopo", ""))
                    # Se foi salvo anteriormente com erro, permite o reprocessamento direto
                    if "Erro no processamento" in escopo or "Erro na API" in escopo:
                        return False
                    log_func(f"        [🛑 SKIPPED] Link '{url_alvo}' já processado com sucesso. Poupando tokens.")
                    return True
        except: 
            pass
    return False

def processar_pagina_interna(url_edital, ignorar_links, nome_portal, log_func):
    if verificar_bloqueio_token(url_edital, log_func): return True

    try:
        resp = requests.get(url_edital, timeout=15)
        html = BeautifulSoup(resp.text, "html.parser")
        links = html.find_all("a")
        txt_ia, pdf_proc, nome_pdf = "", False, ""
        
        for l in links:
            href = l.get("href", "")
            txt_l = l.get_text().lower()
            if ".pdf" in href.lower() and any(k in txt_l for k in ["chamada", "edital", "regulamento", ".pdf"]):
                url_pdf = urljoin(url_edital, href)
                nome_pdf = url_pdf.split("/")[-1]
                if not nome_pdf.endswith(".pdf"): nome_pdf += ".pdf"
                log_func(f"        [Documento] Localizado PDF para análise: {nome_pdf}")
                txt_ia = processador.baixar_e_ler_pdf(url_pdf, nome_pdf, ignorar_links)
                if txt_ia.strip():
                    pdf_proc = True
                    break
                    
        if not pdf_proc:
            log_func("        [Texto Web] Extraindo conteúdo textual direto da página...")
            for s in html(["script", "style", "nav", "footer", "header"]): s.decompose()
            txt_ia = html.get_text(separator="\n")
            
        if txt_ia.strip():
            data_limite = extrair_data_texto(txt_ia)
            if data_limite and data_limite.date() < datetime.now().date():
                log_func(f"        [⏩ DESCARTADO] Edital com prazo vencido em ({data_limite.strftime('%d/%m/%Y')}).")
                return True 
            
            log_func("    [✨] Acionando Inteligência Artificial para análise de escopo técnico...")
            
            with banco_dados_lock:
                inf = processador.extrair_dados_com_ia(txt_ia)
                
                # --- NOVA LÓGICA DE SALVAMENTO DE FALHAS DO GEMINI ---
                if "Erro no processamento" in str(inf.get("Resumo do Escopo", "")) or not inf:
                    log_func(f"        [⚠️ SALVANDO LINK] Falha no Gemini. Gravando URL para re-tentativa automática.")
                    
                    # Cria um dicionário estruturado provisório apontando o erro para a tabela/fila
                    dados_erro = {
                        "Portal": nome_portal,
                        "Prazo / Submissão": "Aguardando renovação da API",
                        "Linha de Pesquisa": "Erro na API do Gemini",
                        "Orçamento / Subvenção": "Erro na API do Gemini",
                        "Resumo do Escopo": "Erro no processamento da API (Cota Excedida). Será re-tentado automaticamente.",
                        "prazo_ISO": "9999-12-31 23:59"
                    }
                    processador.salvar_resultado_no_historico(nome_portal, url_edital, dados_erro, nome_pdf if pdf_proc else "")
                    return False
                
                # Fluxo normal caso a IA funcione perfeitamente
                processador.salvar_resultado_no_historico(nome_portal, url_edital, inf, nome_pdf if pdf_proc else "")
                log_func(f"        [✓] Edital gravado com sucesso no arquivo JSON!")
                
            # Intervalo de respiro anti-bloqueio RPM do Google AI Studio
            time.sleep(3)
            return True
    except Exception as e: 
        log_func(f"        [X] Falha interna de varredura: {e}")
    return False
