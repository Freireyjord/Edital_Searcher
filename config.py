import os
import sys
import json
from supabase import create_client

# Define os diretórios de execução da aplicação (compatível com PyInstaller)
if getattr(sys, 'frozen', False):
    DIRETORIO_PAI = os.path.dirname(sys.executable)
else:
    DIRETORIO_PAI = os.path.dirname(os.path.abspath(__file__))

# Arquivo JSON exclusivo para preferências da interface (tags/filtros locais)
CAMINHO_CONFIG_DINAMICO = os.path.join(DIRETORIO_PAI, "config_app.json")

# Pasta para armazenamento local dos PDFs baixados
DIRETORIO_PDFS = os.path.join(DIRETORIO_PAI, "editais_baixados")
os.makedirs(DIRETORIO_PDFS, exist_ok=True)

# Prompt padrão utilizado pelo processador de IA
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

# --- PREFERÊNCIAS LOCAIS DO USUÁRIO ---
PALAVRAS_CHAVE = [
    "veículo", "veículos", "combustível", "combustíveis", 
    "Mecânico", "Mecânica", "Eficiência energética", "Biocombustíveis"
]
PORTAIS_ATIVOS = {"cnpq": True, "finep": True, "fundep": True}


def carregar_configuracoes_salvas():
    """Carrega as preferências locais salvas pelo usuário no JSON de configuração."""
    global PALAVRAS_CHAVE, PORTAIS_ATIVOS
    if os.path.exists(CAMINHO_CONFIG_DINAMICO):
        try:
            with open(CAMINHO_CONFIG_DINAMICO, "r", encoding="utf-8") as f:
                dados = json.load(f)
                PALAVRAS_CHAVE = dados.get("palavras_chave", PALAVRAS_CHAVE)
                PORTAIS_ATIVOS = dados.get("portais_ativos", PORTAIS_ATIVOS)
        except Exception as e:
            print(f"Erro ao carregar configuracoes locais: {e}")


def salvar_configuracoes_usuario(lista_palavras, dicionario_portais=None):
    """Grava as novas palavras-chave e portais ativos de forma definitiva no disco."""
    global PALAVRAS_CHAVE, PORTAIS_ATIVOS
    PALAVRAS_CHAVE = [p.strip() for p in lista_palavras if p.strip()]
    
    if dicionario_portais is not None:
        PORTAIS_ATIVOS = dicionario_portais

    try:
        payload = {
            "palavras_chave": PALAVRAS_CHAVE,
            "portais_ativos": PORTAIS_ATIVOS
        }
        with open(CAMINHO_CONFIG_DINAMICO, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar configuracoes: {e}")
        return False


# Carrega as preferências na inicialização do módulo
carregar_configuracoes_salvas()

# --- CONEXÃO BANCO DE DADOS NUVEM (SUPABASE) ---
SUPABASE_URL = "https://sjozzxjyqkcofjmyljlv.supabase.co"
SUPABASE_KEY = "sb_publishable_r8890QkbhIEaO1A8gV9p8A_lYzTfuxI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)