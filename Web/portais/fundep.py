import time
import requests
import re
from urllib.parse import urljoin
import web_utils

NOME_PORTAL = "Fundep - Projetos"
URL_BASE = "https://fundep.ufmg.br/projetos"
IGNORAR_LINKS = []

def varrer(log, atualizar_tabela_func):
    log(f"\n===> Verificando portal via API Next.js: {NOME_PORTAL}")
    session = requests.Session()
    
    # Cabeçalho padrão simulando um navegador real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Connection": "keep-alive",
        "Rsc": "1",  # <-- ESTE CABEÇALHO OBRIGA O NEXT.JS A RETORNAR APENAS OS DADOS BRUTOS DOS CARDS
        "Next-Router-Prefetch": "1",
        "Next-Url": "/projetos",
        "Referer": "https://fundep.ufmg.br/projetos"
    }
    
    try:
        # Aponta diretamente para a rota de busca de componentes sem precisar adivinhar o token temporário
        url_api_direta = "https://ufmg.br"
        
        log("    [+] Solicitando carga de dados assíncronos (RSC)...")
        resp = session.get(url_api_direta, headers=headers, timeout=25)
        
        if resp.status_code != 200:
            log(f"    [X] Erro de comunicação com o servidor da Fundep. Status: {resp.status_code}")
            return
            
        conteudo_rsc = resp.text
        
        # Procura pelos caminhos/slugs dos projetos dentro do retorno estruturado (ex: "/projetos/instituto-vacinas")
        padrao_slugs = re.findall(r'"/projetos/([^"]+)"', conteudo_rsc)
        
        urls_validas = set()
        for slug in padrao_slugs:
            # Filtra IDs de paginação puros (ex: "1", "2") ou caracteres de escape do JSON do Next.js
            if slug and not slug.isdigit() and "\\" not in slug and "busca" not in slug:
                url_completa = urljoin("https://ufmg.br", slug)
                urls_validas.add(url_completa)
                
        log(f"    [✓] Varredura concluída. Encontrados {len(urls_validas)} editais válidos.")

        # Envia os links para o processador central e o Supabase
        for idx, url_edital in enumerate(urls_validas, start=1):
            log(f"        [Fila {idx}/{len(urls_validas)}] Enviando: {url_edital}")
            
            # Executa a sua função padrão de cadastro em lote
            web_utils.processar_pagina_interna(
                url_edital, 
                IGNORAR_LINKS, 
                NOME_PORTAL, 
                log, 
                "Busca Ampla", 
                None
            )
            
            # Delay de segurança de 2 segundos para evitar bloqueios de firewall
            time.sleep(2.0)
            
        log(f"[✓] O motor da {NOME_PORTAL} finalizou todas as inclusões com sucesso!")
            
    except Exception as e:
        log(f"    [X] Erro crítico na execução do motor Fundep: {e}")
