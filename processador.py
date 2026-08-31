import os, json, requests, time, sys, pytesseract
from pypdf import PdfReader
from pdf2image import convert_from_path
from google import genai
from google.genai import types
from google.genai.errors import APIError
import config

# --- MAPEAMENTO DO TESSERACT PORTÁTIL PARA O PYINSTALLER ---
if getattr(sys, 'frozen', False):
    # Se o app estiver rodando compilado (.exe), busca na pasta temporária do PyInstaller
    DIRETORIO_TESSERACT = os.path.join(sys._MEIPASS, "tesseract_bin")
else:
    # Se estiver rodando o código fonte em desenvolvimento, busca na pasta local do projeto
    DIRETORIO_TESSERACT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesseract_bin")

# Configura o caminho do executável do Tesseract e a pasta de idiomas de forma explícita
caminho_exe_tesseract = os.path.join(DIRETORIO_TESSERACT, "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = caminho_exe_tesseract

# Aponta para a pasta interna 'tessdata' que contém o arquivo 'por.traineddata'
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

def extrair_dados_com_ia(texto_analise):
    """Envia o texto coletado de forma isolada e segura por thread."""
    try:
        client = genai.Client(api_key=config.API_KEY_GEMINI)
    except Exception as e:
        return {"erro": f"Falha na Inicialização da API: {e}"}

    prompt_completo = f"{config.PROMPT_BASE_IA}\n\nTexto do Edital para Análise:\n{texto_analise}"
    
    try:
        resposta = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt_completo,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(resposta.text)
    except APIError as e:
        return {"erro": f"API Limite Excedido (429) ou Indisponível: {e}"}
    except Exception as e:
        return {"erro": f"Erro inesperado: {e}"}

def consumir_fila_pendente_ia(log_func):
    """Varre o JSON histórico procurando registros com status_ia='pendente' e executa a IA sequencialmente."""
    arq = config.CAMINHO_JSON_HISTORICO
    if not os.path.exists(arq): return

    try:
        with open(arq, "r", encoding="utf-8") as f: hist = json.load(f)
    except: return

    # Filtra os editais que aguardam análise
    itens_pendentes = [i for i in hist if i.get("status_ia") == "pendente"]
    if not itens_pendentes:
        log_func("    [✨] Fila de IA vazia. Nenhum edital pendente de resumo.")
        return

    log_func(f"\n    [ Esteira IA] Localizados {len(itens_pendentes)} novos editais na fila de análise. Iniciando chamadas...")

    for idx, edital in enumerate(itens_pendentes, start=1):
        log_func(f"    -> Processando item {idx} de {len(itens_pendentes)}: {edital['url']}")
        
        texto_para_ia = edital.get("texto_extracao", "")
        if not texto_para_ia.strip():
            edital["status_ia"] = "erro_sem_texto"
            edital["escopo"] = "Erro: Sem texto para análise."
            continue

        # Realiza a chamada real para a IA
        resultado_ia = extrair_dados_com_ia(texto_para_ia)

        if "erro" in resultado_ia:
            log_func(f"        [⚠️] Falha no Gemini ao processar este item: {resultado_ia['erro']}")
            # Mantém como pendente para tentar na próxima sincronização ou marca com erro provisório
            edital["escopo"] = f"Erro no processamento da API (Cota Excedida). Será re-tentado automaticamente."
            # Interrompe o processamento da fila inteira se for erro de limite para poupar processamento
            if "429" in resultado_ia["erro"]:
                log_func("        [🛑] Fila interrompida devido ao limite de cota de minuto atingido.")
                break
        else:
            # IA respondeu com sucesso: Atualiza os dados do registro mapeado
            edital["datas"] = resultado_ia.get("Data de Submissão", "Não encontrada")
            edital["pesquisa"] = resultado_ia.get("Linha de Pesquisa", "Não encontrada")
            edital["subvencao"] = resultado_ia.get("Linha de Subvenção", "Não encontrada")
            edital["escopo"] = resultado_ia.get("Resumo do Escopo", "Não encontrado")
            
            prazo = resultado_ia.get("prazo_ISO", "")
            edital["prazo_ISO"] = prazo if (prazo and "não" not in prazo.lower()) else "9999-12-31 23:59"
            
            edital["status_ia"] = "concluido" # Altera status para não re-processar
            edital.pop("texto_extracao", None) # Remove o texto bruto pesado do JSON final para economizar espaço em disco
            log_func(f"        [✓] Análise da IA integrada com sucesso!")

        # Grava o progresso no JSON imediatamente a cada item concluído
        with open(arq, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=4, ensure_ascii=False)

        # CADÊNCIA CRÍTICA ANTI-429: Pausa forçada de 6 segundos entre requisições (Garanta no máximo 10 requisições por minuto)
        if idx < len(itens_pendentes):
            time.sleep(6)
