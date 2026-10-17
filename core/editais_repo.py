"""Consultas ao Supabase usadas pela tabela de editais (rede; chamar fora da thread da UI)."""
from datetime import date
from core import config

# Só o necessário para listar. NUNCA usar select("*"): a tabela guarda o texto bruto dos
# editais e PDFs (texto_extracao, centenas de milhares de caracteres por linha).
COLUNAS_LISTA = "url,portal,titulo,datas,prazo_iso,vigencia_projeto,tags_ia,status_ia"
COLUNAS_DETALHE = "escopo,pesquisa,subvencao"

TAMANHO_PAGINA = 1000   # limite padrão do PostgREST por requisição


def buscar_editais_visiveis():
    """
    Editais CONCLUIDOS e ainda abertos (ou sem prazo), paginando para não
    esbarrar no limite de 1000 linhas por consulta.
    """
    hoje = date.today().isoformat()
    editais, inicio = [], 0
    while True:
        resposta = (
            config.supabase.table("editais")
            .select(COLUNAS_LISTA)
            .eq("status_ia", "CONCLUIDO")
            .or_(f"prazo_iso.is.null,prazo_iso.gte.{hoje}")
            .order("created_at", desc=True)
            .order("url")                       # desempate: paginação estável
            .range(inicio, inicio + TAMANHO_PAGINA - 1)
            .execute()
        )
        lote = resposta.data or []
        editais.extend(lote)
        if len(lote) < TAMANHO_PAGINA:
            return editais
        inicio += TAMANHO_PAGINA


def buscar_detalhe(url):
    """Resumo, linha de pesquisa e verba de UM edital (carregado ao selecionar a linha)."""
    resposta = (
        config.supabase.table("editais")
        .select(COLUNAS_DETALHE)
        .eq("url", url)
        .limit(1)
        .execute()
    )
    return resposta.data[0] if resposta.data else {}