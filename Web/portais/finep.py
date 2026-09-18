import time
import requests
from urllib.parse import urljoin
import web_utils

NOME_PORTAL = "Finep - Oportunidades"
URL_REAL_FINEP = "https://www.finep.gov.br/oportunidades"

# Barramento REST oficial oculto que fornece os dados brutos dos cards para o componente React
URL_REST_API = "https://finep.gov.br"

def varrer(log, atualizar_tabela_func=None):
    log(f"\n===> [INÍCIO REAL] Iniciando varredura via Barramento REST de Dados (Sem Selenium) na Finep")
    log(f"    [DOMÍNIO SEGURO] Alvo fixado no ecossistema: {URL_REAL_FINEP}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Referer": URL_REAL_FINEP,
        "Origin": "https://www.finep.gov.br"
    }
    
    urls_validas = set()  # Acumulador unificado anti-duplicados (Padrão Fundep/CNPq)
    inicio_triagem = time.time()
    
    # Começamos na página 1 e avançamos dinamicamente (Loop infinito controlado)
    pagina_atual = 1

    while True:
        log(f"    [API JSON] Solicitando e decodificando registros da página {pagina_atual}...")
        
        # Parâmetros de paginação oficiais aceitos pela rota REST do componente
        parametros = {
            "page": str(pagina_atual),
            "size": "8",  # Quantidade padrão de cards que o site exibe por página
            "situacao": "aberta"  # Filtra apenas chamadas ativas/abertas
        }
        
        try:
            resp = requests.get(URL_REST_API, headers=headers, params=parametros, timeout=25)
            
            if resp.status_code != 200:
                log(f"        [ℹ️] Fim da paginação ou limite atingido na página {pagina_atual} (Status {resp.status_code}).")
                break
                
            dados_json = resp.json()
            
            # O Liferay armazena o array de dados dentro do nó 'items' ou 'content'
            oportunidades = dados_json.get("items", []) or dados_json.get("content", [])
            
            # Caso a API mude a estrutura e envie a lista direto na raiz
            if not oportunidades and isinstance(dados_json, list):
                oportunidades = dados_json
                
            # Condição de parada crucial: Se a página JSON veio sem nenhum edital, a paginação acabou
            if not oportunidades or len(oportunidades) == 0:
                log(f"        [✓] Página {pagina_atual} retornou vazia. Fim dos registros alcançado.")
                break
                
            links_na_pagina = 0
            for item in oportunidades:
                # O Liferay armazena a URL interna nas chaves 'url', 'href' ou 'link'
                href = item.get("url") or item.get("href") or item.get("link")
                if not href:
                    continue
                    
                # Força a reconstrução absoluta da URL usando a raiz correta
                url_completa = urljoin("https://www.finep.gov.br/", str(href).strip())
                
                if url_completa.rstrip("/") not in [URL_REAL_FINEP.rstrip("/"), "https://www.finep.gov.br", "https://finep.gov.br"]:
                    urls_validas.add(url_completa)
                    links_na_pagina += 1
                    
            log(f"        [+] Sucesso: Extraídos {links_na_pagina} editais na página {pagina_atual}.")
            
            # Avança para a próxima página do lote
            pagina_atual += 1
            
        except Exception as e:
            log(f"        [X] Erro de parsing ou fim de dados na página {pagina_atual}: {e}")
            break
            
        # Delay protocolar amigável de 1 segundo para evitar bloqueios de IP (WAF)
        time.sleep(1.0)

    log(f"\n    [✓] Triagem concluída em {time.time() - inicio_triagem:.2f}s! Total de editais únicos localizados: {len(urls_validas)}")

    if len(urls_validas) == 0:
        log("    [⚠️ CRÍTICO] Falha na mineração. Nenhuma oportunidade legítima foi encontrada no JSON da API.")
        return

    # Despacha a fila purificada diretamente para o Supabase via web_utils (Padrão Fundep)
    for idx, url_edital in enumerate(urls_validas, start=1):
        log(f"        [Fila {idx}/{len(urls_validas)}] Despachando para processamento: {url_edital}")
        
        web_utils.processar_pagina_interna(
            url_edital, 
            [], 
            NOME_PORTAL, 
            log, 
            "Busca Ampla", 
            None
        )
        time.sleep(2.0)
        
    log(f"[✓] O motor da {NOME_PORTAL} finalizou com sucesso!")
