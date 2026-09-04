import os, json, requests, time, sys, pytesseract, re
from pypdf import PdfReader
from pdf2image import convert_from_path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from datetime import datetime
import config

if getattr(sys, 'frozen', False):
    DIRETORIO_TESSERACT = os.path.join(sys._MEIPASS, "tesseract_bin")
else:
    DIRETORIO_TESSERACT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesseract_bin")

caminho_exe_tesseract = os.path.join(DIRETORIO_TESSERACT, "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = caminho_exe_tesseract
os.environ["TESSDATA_PREFIX"] = os.path.join(DIRETORIO_TESSERACT, "tessdata")

def baixar_e_ler_pdf(url_pdf, nome_arquivo, termos_ignorados):
    if any(t in url_pdf.lower() for t in termos_ignorados): return ""
    caminho = os.path.join(config.DIRETORIO_PDFS, nome_arquivo)
    try:
        resp = requests.get(url_pdf, timeout=15)
        with open(caminho, 'wb') as f: f.write(resp.content)
    except: return ""
    texto = ""
    try:
        leitor = PdfReader(caminho)
        for p in leitor.pages: texto += p.extract_text() or ""
    except: pass
    if len(texto.strip()) < 50:
        try:
            imgs = convert_from_path(caminho, dpi=150)
            for img in imgs: texto += pytesseract.image_to_string(img, lang='por') + "\n"
        except: pass
    return texto

def extrair_dados_com_ia(texto_analise, chave_api):
    """Executa a chamada da API do Gemini usando uma chave específica repassada."""
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
        
        # 1. Auto-renovação de chaves
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
                
            log_func("    [🔄 Auto-Renovação] Todas as chaves foram reativadas com sucesso!")
            
        resp_chaves = config.supabase.table("chaves_api").select("*").eq("status", "ativa").order("id").execute()
        lista_chaves_banco = resp_chaves.data
        
    except Exception as e_bd:
        log_func(f"    [X] Erro no motor de chaves: {e_bd}")
        return "vazio"

    if not lista_chaves_banco:
        log_func("    [🛑 PARADA] Todas as chaves de API cadastradas no Supabase foram esgotadas!")
        return "bloqueio_diario"

    try:
        # CORREÇÃO: Busca por 'PENDENTE' em maiúsculo para combinar com o web_utils.py
        resposta = config.supabase.table("editais").select("*").eq("status_ia", "PENDENTE").execute()
        itens_pendentes = resposta.data
    except Exception as e:
        log_func(f"    [X] Erro ao buscar fila do Supabase: {e}")
        return "vazio"

    if not itens_pendentes:
        log_func("    [✨] Fila de IA vazia na Nuvem. Nenhum edital pendente de resumo.")
        return "vazio"

    log_func(f"\n    [Esteira IA Global] Iniciando processamento de {len(itens_pendentes)} editais...")
    
    indice_chave_atual = 0

    for idx, edital in enumerate(itens_pendentes, start=1):
        log_func(f"    -> Processando item {idx} de {len(itens_pendentes)}: {edital['url']}")
        
        # CORREÇÃO: O texto lido foi gravado na coluna 'escopo' pelo web_utils.py
        texto_para_ia = edital.get("escopo", "") or edital.get("texto_extracao", "")
        
        if not texto_para_ia or not texto_para_ia.strip() or texto_para_ia == "Processando...":
            config.supabase.table("editais").update({
                "status_ia": "erro_sem_texto", 
                "escopo": "Erro: Texto não disponível para análise da IA."
            }).eq("url", edital["url"]).execute()
            continue

        resultado_ia = None
        edital_processado_com_sucesso = False

        while indice_chave_atual < len(lista_chaves_banco):
            chave_obj = lista_chaves_banco[indice_chave_atual]
            token_google = chave_obj["chave"]

            resultado_ia = extrair_dados_com_ia(texto_para_ia, token_google)
            
            if "erro" not in resultado_ia:
                edital_processado_com_sucesso = True
                break
                
            err_msg = str(resultado_ia["erro"]).upper()
            if "RESOURCE_EXHAUSTED" in err_msg or "QUOTA" in err_msg or "429" in err_msg:
                log_func(f"        [🚨 CHAVE ESGOTADA] Chave ID {chave_obj['id']} limite atingido. Desativando...")
                config.supabase.table("chaves_api").update({"status": "esgotada"}).eq("id", chave_obj["id"]).execute()
                
                indice_chave_atual += 1
                if indice_chave_atual < len(lista_chaves_banco):
                    log_func(f"        [🔄 Rotatividade] Mudando para a Chave ID {lista_chaves_banco[indice_chave_atual]['id']}...")
                continue
            else:
                log_func(f"        [⚠️ Instabilidade] Gemini erro ({resultado_ia['erro']}). Aguardando 10s...")
                time.sleep(10)
                resultado_ia = extrair_dados_com_ia(texto_para_ia, token_google)
                if "erro" not in resultado_ia:
                    edital_processado_com_sucesso = True
                    break
                break

        if not edital_processado_com_sucesso:
            log_func("        [🛑 INTERRUPÇÃO CRÍTICA] Fila travada: Chaves de API indisponíveis.")
            config.supabase.table("editais").update({"escopo": "Erro: Infraestrutura de chaves de API esgotada."}).eq("url", edital["url"]).execute()
            return "bloqueio_diario"

        # --- PROCESSAMENTO E SALVAMENTO DOS DADOS ---
        prazo_texto = resultado_ia.get("datas") or resultado_ia.get("Data de Submissão", "Não encontrada")
        # Se a IA não encontrou o prazo, faz uma busca direta via Regex no texto bruto antes de definir como indisponível
        if prazo_texto in ["Não encontrada", None, ""]:
            match = re.search(r"Prazo para envio[^\n:]*:\s*(\d{2}/\d{2}/\d{4})", texto_para_ia, re.IGNORECASE)
            if match:
                prazo_texto = match.group(1)
            else:
                prazo_texto = "A consultar no edital"
        prazo_iso = resultado_ia.get("prazo_iso") or resultado_ia.get("prazo_ISO", "")
        edital_vencido = False
        hoje = datetime.now().date()

        if prazo_iso and "9999" not in prazo_iso:
            try:
                dt_limite = datetime.strptime(prazo_iso.split(" ")[0].strip(), "%Y-%m-%d").date()
                if dt_limite < hoje: edital_vencido = True
            except: pass
        
        if not edital_vencido and prazo_texto:
            match_datas = re.findall(r"\d{2}/\d{2}/\d{2,4}", str(prazo_texto))
            if match_datas:
                try:
                    data_alvo_str = match_datas[-1].strip()
                    dt_limite = datetime.strptime(data_alvo_str, "%d/%m/%y").date() if len(data_alvo_str.split("/")[-1]) == 2 else datetime.strptime(data_alvo_str, "%d/%m/%Y").date()
                    if dt_limite < hoje: edital_vencido = True
                except: pass

        if edital_vencido:
            log_func(f"        [⏩ DESCARTE PÓS-IA] Edital descartado por prazo vencido.")
            config.supabase.table("editais").update({
                "datas": "Expirado / Descartado", 
                "status_ia": "descartado_vencido"
            }).eq("url", edital["url"]).execute()
            if atualizar_tabela_func: atualizar_tabela_func()
            continue

        # CORREÇÃO: Nomes exatos das colunas do seu banco Supabase
        dados_atualizados = {
            "datas": prazo_texto,
            "pesquisa": resultado_ia.get("pesquisa") or resultado_ia.get("Linha de Pesquisa", "Não encontrada"),
            "subvencao": resultado_ia.get("subvencao") or resultado_ia.get("Linha de Subvenção", "Não encontrada"),
            "escopo": resultado_ia.get("escopo") or resultado_ia.get("Resumo do Escopo", "Não encontrado"),
            "prazo_iso": prazo_iso if (prazo_iso and "não" not in str(prazo_iso).lower()) else "9999-12-31 23:59",
            "status_ia": "CONCLUIDO"
        }
        
        config.supabase.table("editais").update(dados_atualizados).eq("url", edital["url"]).execute()
        log_func(f"        [✓] Análise da IA integrada com sucesso ao Supabase!")

        if atualizar_tabela_func: atualizar_tabela_func()
        if idx < len(itens_pendentes): time.sleep(4)
        
    return "sucesso"