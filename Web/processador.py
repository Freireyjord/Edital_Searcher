import os
import json
from urllib import response
import requests
import time
import sys
import pytesseract
from pypdf import PdfReader
from pdf2image import convert_from_path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from datetime import datetime
from playwright.sync_api import sync_playwright

import config

# Configurações de caminhos para o executável do Tesseract OCR
if getattr(sys, 'frozen', False):
    DIR_TESS = os.path.join(sys._MEIPASS, "tesseract_bin")
else:
    DIR_TESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesseract_bin")

caminho_exe_tesseract = os.path.join(DIR_TESS, "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = caminho_exe_tesseract
os.environ["TESSDATA_PREFIX"] = os.path.join(DIR_TESS, "tessdata")
# ==============================================================================
# 🦊 MOTORES DE CONTINGÊNCIA ISOLADOS POR PORTAL (RETRABALHO CIRÚRGICO)
# ==============================================================================

def recuperar_texto_petrobras(page, url_alvo, log_func):
    """Estratégia pesada e dedicada para o SPA React da Petrobras (Sigitec)."""
    page.goto(url_alvo, timeout=45000, wait_until="networkidle")
    page.wait_for_selector("div.text-justify, main h4, .sc-ehSEfb", timeout=20000)
    time.sleep(3.0)  # Acomodação do Virtual DOM
    page.evaluate("""() => {
        const loader = document.getElementById('loader');
        if (loader) loader.remove();
    }""")
    return page.evaluate("() => document.body.innerText")


def recuperar_texto_fundep(page, url_alvo, log_func):
    """Estratégia dedicada para as páginas dinâmicas em Next.js da Fundep."""
    page.goto(url_alvo, timeout=35000, wait_until="domcontentloaded")
    page.wait_for_selector("main, article, .content, #__next", timeout=15000)
    time.sleep(1.5)  # Garante a hidratação dos blocos de texto nativos
    return page.evaluate("() => document.body.innerText")


def recuperar_texto_cnpq(page, url_alvo, log_func):
    """Estratégia dedicada para o CNPq (HTML clássico institucional)."""
    page.goto(url_alvo, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_selector("table, div.conteudo, #main-content", timeout=10000)
    return page.evaluate("() => document.body.innerText")


def recuperar_texto_finep(page, url_alvo, log_func):
    """Estratégia dedicada para a Finep."""
    page.goto(url_alvo, timeout=35000, wait_until="domcontentloaded")
    page.wait_for_selector(".chamada-publica, #conteudo, main", timeout=15000)
    return page.evaluate("() => document.body.innerText")


# ==============================================================================
# 🎯 MAPEAMENTO DOS MOTORES POR PORTAL (DIREÇÃO DO RETRABALHO)
# ==============================================================================
DICIONARIO_MOTORES_RECOVERY = {
    "Petrobras - Sigitec": recuperar_texto_petrobras,
    "Fundep - Projetos": recuperar_texto_fundep,
    "CNPq": recuperar_texto_cnpq,
    "FINEP": recuperar_texto_finep
}
# ==============================================================================
# FUNÇÕES DE EXTRAÇÃO DE TEXTO BRUTO E ENVIOS DE PROMPT PARA IA
# ==============================================================================

def baixar_e_ler_pdf(url_pdf, nome_arquivo, termos_ignorados):
    if any(t in url_pdf.lower() for t in termos_ignorados): 
        return ""
    caminho = os.path.join(config.DIRETORIO_PDFS, nome_arquivo)
    try:
        resp = requests.get(url_pdf, timeout=15)
        with open(caminho, 'wb') as f: 
            f.write(resp.content)
    except: 
        return ""
    texto = ""
    try:
        leitor = PdfReader(caminho)
        for p in leitor.pages: 
            texto += p.extract_text() or ""
    except: 
        pass
    if len(texto.strip()) < 50:
        try:
            imgs = convert_from_path(caminho, first_page=1, last_page=10, dpi=150)
            for img in imgs: 
                texto += pytesseract.image_to_string(img, lang='por') + "\n"
        except: 
            pass
    return texto

def extrair_dados_com_ia(texto_analise, chave_api, url_edital="N/A", nome_portal="Portal"):
    try:
        client = genai.Client(api_key=chave_api)
    except Exception as e:
        return {"erro": f"MALA_INICIALIZACAO: {e}"}

    prompt_completo = f"{config.PROMPT_BASE_IA}\n\nTexto do Edital para Análise:\n{texto_analise}"
    
    try:
        pasta_auditoria = os.path.join(config.DIRETORIO_PAI, "logs_auditoria")
        os.makedirs(pasta_auditoria, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_portal_limpo = "".join(c for c in nome_portal if c.isalnum() or c in (' ', '_', '-')).strip().replace(" ", "_")
        caminho_prompt = os.path.join(pasta_auditoria, f"{nome_portal_limpo}_ia_prompt_{timestamp}.txt")
        with open(caminho_prompt, "w", encoding="utf-8") as f_prompt:
            f_prompt.write(f"URL ALVO: {url_edital}\nDATA DA REQUISIÇÃO IA: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n" + "="*80 + "\n\n" + prompt_completo)
    except Exception as e_prmt:
        print(f"[⚠️ Auditoria] Falha ao salvar txt do prompt da IA: {e_prmt}")
    
    try:
        resposta = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt_completo,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(resposta.text)
    except APIError as e:
        return {"erro": f"API_ERRO_{e.code}: {e.message}"}
    except Exception as e:
        return {"erro": f"ERRO_INESPERADO: {e}"}
    
def consumir_fila_pendente_ia(log_func, atualizar_tabela_func=None):
    try:
        hoje_str = datetime.now().date().isoformat()
        verificar_hoje = config.supabase.table("chaves_api").select("id").eq("ultima_renovacao", hoje_str).execute()
        
        if not verificar_hoje.data:
            log_func("    [🔄 Auto-Renovação] Novo dia detectado. Reativando chaves de API...")
            todas_as_chaves = config.supabase.table("chaves_api").select("id").execute()
            for chave_registro in todas_as_chaves.data:
                config.supabase.table("chaves_api").update({"status": "ativa", "ultima_renovacao": hoje_str, "falhas_seguidas": 0}).eq("id", chave_registro["id"]).execute()
            log_func("    [🔄 Auto-Renovação] Todas as chaves foram reativadas!")
            
        resp_chaves = config.supabase.table("chaves_api").select("*").eq("status", "ativa").order("id").execute()
        lista_chaves_banco = resp_chaves.data
    except Exception as e_bd:
        log_func(f"    [X] Erro no motor de chaves: {e_bd}")
        return "vazio"

    if not lista_chaves_banco:
        log_func("    [🛑 PARADA] Todas as chaves de API foram esgotadas!")
        return "bloqueio_diario"

    try:
        resposta = config.supabase.table("editais").select("*").eq("status_ia", "PENDENTE").execute()
        itens_pendentes = resposta.data
    except Exception as e:
        log_func(f"    [X] Erro ao buscar fila do Supabase: {e}")
        return "vazio"

    if not itens_pendentes:
        log_func("    [✨] Fila de IA vazia. Nenhum edital pendente de resumo.")
        return "vazio"

    log_func(f"\n    [Esteira IA] Processando {len(itens_pendentes)} editais...")
    indice_chave_atual = 0
    for idx, edital in enumerate(itens_pendentes, start=1):
        log_func(f"    -> Item {idx} de {len(itens_pendentes)}: {edital['url']}")
        texto_para_ia = edital.get("escopo", "") or edital.get("texto_extracao", "")
        
        if not texto_para_ia or not texto_para_ia.strip() or texto_para_ia == "Processando...":
            config.supabase.table("editais").update({"status_ia": "erro_sem_texto", "escopo": "Erro: Texto indisponivel."}).eq("url", edital["url"]).execute()
            continue

        resultado_ia = None
        edital_processado_com_sucesso = False

        while indice_chave_atual < len(lista_chaves_banco):
            chave_obj = lista_chaves_banco[indice_chave_atual]
            token_google = chave_obj["chave"]
            
            for tentativa in range(1, 4):
                resultado_ia = extrair_dados_com_ia(texto_para_ia, token_google, edital['url'], edital['portal'])
                if "erro" not in resultado_ia:
                    edital_processado_com_sucesso = True
                    break
                err_msg = str(resultado_ia["erro"]).upper()
                if "503" in err_msg or "HIGH DEMAND" in err_msg or "TEMPORARILY" in err_msg:
                    log_func(f"        [⚠️ Instabilidade] Gemini instável (Tentativa {tentativa}/3). Aguardando 20s...")
                    time.sleep(20)
                else:
                    break
            
            if edital_processado_com_sucesso:
                break
                
            err_msg = str(resultado_ia["erro"]).upper()
            if "RESOURCE_EXHAUSTED" in err_msg or "QUOTA" in err_msg or "429" in err_msg:
                log_func(f"        [🚨 LIMITE] Chave ID {chave_obj['id']} esgotada. Rotacionando...")
                config.supabase.table("chaves_api").update({"status": "esgotada"}).eq("id", chave_obj["id"]).execute()
                indice_chave_atual += 1
            else:
                log_func(f"        [X] Chave ID {chave_obj['id']} falhou por erro crítico. Mudando de chave...")
                indice_chave_atual += 1

        if not edital_processado_com_sucesso:
            log_func("        [🛑 INTERRUPÇÃO] Infraestrutura de chaves de API esgotada.")
            return "bloqueio_diario"

        prazo_texto = resultado_ia.get("datas") or "A consultar no edital"
        prazo_iso = resultado_ia.get("prazo_iso") or ""
        fim_projeto_iso = resultado_ia.get("fim_projeto_iso") or ""
        
        edital_vencido = False
        hoje = datetime.now().date()
        data_corte_iso = prazo_iso if (prazo_iso and "não" not in str(prazo_iso).lower()) else fim_projeto_iso

        if data_corte_iso and "9999" not in data_corte_iso:
            try:
                dt_limite = datetime.strptime(data_corte_iso.strip(), "%Y-%m-%d").date()
                if dt_limite < hoje: edital_vencido = True
            except: pass

        if edital_vencido:
            log_func(f"        [⏩ DESCARTE] Edital descartado por prazo vencido ({data_corte_iso}).")
            config.supabase.table("editais").update({"datas": "Expirado / Descartado", "status_ia": "descartado_vencido"}).eq("url", edital["url"]).execute()
            continue

        dados_atualizados = {
            "titulo": resultado_ia.get("titulo") or "Edital sem título definido",
            "datas": prazo_texto,
            "pesquisa": resultado_ia.get("pesquisa") or "Não encontrada",
            "subvencao": resultado_ia.get("subvencao") or "Não encontrada",
            "escopo": resultado_ia.get("escopo") or "Não encontrado",
            "prazo_iso": prazo_iso if (prazo_iso and "não" not in str(prazo_iso).lower()) else (fim_projeto_iso if fim_projeto_iso else "9999-12-31 23:59"),
            "vigencia_projeto": resultado_ia.get("vigencia_projeto") or "Não encontrada",
            "tags_ia": resultado_ia.get("tags_ia") or "Geral",
            "status_ia": "CONCLUIDO"
        }
        config.supabase.table("editais").update(dados_atualizados).eq("url", edital["url"]).execute()
        log_func(f"        [✓] Analise integrada com sucesso ao Supabase!")
        if idx < len(itens_pendentes): time.sleep(4)
        
    return "sucesso"
def executar_retrabalho_editais_com_erro(log_func):
    log_func("\n    [🔄 RETRABALHO] Iniciando varredura de contingência inteligente por portal...")
    
    try:
        resposta = config.supabase.table("editais").select("*").eq("status_ia", "erro_sem_texto").execute()
        itens_com_erro = resposta.data
    except Exception as e:
        log_func(f"    [X] Erro ao buscar fila de retrabalho no Supabase: {e}")
        return

    if not itens_com_erro:
        log_func("    [✨] Nenhum edital com erro crônico pendente de retrabalho na base.")
        return

    log_func(f"    [Esteira Retrabalho] Encontrados {len(itens_com_erro)} editais para análise dinâmica.")
    
    try:
        resp_chaves = config.supabase.table("chaves_api").select("*").eq("status", "ativa").order("id").execute()
        chaves_disponiveis = resp_chaves.data
    except:
        chaves_disponiveis = []

    if not chaves_disponiveis:
        log_func("    [🛑 Retrabalho] Abortando: Nenhuma chave de IA ativa disponível.")
        return

    with sync_playwright() as p_retro:
        browser = p_retro.chromium.launch(headless=True, args=["--headless=shell"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}, locale="pt-BR"
        )
        page = context.new_page()
        
        recuperados = 0
        falhas_persistentes = 0

        for edital in itens_com_erro:
            url_alvo = edital["url"]
            portal_origem = edital.get("portal", "Desconhecido")
            
            log_func(f"        [*] Re-analisando link da origem [{portal_origem}]: {url_alvo}")
            
            funcao_recuperacao = DICIONARIO_MOTORES_RECOVERY.get(portal_origem)
            
            if not funcao_recuperacao:
                log_func(f"            [⚠️] Alerta: Nenhum motor cadastrado para o portal '{portal_origem}'. Pulando...")
                falhas_persistentes += 1
                continue

            texto_recuperado = ""
            try:
                texto_recuperado = funcao_recuperacao(page, url_alvo, log_func)
            except Exception as err_nav:
                log_func(f"            [!] O motor '{portal_origem}' falhou na re-tentativa: {err_nav}")
            if texto_recuperado and len(texto_recuperado.strip()) >= 100:
                log_func(f"            [✓] Sucesso! Texto recuperado por contingência. Acionando IA...")
                
                resultado_ia = extrair_dados_com_ia(texto_recuperado, chaves_disponiveis["chave"], url_alvo, portal_origem)
                
                if "erro" not in resultado_ia:
                    prazo_texto = resultado_ia.get("datas") or "A consultar no edital"
                    prazo_iso = resultado_ia.get("prazo_iso") or "9999-12-31 23:59"
                    
                    dados_atualizados = {
                        "titulo": resultado_ia.get("titulo") or "Edital Recuperado",
                        "datas": prazo_texto,
                        "pesquisa": resultado_ia.get("pesquisa") or "Não encontrada",
                        "subvencao": resultado_ia.get("subvencao") or "Não encontrada",
                        "escopo": resultado_ia.get("escopo") or "Não encontrado",
                        "prazo_iso": prazo_iso,
                        "vigencia_projeto": resultado_ia.get("vigencia_projeto") or "Não encontrada",
                        "tags_ia": resultado_ia.get("tags_ia") or "Geral",
                        "status_ia": "CONCLUIDO"
                    }
                    config.supabase.table("editais").update(dados_atualizados).eq("url", url_alvo).execute()
                    log_func("            [🎉 PROMOVIDO] Edital recuperado e integrado à base ativa!")
                    recuperados += 1
                else:
                    log_func(f"            [X] IA rejeitou os dados extraídos: {resultado_ia['erro']}")
                    falhas_persistentes += 1
            else:
                log_func(f"            [❌] O motor especializado confirmou falha persistente (Link indisponível/Vazio).")
                falhas_persistentes += 1
                
            time.sleep(2.0)

        try: browser.close()
        except: pass

        log_func(f"\n    === [REPORT GERAL DE RETRABALHO DOS MOTORES] ===")
        log_func(f"        [📈] Total de Links de Erro Processados: {len(itens_com_erro)}")
        log_func(f"        [🎉] Editais Salvos e Ativados com código correto: {recuperados}")
        log_func(f"        [💀] Falhas Crônicas Mantidas (Servidor instável): {falhas_persistentes}")
        log_func(f"    ====================================================\n")


def limpar_editais_expirados_no_banco(log_func):
    try:
        hoje_str = datetime.now().date().isoformat()
        log_func("    [🧹 Faxina Base] Verificando se existem editais vencidos para expurgar...")
        resposta = config.supabase.table("editais").select("url, prazo_iso").not_.eq("status_ia", "expirado").not_.eq("prazo_iso", "9999-12-31 23:59").lt("prazo_iso", hoje_str).execute()
        editais_vencidos = response.data if hasattr(resposta, 'data') else resposta.data
        
        if not editais_vencidos:
            log_func("    [🧹 Faxina Base] Nenhum edital ativo está vencido. Base saudável!")
            return
            
        log_func(f"    [🧹 Faxina Base] Encontrados {len(editais_vencidos)} editais vencidos. Iniciando expurno...")
        dados_expurgados = {"datas": "Expirado", "pesquisa": None, "subvencao": None, "escopo": "Dados limpos por expiração de prazo.", "tags_ia": None, "status_ia": "expirado"}
        
        for item in editais_vencidos:
            config.supabase.table("editais").update(dados_expurgados).eq("url", item["url"]).execute()
            log_func(f"        [✓] Edital limpo e marcado como expirado: {item['url']}")
        log_func("    [🧹 Faxina Base] Rotina de expurgo concluída com sucesso!")
    except Exception as e:
        log_func(f"    [X] Erro na rotina de limpeza de expirados: {e}")
