import os, json, requests, time, sys, pytesseract

from pypdf import PdfReader
from pdf2image import convert_from_path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from datetime import datetime

import config

# Configurações de caminhos para o executável do Tesseract OCR
if getattr(sys, 'frozen', False):
    DIR_TESS = os.path.join(sys._MEIPASS, "tesseract_bin")
else:
    DIR_TESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesseract_bin")

caminho_exe_tesseract = os.path.join(DIR_TESS, "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = caminho_exe_tesseract
os.environ["TESSDATA_PREFIX"] = os.path.join(DIR_TESS, "tessdata")
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
def extrair_dados_com_ia(texto_analise, chave_api):
    """Executa a chamada da API do Gemini usando o modelo homologado."""
    try:
        client = genai.Client(api_key=chave_api)
    except Exception as e:
        return {"erro": f"MALA_INICIALIZACAO: {e}"}

    prompt_completo = f"{config.PROMPT_BASE_IA}\n\nTexto do Edital para Análise:\n{texto_analise}"
    
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
        
        # 1. Auto-renovação de chaves na virada do dia
        verificar_hoje = config.supabase.table("chaves_api").select("id").eq("ultima_renovacao", hoje_str).execute()
        
        if not verificar_hoje.data:
            log_func("    [🔄 Auto-Renovação] Novo dia detectado. Reativando chaves de API...")
            todas_as_chaves = config.supabase.table("chaves_api").select("id").execute()
            
            for chave_registro in todas_as_chaves.data:
                id_real = chave_registro["id"]
                config.supabase.table("chaves_api").update({
                    "status": "ativa", 
                    "ultima_renovacao": hoje_str,
                    "falhas_seguidas": 0
                }).eq("id", id_real).execute()
                
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
        # Busca editais que aguardam análise da IA
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
            config.supabase.table("editais").update({
                "status_ia": "erro_sem_texto", "escopo": "Erro: Texto indisponivel."
            }).eq("url", edital["url"]).execute()
            continue

        resultado_ia = None
        edital_processado_com_sucesso = False

        while indice_chave_atual < len(lista_chaves_banco):
            chave_obj = lista_chaves_banco[indice_chave_atual]
            token_google = chave_obj["chave"]
            
            # Tenta executar a chamada à IA com suporte a retentativas em caso de instabilidade (Erro 503)
            for tentativa in range(1, 4):
                resultado_ia = extrair_dados_com_ia(texto_para_ia, token_google)
                if "erro" not in resultado_ia:
                    edital_processado_com_sucesso = True
                    break
                
                err_msg = str(resultado_ia["erro"]).upper()
                if "503" in err_msg or "HIGH DEMAND" in err_msg or "TEMPORARILY" in err_msg:
                    log_func(f"        [⚠️ Instabilidade] Gemini instável (Tentativa {tentativa}/3). Aguardando 20s...")
                    time.sleep(20)
                else:
                    break # Se for outro tipo de erro (ex: cota esgotada), quebra e roda a rotatividade de chaves
            
            if edital_processado_com_sucesso:
                break
                
            err_msg = str(resultado_ia["erro"]).upper()
            if "RESOURCE_EXHAUSTED" in err_msg or "QUOTA" in err_msg or "429" in err_msg:
                log_func(f"        [🚨 LIMITE] Chave ID {chave_obj['id']} de fato esgotada. Rotacionando...")
                config.supabase.table("chaves_api").update({"status": "esgotada"}).eq("id", chave_obj["id"]).execute()
                indice_chave_atual += 1
                continue
            else:
                log_func(f"        [X] Chave ID {chave_obj['id']} falhou por erro crítico: {resultado_ia['erro']}. Mudando de chave...")
                indice_chave_atual += 1
                continue


        if not edital_processado_com_sucesso:
            log_func("        [🛑 INTERRUPÇÃO] Infraestrutura de chaves de API esgotada.")
            return "bloqueio_diario"

        # Tratamento de datas e prazos de validade do edital
        prazo_texto = resultado_ia.get("datas") or "A consultar no edital"
        prazo_iso = resultado_ia.get("prazo_iso") or ""
        edital_vencido = False
        hoje = datetime.now().date()

        if prazo_iso and "9999" not in prazo_iso:
            try:
                dt_limite = datetime.strptime(prazo_iso.split(" ")[0].strip(), "%Y-%m-%d").date()
                if dt_limite < hoje: edital_vencido = True
            except: pass

        if edital_vencido:
            log_func(f"        [⏩ DESCARTE] Edital descartado por prazo vencido.")
            config.supabase.table("editais").update({
                "datas": "Expirado / Descartado", "status_ia": "descartado_vencido"
            }).eq("url", edital["url"]).execute()
            continue

        # Inserção atualizada enviando os resultados para as colunas estruturadas do banco
        dados_atualizados = {
            "datas": prazo_texto,
            "pesquisa": resultado_ia.get("pesquisa") or "Não encontrada",
            "subvencao": resultado_ia.get("subvencao") or "Não encontrada",
            "escopo": resultado_ia.get("escopo") or "Não encontrado",
            "prazo_iso": prazo_iso if (prazo_iso and "não" not in str(prazo_iso).lower()) else "9999-12-31 23:59",
            
            # GRAVAÇÃO OFICIAL DAS TAGS GERADAS PELA IA NA NOVA COLUNA DO SUPABASE
            "tags_ia": resultado_ia.get("tags_ia") or "Geral",
            
            "status_ia": "CONCLUIDO"
        }
        
        config.supabase.table("editais").update(dados_atualizados).eq("url", edital["url"]).execute()
        log_func(f"        [✓] Analise integrada com sucesso ao Supabase!")
        if idx < len(itens_pendentes): time.sleep(4)
        
    return "sucesso"


def limpar_editais_expirados_no_banco(log_func):
    """
    Identifica editais vencidos na base de dados, limpa os textos pesados 
    para economizar espaço e atualiza o status para 'expirado'.
    """
    try:
        hoje_str = datetime.now().date().isoformat()
        log_func("    [🧹 Faxina Base] Verificando se existem editais vencidos para expurgar...")
        
        # Busca editais concluídos que possuem data limite válida menor que hoje e que ainda não foram limpos
        resposta = config.supabase.table("editais")\
            .select("url, prazo_iso")\
            .not_.eq("status_ia", "expirado")\
            .not_.eq("prazo_iso", "9999-12-31 23:59")\
            .lt("prazo_iso", hoje_str)\
            .execute()
            
        editais_vencidos = resposta.data
        
        if not editais_vencidos:
            log_func("    [🧹 Faxina Base] Nenhum edital ativo está vencido. Base saudável!")
            return
            
        log_func(f"    [🧹 Faxina Base] Encontrados {len(editais_vencidos)} editais vencidos. Iniciando expurgo de textos...")
        
        # Payload de anulação de dados conforme o seu requisito (mantém apenas a URL e muda o status)
        dados_expurgados = {
            "datas": "Expirado",
            "pesquisa": None,
            "subvencao": None,
            "escopo": "Dados limpos por expiração de prazo.",
            "tags_ia": None,
            "status_ia": "expirado"
        }
        
        for item in editais_vencidos:
            config.supabase.table("editais").update(dados_expurgados).eq("url", item["url"]).execute()
            log_func(f"        [✓] Edital limpo e marcado como expirado: {item['url']}")
            
        log_func("    [🧹 Faxina Base] Rotina de expurgo concluída com sucesso!")
        
    except Exception as e:
        log_func(f"    [X] Erro na rotina de limpeza de expirados: {e}")
