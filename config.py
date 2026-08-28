import os
import sys
import json

# --- MAPEAMENTO BLINDADO DE DIRETÓRIOS ---
if getattr(sys, 'frozen', False):
    DIRETORIO_PAI = os.path.dirname(sys.executable)
else:
    DIRETORIO_PAI = os.path.dirname(os.path.abspath(__file__))

CAMINHO_JSON_HISTORICO = os.path.join(DIRETORIO_PAI, "resultados_editais.json")
CAMINHO_CONFIG_DINAMICO = os.path.join(DIRETORIO_PAI, "config_app.json")

# --- CENTRALIZAÇÃO DOS DIRETÓRIOS DE PDF ---
DIRETORIO_PDFS = os.path.join(DIRETORIO_PAI, "editais_baixados")
os.makedirs(DIRETORIO_PDFS, exist_ok=True)

# --- CONFIGURAÇÕES PADRÃO (FALLBACK) ---
API_KEY_GEMINI = "SUA_CHAVE_AQUI"
PALAVRAS_CHAVE = ["veículo", "veículos", "combustível", "combustíveis", "Mecânico", "Mecânica", "Eficiência energética", "Biocombustíveis"]

# --- PROMPT BASE DA IA DO GEMINI CENTRALIZADO ---
PROMPT_BASE_IA = """
Você é um assistente especialista em analisar documentos institucionais, editais, chamadas públicas e escopos de projetos.
Analise o texto fornecido abaixo e extraia estritamente as seguintes 5 informações:

1.  Data de Submissão (Se for um edital aberto, extraia o período ou data limite de envio. Se for um projeto institucional já ativo, extraia a Data de Início e Término Previsto), 
    por favor no formato DD/MM/AA - DD/MM/AA (caso so encontre a data de inicio escreva: Iniciado em DD/MM/AAAA, e caso encontre apenas a data de finalização escreva: Finaliza em DD/MM/AAAA, 
    e caso não encontre nenhuma das duas escreva apenas: Indisponivel).
2.  Linha de Pesquisa (Quais são as áreas temáticas, eixos fundamentais, divisões de atuação ou setores aceitos/envolvidos).
3.  Resumo do Escopo Técnico (Um resumo real, explicativo, coeso e humano de qual é o objetivo prático e a aplicação técnica descrita).
4.  Linha de Subvenção (Informações sobre valores financeiros totais, orçamento por projeto, bolsas, bolsas concedidas ou o nome dos órgãos Financiadores/Apoiadores envolvidos).
5.  prazo_ISO (Converta a data limite final encontrada estritamente para o formato 'AAAA-MM-DD HH:MM'. Se não houver horário explícito, assuma '23:59'. Se for fluxo contínuo ou sem prazo, retorne '9999-12-31 23:59').

Regras estritas:
- Forneça um RESUMO interpretado por você de forma humana e legível. Não faça apenas recortes mecânicos ou colagens de frases soltas.
- Se a informação não constar de nenhuma forma no documento ou na página, escreva "Não encontrada".
- Responda estritamente no formato JSON estruturado com as chaves exatas: 
  "Data de Submissão", "Linha de Pesquisa", "Resumo do Escopo", "Linha de Subvenção", "prazo_ISO".
"""

# --- PORTAIS DE BUSCA (ESTRUTURA FIXA) ---
SITES_ESTATICOS = {
    "CNPq - Chamadas Abertas": {
        "url": "https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao",
        "tag_titulo": "h4",
        "ignorar_links": []
    }
}

SITES_DINAMICOS = {
    "Fundep - Projetos": {
        "url": "https://fundep.ufmg.br/projetos",
        "seletor_card": "div.MuiGrid-item",
        "seletor_link": "a",
        "seletor_paginacao": "fundep",
        "max_paginas": 5,
        "ignorar_links": []
    },
    "Finep - Oportunidades": {
        "url": "https://www.finep.gov.br/oportunidades",
        "seletor_card": "tr",
        "seletor_link": "a",
        "seletor_paginacao": "finep",
        "max_paginas": 5,
        "ignorar_links": []
    }
}

def carregar_configuracoes_salvas():
    """Carrega os dados dinâmicos salvos pelo usuário no JSON de configuração."""
    global API_KEY_GEMINI, PALAVRAS_CHAVE
    if os.path.exists(CAMINHO_CONFIG_DINAMICO):
        try:
            with open(CAMINHO_CONFIG_DINAMICO, "r", encoding="utf-8") as f:
                dados = json.load(f)
                API_KEY_GEMINI = dados.get("api_key", API_KEY_GEMINI)
                PALAVRAS_CHAVE = dados.get("palavras_chave", PALAVRAS_CHAVE)
        except:
            pass

def salvar_configuracoes_usuario(nova_key, lista_palavras):
    """Grava as novas configurações de forma definitiva no disco."""
    global API_KEY_GEMINI, PALAVRAS_CHAVE
    API_KEY_GEMINI = nova_key
    PALAVRAS_CHAVE = [p.strip() for p in lista_palavras if p.strip()]
    try:
        with open(CAMINHO_CONFIG_DINAMICO, "w", encoding="utf-8") as f:
            json.dump({"api_key": API_KEY_GEMINI, "palavras_chave": PALAVRAS_CHAVE}, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

# Carrega os dados salvos imediatamente ao importar o módulo
carregar_configuracoes_salvas()
