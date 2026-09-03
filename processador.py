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
        # Inicializa o cliente localmente de forma isolada com a chave da vez
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
        # CORREÇÃO DE FORMATO: Gera a data de forma pura que o Supabase aceita (AAAA-MM-DD)
        hoje_str = datetime.now().date().isoformat()
        
        # 1. Busca se alguma chave já foi renovada no dia de hoje
        verificar_hoje = config.supabase.table("chaves_api").select("id").eq("ultima_renovacao", hoje_str).execute()
        
        # Se não encontrar nenhuma chave com a data de hoje, roda a auto-renovação!
        if not verificar_hoje.data:
            log_func("    [🔄 Auto-Renovação] Novo dia detectado. Reativando chaves de API uma a uma...")
            
            # Puxa TODAS as chaves cadastradas para pegar os IDs reais
            todas_as_chaves = config.supabase.table("chaves_api").select("id").execute()
            
            # Atualiza cada linha individualmente pelo ID injetando o formato isoformat() válido
            for chave_registro in todas_as_chaves.data:
                id_real = chave_registro["id"]
                config.supabase.table("chaves_api").update({
                    "status": "ativa", 
                    "ultima_renovacao": hoje_str,
                    "falhas_seguidas": 0 # Reseta também o contador de falhas por segurança
                }).eq("id", id_real).execute()
                
            log_func("    [🔄 Auto-Renovação] Todas as chaves foram reativadas com sucesso!")
            
        # 2. Continua o fluxo normal: Busca as chaves ativas do banco para a esteira usar
        resp_chaves = config.supabase.table("chaves_api").select("*").eq("status", "ativa").order("id").execute()
        lista_chaves_banco = resp_chaves.data
        
    except Exception as e_bd:
        log_func(f"    [X] Erro no motor de auto-renovação de chaves: {e_bd}")
        return "vazio"


    try:
        # 1. Recupera todas as chaves que estão marcadas como 'ativa' no Supabase
        resp_chaves = config.supabase.table("chaves_api").select("*").eq("status", "ativa").order("id").execute()
        lista_chaves_banco = resp_chaves.data
    except Exception as e_bd:
        log_func(f"    [X] Erro de rede ao buscar chaves de API: {e_bd}")
        return "vazio"

    if not lista_chaves_banco:
        log_func("    [🛑 PARADA] Todas as chaves de API cadastradas no Supabase foram esgotadas!")
        return "bloqueio_diario"

    try:
        # Puxa os editais pendentes da nuvem
        resposta = config.supabase.table("editais").select("*").eq("status_ia", "pendente").execute()
        itens_pendentes = resposta.data
    except: return "vazio"

    if not itens_pendentes:
        log_func("    [✨] Fila de IA vazia na Nuvem. Nenhum edital pendente de resumo.")
        return "vazio"

    log_func(f"\n    [ Esteira IA Global] Iniciando processamento de {len(itens_pendentes)} editais...")
    
    # Índice da chave atual que estamos usando dentro da lista de chaves ativas
    indice_chave_atual = 0

    for idx, edital in enumerate(itens_pendentes, start=1):
        log_func(f"    -> Processando item {idx} de {len(itens_pendentes)}: {edital['url']}")
        texto_para_ia = edital.get("texto_extracao", "")
        if not texto_para_ia or not texto_para_ia.strip():
            config.supabase.table("editais").update({"status_ia": "erro_sem_texto", "escopo": "Erro: Sem texto."}).eq("url", edital["url"]).execute()
            continue

        resultado_ia = None
        edital_processado_com_sucesso = False

        # Loop interno de rotatividade de chaves caso a atual falhe
        while indice_chave_atual < len(lista_chaves_banco):
            chave_obj = lista_chaves_banco[indice_chave_atual]
            token_google = chave_obj["chave"]

            resultado_ia = extrair_dados_com_ia(texto_para_ia, token_google)
            
            # Se deu certo, quebra o loop de chaves e segue em frente
            if "erro" not in resultado_ia:
                edital_processado_com_sucesso = True
                break
                
            err_msg = resultado_ia["erro"].upper()
            # SE A CHAVE ATUAL ESTOUROU A COTA DIÁRIA OU BLOQUEOU TOTALMENTE
            if "RESOURCE_EXHAUSTED" in err_msg or "QUOTA" in err_msg or "429" in err_msg:
                log_func(f"        [🚨 CHAVE ESGOTADA] Chave ID {chave_obj['id']} atingiu o limite de cota. Desativando e rotacionando...")
                
                # Desativa a chave direto no Supabase para nenhum outro usuário tentar usar ela hoje
                config.supabase.table("chaves_api").update({"status": "esgotada"}).eq("id", chave_obj["id"]).execute()
                
                # Pula para a próxima chave da lista
                indice_chave_atual += 1
                if indice_chave_atual < len(lista_chaves_banco):
                    log_func(f"        [🔄 Rotatividade] Mudando para a Chave de API ID {lista_chaves_banco[indice_chave_atual]['id']}...")
                continue
            else:
                # Se for outro erro temporário de minuto (RPM) ou instabilidade 503, aguarda um pouco na mesma chave
                log_func(f"        [⚠️ Instabilidade] Gemini instável ({resultado_ia['erro']}). Aguardando 10s...")
                time.sleep(10)
                resultado_ia = extrair_dados_com_ia(texto_para_ia, token_google)
                if "erro" not in resultado_ia:
                    edital_processado_com_sucesso = True
                    break
                break
        # Se varreu todas as chaves e nenhuma funcionou, desliga o atualizador cíclico do app
        if not edital_processado_com_sucesso:
            log_func("        [🛑 INTERRUPÇÃO CRÍTICA] Fila travada: Todas as chaves ativas falharam permanentemente.")
            config.supabase.table("editais").update({"escopo": "Erro: Infraestrutura de chaves de API esgotada."}).eq("url", edital["url"]).execute()
            return "bloqueio_diario"

        # --- SALVAMENTO DOS DADOS COM SUCESSO ---
        prazo_texto = resultado_ia.get("Data de Submissão", "Não encontrada")
        prazo_iso = resultado_ia.get("prazo_ISO", "")
        edital_vencido = False
        hoje = datetime.now().date()

        if prazo_iso and "9999" not in prazo_iso:
            try:
                dt_limite = datetime.strptime(prazo_iso.split(" ")[0].strip(), "%Y-%m-%d").date()
                if dt_limite < hoje: edital_vencido = True
            except: pass
        
        if not edital_vencido and prazo_texto:
            match_datas = re.findall(r"\d{2}/\d{2}/\d{2,4}", prazo_texto)
            if match_datas:
                try:
                    data_alvo_str = match_datas[-1].strip()
                    dt_limite = datetime.strptime(data_alvo_str, "%d/%m/%y").date() if len(data_alvo_str.split("/")[-1]) == 2 else datetime.strptime(data_alvo_str, "%d/%m/%Y").date()
                    if dt_limite < hoje: edital_vencido = True
                except: pass

        if edital_vencido:
            log_func(f"        [⏩ DESCARTE PÓS-IA] Edital descartado por prazo vencido.")
            config.supabase.table("editais").update({"datas": "Expirado / Descartado", "status_ia": "descartado_vencido", "texto_extracao": None}).eq("url", edital["url"]).execute()
            if atualizar_tabela_func: atualizar_tabela_func()
            continue

        dados_atualizados = {
            "datas": prazo_texto,
            "pesquisa": resultado_ia.get("Linha de Pesquisa", "Não encontrada"),
            "subvencao": resultado_ia.get("Linha de Subvenção", "Não encontrada"),
            "escopo": resultado_ia.get("Resumo do Escopo", "Não encontrado"),
            "prazo_ISO": prazo_iso if (prazo_iso and "não" not in prazo_iso.lower()) else "9999-12-31 23:59",
            "status_ia": "concluido", "texto_extracao": None
        }
        config.supabase.table("editais").update(dados_atualizados).eq("url", edital["url"]).execute()
        log_func(f"        [✓] Análise da IA integrada com sucesso ao Supabase!")

        if atualizar_tabela_func: atualizar_tabela_func()
        if idx < len(itens_pendentes): time.sleep(6)
        
    return "sucesso"
