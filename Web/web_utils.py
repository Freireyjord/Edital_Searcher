import re
import io
import os
import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from datetime import datetime
import config

def limpar_texto_extraido(texto):
    """Remove ruidos do HTML/PDF para otimizar o consumo de tokens na IA."""
    if not texto: return ""
    texto = re.sub(r'[ \t]+', ' ', texto)
    texto = re.sub(r'[\r\n]+', '\n', texto)
    linhas = [linha.strip() for linha in texto.split('\n') if linha.strip()]
    return '\n'.join(linhas)

def extrair_texto_pdf(url_pdf, log):
    """Baixa o arquivo PDF em memoria e extrai seu conteudo textual."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url_pdf, headers=headers, timeout=25)
        if resp.status_code == 200:
            with io.BytesIO(resp.content) as stream_pdf:
                texto = extract_text(stream_pdf)
                return texto if texto else ""
    except Exception as e:
        log(f"        [⚠️] Erro ao extrair PDF ({url_pdf}): {e}")
    return ""

def extrair_texto_html(url_html, log):
    """Faz a raspagem do conteudo textual de paginas web padrao."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url_html, headers=headers, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.decompose()
            return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        log(f"        [⚠️] Erro ao extrair HTML ({url_html}): {e}")
    return ""

def processar_pagina_interna(url_edital, ignorar_links, nome_portal, log, palavra_chave, atualizar_tabela_func=None):
    """Verifica duplicidade, salva o texto bruto localmente para auditoria e cadastra no Supabase."""
    try:
        if any(ign in url_edital.lower() for ign in ignorar_links): return False

        # Verifica duplicidade no banco
        res_banco = config.supabase.table("editais").select("url").eq("url", url_edital).execute()
        if res_banco.data and len(res_banco.data) > 0:
            return False

        log(f"        [+] Novo edital localizado: {url_edital}")
        
        # Extração do Conteúdo bruto (PDF ou HTML)
        if url_edital.lower().endswith(".pdf"):
            texto_bruto = extrair_texto_pdf(url_edital, log)
        else:
            texto_bruto = extrair_texto_html(url_edital, log)

        texto_limpo = limpar_texto_extraido(texto_bruto)

        if not texto_limpo.strip() or len(texto_limpo.strip()) < 100:
            log(f"        [⚠️] Texto extraído muito curto ou inválido. Ignorando link.")
            return False

        # ----------------------------------------------------------------------
        # [AUDITORIA] SALVA O TEXTO BRUTO QUE O ROBÔ COLETOU DO SITE EM .TXT
        # ----------------------------------------------------------------------
        try:
            pasta_auditoria = os.path.join(config.DIRETORIO_PAI, "logs_auditoria")
            os.makedirs(pasta_auditoria, exist_ok=True)
            
            # Cria um nome de arquivo único e seguro para o sistema de arquivos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_portal_limpo = "".join(c for c in nome_portal if c.isalnum() or c in (' ', '_', '-')).strip().replace(" ", "_")
            nome_arquivo_txt = f"{nome_portal_limpo}_raw_texto_{timestamp}.txt"
            caminho_txt = os.path.join(pasta_auditoria, nome_arquivo_txt)
            
            with open(caminho_txt, "w", encoding="utf-8") as f_audit:
                f_audit.write(f"URL ORIGEM: {url_edital}\n")
                f_audit.write(f"PORTAL: {nome_portal}\n")
                f_audit.write(f"DATA COLETA: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f_audit.write("="*80 + "\n\n")
                f_audit.write(texto_limpo)
            log(f"        [📝 Auditoria] Texto bruto salvo em: {nome_arquivo_txt}")
        except Exception as e_txt:
            log(f"        [⚠️] Falha ao salvar txt de auditoria do robô: {e_txt}")
        # ----------------------------------------------------------------------

        # --- LÓGICA DE CAPTURA DUPLA INTELIGENTE (CABEÇA + CAUDA) ---
        if len(texto_limpo) > 25000:
            inicio_texto = texto_limpo[:15000]
            fim_texto = texto_limpo[-10000:]
            texto_final = f"{inicio_texto}\n\n[... TEXTO SUCINTADO PARA OTIMIZAÇÃO DE TOKEN ...]\n\n{fim_texto}"
        else:
            texto_final = texto_limpo

        # Inserção no Supabase mapeando o schema correto do banco
        dados_edital = {
            "url": url_edital,
            "portal": nome_portal,
            "palavra_chave": "Busca Ampla", 
            "status_ia": "PENDENTE",        
            "datas": "Processando...",
            "pesquisa": "Processando...",
            "escopo": texto_final, 
            "subvencao": "Processando...",
            "prazo_iso": None,
            "tags_ia": "Processando..."     
        }

        config.supabase.table("editais").insert(dados_edital).execute()
        log(f"        [✓] Edital registrado no Supabase com status PENDENTE.")
        return True

    except Exception as e:
        log(f"        [X] Erro no processamento do edital ({url_edital}): {e}")
        return False
