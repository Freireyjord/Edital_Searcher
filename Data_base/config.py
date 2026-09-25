import os, sys, json

from supabase import create_client

if getattr(sys, 'frozen', False):
    DIRETORIO_PAI = os.path.dirname(sys.executable)
else:
    DIRETORIO_PAI = os.path.dirname(os.path.abspath(__file__))

CAMINHO_CONFIG_DINAMICO = os.path.join(DIRETORIO_PAI, "config_app.json")

# Prefs Padrão
PALAVRAS_CHAVE = ["veículo", "veículos", "combustível", "combustíveis", "Mecânico", "Mecânica"]
PORTAIS_ATIVOS = {"cnpq": True, "finep": True, "fundep": True, "petrobras": True}

# 🔥 NOVAS VARIÁVEIS EXCLUSIVAS DO RELATÓRIO
EMAIL_RELATORIO = ""
FILTRAR_RELATORIO_POR_TAGS = False
TAGS_RELATORIO = [] # Nova lista separada de monitoramento por e-mail


def carregar_configuracoes_salvas():
    global PALAVRAS_CHAVE, PORTAIS_ATIVOS, EMAIL_RELATORIO, FILTRAR_RELATORIO_POR_TAGS, TAGS_RELATORIO
    if os.path.exists(CAMINHO_CONFIG_DINAMICO):
        try:
            with open(CAMINHO_CONFIG_DINAMICO, "r", encoding="utf-8") as f:
                dados = json.load(f)
                PALAVRAS_CHAVE = dados.get("palavras_chave", PALAVRAS_CHAVE)
                PORTAIS_ATIVOS = dados.get("portais_ativos", PORTAIS_ATIVOS)
                EMAIL_RELATORIO = dados.get("email_relatorio", EMAIL_RELATORIO)
                FILTRAR_RELATORIO_POR_TAGS = dados.get("filtrar_relatorio_por_tags", FILTRAR_RELATORIO_POR_TAGS)
                TAGS_RELATORIO = dados.get("tags_relatorio", TAGS_RELATORIO) # 🔥 Adicionado
        except Exception as e:
            print(f"Erro ao carregar configuracoes locais: {e}")


def salvar_configuracoes_usuario(lista_palavras, dicionario_portais=None, email_destino=None, filtrar_tags=None, lista_tags_relatorio=None):
    global PALAVRAS_CHAVE, PORTAIS_ATIVOS, EMAIL_RELATORIO, FILTRAR_RELATORIO_POR_TAGS, TAGS_RELATORIO
    
    PALAVRAS_CHAVE = [p.strip() for p in lista_palavras if p.strip()]
    if dicionario_portais is not None: PORTAIS_ATIVOS = dicionario_portais
    if email_destino is not None: EMAIL_RELATORIO = email_destino.strip()
    if filtrar_tags is not None: FILTRAR_RELATORIO_POR_TAGS = filtrar_tags
    if lista_tags_relatorio is not None: TAGS_RELATORIO = [t.strip() for t in lista_tags_relatorio if t.strip()] # 🔥 Adicionado

    try:
        payload = {
            "palavras_chave": PALAVRAS_CHAVE,
            "portais_ativos": PORTAIS_ATIVOS,
            "email_relatorio": EMAIL_RELATORIO,
            "filtrar_relatorio_por_tags": FILTRAR_RELATORIO_POR_TAGS,
            "tags_relatorio": TAGS_RELATORIO # 🔥 Salva no arquivo JSON
        }
        with open(CAMINHO_CONFIG_DINAMICO, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar configuracoes: {e}")
        return False

carregar_configuracoes_salvas()

# --- CONEXÃO BANCO DE DADOS NUVEM (SUPABASE) ---
SUPABASE_URL = "https://sjozzxjyqkcofjmyljlv.supabase.co"
SUPABASE_KEY = "sb_publishable_r8890QkbhIEaO1A8gV9p8A_lYzTfuxI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
