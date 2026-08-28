import os, json, requests
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from google import genai
from google.genai import types
import config

client = genai.Client(api_key=config.API_KEY_GEMINI)

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

def salvar_resultado_no_historico(portal, url, dados_ia, nome_pdf=""):
    # CORREÇÃO: Usa o caminho absoluto unificado mapeado pelo config
    arq = config.CAMINHO_JSON_HISTORICO
    hist = []
    if os.path.exists(arq):
        try:
            with open(arq, "r", encoding="utf-8") as f: hist = json.load(f)
        except: pass
    
    prazo = dados_ia.get("prazo_ISO", "")
    if not prazo or "não" in prazo.lower(): prazo = "9999-12-31 23:59"
    
    # Salva o caminho relativo do PDF para a interface conseguir ler
    novo = {
        "portal": portal, "url": url, "pdf": f"editais_baixados/{nome_pdf}" if nome_pdf else "",
        "datas": dados_ia.get("Data de Submissão", "Não encontrada"),
        "pesquisa": dados_ia.get("Linha de Pesquisa", "Não encontrada"),
        "subvencao": dados_ia.get("Linha de Subvenção", "Não encontrada"),
        "escopo": dados_ia.get("Resumo do Escopo", "Não encontrado"),
        "prazo_ISO": prazo
    }
    if not any(i["url"] == url for i in hist):
        hist.append(novo)
        with open(arq, "w", encoding="utf-8") as f: json.dump(hist, f, indent=4, ensure_ascii=False)

def extrair_dados_com_ia(texto_analise):
    """Envia o texto coletado para a engenharia de prompt unificada no config."""
    print("    [✨] Enviando informações para análise e resumo da Inteligência Artificial...")
    
    # CORREÇÃO: Concatena a regra estrutural do config com o texto bruto para análise
    prompt_completo = f"{config.PROMPT_BASE_IA}\n\nTexto do Edital para Análise:\n{texto_analise}"
    
    try:
        resposta = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt_completo,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        return json.loads(resposta.text)
    except Exception as e:
        print(f"    [X] Erro ao consultar a API do Gemini: {e}")
        return {
            "Data de Submissão": "Erro no processamento da API",
            "Linha de Pesquisa": "Erro no processamento da API",
            "Resumo do Escopo": "Erro no processamento da API",
            "Linha de Subvenção": "Erro no processamento da API",
            "prazo_ISO": "9999-12-31 23:59" # CORREÇÃO: Evita quebra de dicionário
        }
