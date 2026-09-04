import os
import re
import io
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pdfminer.high_level import extract_text
import config


def limpar_texto_extraido(texto):
    """
    Remove ruídos do HTML/PDF para otimizar o consumo de caracteres:
    - Reduz múltiplos espaços e tabs sequenciais para um único espaço.
    - Reduz múltiplas quebras de linha seguidas para apenas uma.
    - Remove espaços desnecessários no início e fim de cada linha.
    """
    if not texto:
        return ""
    
    # 1. Substitui múltiplos espaços/tabs na mesma linha por um único espaço
    texto = re.sub(r'[ \t]+', ' ', texto)
    
    # 2. Substitui múltiplas quebras de linha seguidas por apenas uma
    texto = re.sub(r'[\r\n]+', '\n', texto)
    
    # 3. Remove espaços no início e final de cada linha e descarta linhas vazias
    linhas = [linha.strip() for linha in texto.split('\n') if linha.strip()]
    
    return '\n'.join(linhas)


def extrair_texto_pdf(url_pdf, log):
    """Baixa o arquivo PDF em memória e extrai seu conteúdo textual."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url_pdf, headers=headers, timeout=25)
        if resp.status_code == 200:
            with io.BytesIO(resp.content) as stream_pdf:
                texto = extract_text(stream_pdf)
                return texto if texto else ""
    except Exception as e:
        log(f"        [⚠️] Erro ao extrair PDF ({url_pdf}): {e}")
    return ""


def extrair_texto_html(url_html, log):
    """Faz a raspagem do conteúdo textual de páginas web padrão."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url_html, headers=headers, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove elementos invisíveis ou irrelevantes antes de extrair o texto
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.decompose()
                
            return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        log(f"        [⚠️] Erro ao extrair HTML ({url_html}): {e}")
    return ""


def processar_pagina_interna(url_edital, ignorar_links, nome_portal, log, palavra_chave, atualizar_tabela_func=None):
    """
    Verifica se a URL já existe no Supabase. Se for nova, extrai e sanitiza
    o texto antes de cadastrar o edital com o schema correto do banco.
    """
    try:
        # 1. Filtro de links descartados
        if any(ign in url_edital.lower() for ign in ignorar_links):
            return False

        # 2. Verificação de Duplicidade no Supabase (utiliza a coluna 'url')
        res_banco = config.supabase.table("editais").select("url").eq("url", url_edital).execute()
        if res_banco.data and len(res_banco.data) > 0:
            log(f"        [i] Edital já cadastrado no banco: {url_edital}")
            return False

        log(f"        [+] Novo edital localizado: {url_edital}")
        
        # 3. Extração do Conteúdo (PDF ou Página HTML)
        texto_bruto = ""
        if url_edital.lower().endswith(".pdf"):
            texto_bruto = extrair_texto_pdf(url_edital, log)
        else:
            texto_bruto = extrair_texto_html(url_edital, log)

        # 4. Sanitização para remover espaços em branco e quebras de linha inúteis
        texto_limpo = limpar_texto_extraido(texto_bruto)

        # Corta mantendo até 25.000 caracteres de texto sanitizado útil
        texto_final = texto_limpo[:25000] if texto_limpo else "Texto indisponível para extração."

        # 5. Inserção no Supabase mapeando as colunas do seu banco
        dados_edital = {
            "url": url_edital,
            "portal": nome_portal,
            "palavra_chave": palavra_chave,
            "status_ia": "PENDENTE",
            "datas": "Processando...",
            "pesquisa": "Processando...",
            "escopo": texto_final,
            "subvencao": "Processando...",
            "prazo_iso": None
        }

        config.supabase.table("editais").insert(dados_edital).execute()
        log(f"        [✓] Edital registrado no Supabase com status PENDENTE.")

        if atualizar_tabela_func:
            atualizar_tabela_func()

        return True

    except Exception as e:
        log(f"        [X] Erro no processamento do edital ({url_edital}): {e}")
        return False