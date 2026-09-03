import os
import sys
import json
from supabase import create_client

if getattr(sys, 'frozen', False):
    DIRETORIO_PAI = os.path.dirname(sys.executable)
else:
    DIRETORIO_PAI = os.path.dirname(os.path.abspath(__file__))

CAMINHO_JSON_HISTORICO = os.path.join(DIRETORIO_PAI, "resultados_editais.json")
CAMINHO_CONFIG_DINAMICO = os.path.join(DIRETORIO_PAI, "config_app.json")

DIRETORIO_PDFS = os.path.join(DIRETORIO_PAI, "editais_baixados")
os.makedirs(DIRETORIO_PDFS, exist_ok=True)

# --- VARIÁVEIS DINÂMICAS GLOBAIS ---
API_KEY_GEMINI = ""
PALAVRAS_CHAVE = ["veículo", "veículos", "combustível", "combustíveis", "Mecânico", "Mecânica", "Eficiência energética", "Biocombustíveis"]
PORTAIS_ATIVOS = {} # Dicionário de controle: {"cnpq": True, "finep": False}

PROMPT_BASE_IA = """
Você é um assistente especialista em analisar documentos institucionais, editais, chamadas públicas e escopos de projetos.
Analise o texto fornecido abaixo e extraia estritamente as seguintes 5 informações:
1. Data de Submissão no formato DD/MM/AA - DD/MM/AA (Iniciado em/Finaliza em/Indisponivel).
2. Linha de Pesquisa.
3. Resumo do Escopo Técnico.
4. Linha de Subvenção (valores/órgãos).
5. prazo_ISO no formato 'AAAA-MM-DD HH:MM'.
Responda estritamente no formato JSON com as chaves: "Data de Submissão", "Linha de Pesquisa", "Resumo do Escopo", "Linha de Subvenção", "prazo_ISO".
"""

# --- PORTAIS DE BUSCA (ESTRUTURA FIXA, NÃO MUDE OS LINK/URL) ---
SITES_ESTATICOS = {
    "CNPq - Chamadas Abertas": {
        "url": "https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao",
        "tag_titulo": "h4", "ignorar_links": []
    }
}

SITES_DINAMICOS = {
    "Fundep - Projetos": {
        "url": "https://fundep.ufmg.br/projetos",
        "seletor_card": "div.MuiGrid-item", "seletor_link": "a",
        "seletor_paginacao": "fundep", "max_paginas": 10, "ignorar_links": []
    },
    "Finep - Oportunidades": {
        "url": "https://www.finep.gov.br/oportunidades",
        "seletor_card": "tr", "seletor_link": "a",
        "seletor_paginacao": "finep", "max_paginas": 10, "ignorar_links": []
    }
}

def carregar_configuracoes_salvas():
    """Carrega os dados dinâmicos salvos pelo usuário no JSON de configuração."""
    global API_KEY_GEMINI, PALAVRAS_CHAVE, PORTAIS_ATIVOS
    if os.path.exists(CAMINHO_CONFIG_DINAMICO):
        try:
            with open(CAMINHO_CONFIG_DINAMICO, "r", encoding="utf-8") as f:
                dados = json.load(f)
                API_KEY_GEMINI = dados.get("api_key", API_KEY_GEMINI)
                PALAVRAS_CHAVE = dados.get("palavras_chave", PALAVRAS_CHAVE)
                PORTAIS_ATIVOS = dados.get("portais_ativos", {})
        except: pass

def salvar_configuracoes_usuario(nova_key, lista_palavras, dicionario_portais=None):
    """Grava as novas configurações de forma definitiva no disco."""
    global API_KEY_GEMINI, PALAVRAS_CHAVE, PORTAIS_ATIVOS
    API_KEY_GEMINI = nova_key
    PALAVRAS_CHAVE = [p.strip() for p in lista_palavras if p.strip()]
    if dicionario_portais is not None:
        PORTAIS_ATIVOS = dicionario_portais
    try:
        payload = {
            "api_key": API_KEY_GEMINI,
            "palavras_chave": PALAVRAS_CHAVE,
            "portais_ativos": PORTAIS_ATIVOS
        }
        with open(CAMINHO_CONFIG_DINAMICO, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        return True
    except: return False

carregar_configuracoes_salvas()

SUPABASE_URL = "https://sjozzxjyqkcofjmyljlv.supabase.co"
SUPABASE_KEY = "sb_publishable_r8890QkbhIEaO1A8gV9p8A_lYzTfuxI"

# Instancia a conexão com a nuvem que será usada por todo o sistema
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
