import time
import sys
import os
import traceback
import importlib
from datetime import datetime

# Garante que o script localize os submódulos da pasta atual de forma nativa
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
import processador

def log_worker(mensagem):
    """Exibe logs estruturados com carimbo de data e hora no terminal de execução."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {mensagem}")
    sys.stdout.flush()

def executar_ciclo_varredura():
    log_worker("=== INICIANDO CICLO DE VARREDURA AUTOMATIZADA DE PORTAIS ===")
    
    # --- NOVA ROTINA: Limpa os editais vencidos da base antes de fazer qualquer outra coisa ---
    processador.limpar_editais_expirados_no_banco(log_worker)
    
    config.PALAVRAS_CHAVE = [""] 
    config.PORTAIS_ATIVOS = {"cnpq": True, "finep": True, "fundep": True, "petrobras": True}
    
    DIRETORIO_PORTAIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portais")
    if not os.path.exists(DIRETORIO_PORTAIS):
        log_worker("[X] ERRO CRÍTICO: A pasta 'portais' não foi localizada no diretório atual.")
        return

    arquivos_portais = [
        f[:-3] for f in os.listdir(DIRETORIO_PORTAIS) 
        if f.endswith(".py") and f != "__init__.py"
    ]

    log_worker(f"[Sistema] Motores de busca localizados no pacote: {arquivos_portais}")

    for modulo_nome in arquivos_portais:
        log_worker(f"[Esteira] Acionando motor de busca: {modulo_nome.upper()}")
        try:
            portal_ativo = importlib.import_module(f"portais.{modulo_nome}")
            importlib.reload(portal_ativo) 
            if hasattr(portal_ativo, "varrer"):
                portal_ativo.varrer(log_worker, None)
            else:
                log_worker(f"    [X] Falha de Assinatura: '{modulo_nome}.py' não possui a função 'varrer'.")
        except Exception as err:
            log_worker(f"    [X] Erro crítico de execução no motor '{modulo_nome}': {err}")
            traceback.print_exc()

    log_worker("[Esteira] Raspagem ampla finalizada. Iniciando processamento da fila de IA...")
    status_ia = processador.consumir_fila_pendente_ia(log_worker, None)
    log_worker(f"[Esteira] Fila de IA processada com status de encerramento: {status_ia}")
    
    # GATILHO DO RETRABALHO AUTOMÁTICO COM REPORT
    processador.executar_retrabalho_editais_com_erro(log_worker)
    
    log_worker("=== CICLO DE TRABALHO ATUAL CONCLUÍDO COM SUCESSO ===")


if __name__ == "__main__":
    # Define o intervalo de espera em repouso entre cada varredura (2 horas = 7200 segundos)
    INTERVALO_SEGUNDOS = 7200 
    
    log_worker("=== SERVIÇO BACKGROUND DE BUSCA DE EDITAIS INICIALIZADO ===")
    
    while True:
        try:
            executar_ciclo_varredura()
        except KeyboardInterrupt:
            log_worker("Serviço de segundo plano interrompido manualmente pelo usuário (Ctrl+C).")
            break
        except Exception as e:
            log_worker(f"[CRÍTICO] Ocorreu uma exceção inesperada no loop principal: {e}")
            traceback.print_exc()
        
        log_worker(f"Entrando em repouso. Aguardando {INTERVALO_SEGUNDOS // 60} minutos para o próximo ciclo...")
        time.sleep(INTERVALO_SEGUNDOS)
