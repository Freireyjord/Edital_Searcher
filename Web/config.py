import os
import sys
from supabase import create_client

# Define os diretórios de execução da aplicação de forma dinâmica
if getattr(sys, 'frozen', False):
    DIRETORIO_PAI = os.path.dirname(sys.executable)
else:
    DIRETORIO_PAI = os.path.dirname(os.path.abspath(__file__))

# Pasta temporária para armazenamento dos PDFs baixados
DIRETORIO_PDFS = os.path.join(DIRETORIO_PAI, "editais_baixados")
os.makedirs(DIRETORIO_PDFS, exist_ok=True)

# --- PROMPT ATUALIZADO: RESTRITIVO CONTRA TAGS GENÉRICAS E NOMES DE PORTAIS ---

PROMPT_BASE_IA = """
Você é especialista em análise de editais públicos de inovação, tecnologia e pesquisa.
Extraia somente informações explicitamente existentes no texto fornecido. Nunca invente valores.
Caso não encontre uma informação de jeito nenhum, retorne o campo correspondente como "Não encontrada".

Responda ESTRITAMENTE com um JSON válido (sem markdown, sem blocos extras).

DIRETRIZES DE CRIAÇÃO DAS TAGS:
Identifique de 3 a 10 palavras-chave ou termos técnicos específicos e profundos que definem o CONTEÚDO TÉCNICO E ESCOPO DO PROJETO deste edital (ex: inteligência artificial, biocombustíveis, previdência complementar, smart cities, telecomunicações). 

Proibições Absolutas:
- NUNCA inclua o nome do portal de origem (como Finep, CNPq, Fundep, Governo Federal).
- NUNCA inclua nomes de órgãos públicos, ministérios ou siglas de agências.
- NUNCA inclua termos genéricos de processo burocrático (como edital, chamada, processo seletivo, convênio, termo de referência).

Insira esses termos técnicos no campo "tags_ia" obrigatoriamente separados por vírgula.

Siga estritamente esta estrutura para o JSON:
{
  "datas": "Texto resumido com o prazo limite de submissão do edital no formato 'DD-MM-YY - DD-MM-YY' ou caso ache so a data de abertura 'Iniciado em DD-MM-YY' ou caso so a data de encerramento 'Até DD-MM-YY",
  "prazo_iso": "Data limite de submissão formatada em YYYY-MM-DD (se encontrada)",
  "vigencia_projeto": "Texto resumido com o período/vigência do projeto (ex: Data de início, término ou prorrogações encontradas)",
  "fim_projeto_iso": "Data de término ou prorrogação final do projeto formatada em YYYY-MM-DD (se encontrada)",
  "pesquisa": "Descrição sucinta das linhas de pesquisa aceitas",
  "escopo": "Resumo detalhado do objetivo e escopo do edital",
  "subvencao": "Informações sobre recursos financeiros, subvenção econômica ou financiamento",
  "tags_ia": "termo1, termo2, termo3, ..."
}
"""


# Configurações padrão utilizadas pelos robôs de varredura ampla
PALAVRAS_CHAVE = [""]
PORTAIS_ATIVOS = {"cnpq": False, "finep": False, "fundep": True}

# --- CONEXÃO BANCO DE DADOS NUVEM (SUPABASE) ---
SUPABASE_URL = "https://sjozzxjyqkcofjmyljlv.supabase.co"
SUPABASE_KEY = "sb_publishable_r8890QkbhIEaO1A8gV9p8A_lYzTfuxI"

# Inicializa o cliente do banco de dados para os robôs
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
