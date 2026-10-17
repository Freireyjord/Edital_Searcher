"""
Regras de filtragem/ordenação dos editais exibidos na tabela (sem dependência de Tkinter).

Mantém o comportamento original da UI:
- só aparecem editais CONCLUIDOS e ainda abertos;
- editais SEM prazo definido (prazo_iso NULL) continuam aparecendo;
- ordenação: mais tags do usuário encontradas primeiro; empate -> prazo mais próximo.
"""
import re
import unicodedata
from datetime import date, datetime

STATUS_VISIVEL = "concluido"
_SEM_PRAZO = "9999-12-31 23:59"   # só para ordenação (e compatibilidade com registros antigos)


def normalizar_texto(texto):
    """Remove acentos, converte para minúsculo e limpa espaços extras."""
    if not texto:
        return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


_SEPARADOR_PORTAL = re.compile(r"\s+[-–—]\s+")


def nome_curto_portal(portal):
    """'CNPq - Chamadas Abertas' -> 'CNPq'. Sem separador, devolve o nome inteiro."""
    return _SEPARADOR_PORTAL.split(str(portal or "").strip(), maxsplit=1)[0].strip()


def chave_do_portal(portal):
    """
    Chave usada nos filtros e salva no config_app.json. Compatível com as antigas
    ('cnpq', 'finep', 'fundep', 'petrobras'); portais novos entram sozinhos.
    """
    return nome_curto_portal(portal).lower()


def portais_disponiveis(editais):
    """[(chave, rótulo)] em ordem alfabética, descobertos a partir dos editais carregados do Supabase."""
    achados = {}
    for edital in editais or []:
        nome = nome_curto_portal(edital.get("portal"))
        if nome:
            achados.setdefault(nome.lower(), nome)
    return sorted(achados.items(), key=lambda par: par[1].lower())


def _parse_data_iso(valor):
    """'YYYY-MM-DD[ T]HH:MM' -> date | None. Trata NULL e a sentinela antiga 9999."""
    if not valor or "9999" in str(valor):
        return None
    try:
        return datetime.strptime(str(valor).strip().replace("T", " ").split(" ")[0], "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_data_br(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except ValueError:
        return None


def _texto_prazo(edital, dt_item):
    """Texto exibido na coluna de prazo."""
    if dt_item:
        return f"Até {dt_item.strftime('%d/%m/%Y')}"

    bruto = edital.get("datas") or ""
    baixo = bruto.lower()
    if "contínuo" in baixo or "continuo" in baixo or "fluxo" in baixo:
        return "Fluxo Contínuo"

    texto = bruto.replace("Envio de propostas ", "").strip()
    for corte in (", às", ", as"):
        if corte in texto:
            texto = texto.split(corte)[0]
            break
    return texto.strip() or "A consultar"


def _chave_prazo(edital):
    return edital.get("prazo_iso") or _SEM_PRAZO


def aplicar_filtros(editais, portais=None, data_min="", data_max="", palavras_chave=None, hoje=None):
    """
    Retorna lista de (qtd_tags_encontradas, valores_das_colunas, edital),
    já ordenada para exibição.
    """
    hoje = hoje or date.today()
    dt_min, dt_max = _parse_data_br(data_min), _parse_data_br(data_max)
    palavras = [p for p in (palavras_chave or []) if p and p.strip()]
    termos_usuario = [normalizar_texto(p) for p in palavras]
    termos_usuario = [t for t in termos_usuario if t]

    resultado = []
    for edital in sorted(editais, key=_chave_prazo):
        if str(edital.get("status_ia") or "").strip().lower() != STATUS_VISIVEL:
            continue

        portal = edital.get("portal") or "N/A"
        if portais and not portais.get(chave_do_portal(portal), True):
            continue

        dt_item = _parse_data_iso(edital.get("prazo_iso"))
        if dt_item and (dt_item < hoje or (dt_min and dt_item < dt_min) or (dt_max and dt_item > dt_max)):
            continue

        titulo_norm = normalizar_texto(edital.get("titulo", ""))
        tags_edital = [normalizar_texto(t) for t in (edital.get("tags_ia") or "").split(",") if t.strip()]

        encontradas = []
        for palavra in palavras:
            p_norm = normalizar_texto(palavra)
            if not p_norm:
                continue
            if p_norm in titulo_norm or any(p_norm in t or t in p_norm for t in tags_edital):
                if palavra not in encontradas:
                    encontradas.append(palavra)

        if termos_usuario and not encontradas:
            continue

        valores = {
            "titulo": edital.get("titulo") or "Edital sem título",
            "portal": portal,
            "datas": _texto_prazo(edital, dt_item),
            "vigencia_projeto": edital.get("vigencia_projeto") or "N/A",
            "palavra_chave": ", ".join(encontradas) if encontradas else "Geral / Amplo",
        }
        resultado.append((len(encontradas), valores, edital))

    resultado.sort(key=lambda x: x[0], reverse=True)   # estável: mantém ordem de prazo nos empates
    return resultado