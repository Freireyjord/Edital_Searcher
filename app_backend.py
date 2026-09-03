import os, sys, traceback, importlib
import config, processador

def rodar_automacao_unificada(callback_fim, log, atualizar_tabela_func):
    try:
        log("[App Backend] Iniciando varredura automatizada e dinâmica de portais...")

        # --- MOTOR PLUGÁVEL COM FILTRO SELETIVO ---
        if getattr(sys, 'frozen', False):
            DIRETORIO_PORTAIS = os.path.join(sys._MEIPASS, "portais")
        else:
            DIRETORIO_PORTAIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portais")

        arquivos_portais = []
        if os.path.exists(DIRETORIO_PORTAIS):
            arquivos_portais = [
                f[:-3] for f in os.listdir(DIRETORIO_PORTAIS) 
                if f.endswith(".py") and f != "__init__.py"
            ]

        log(f"[Sistema] Módulos de portais identificados no pacote: {arquivos_portais}")

        for modulo_nome in arquivos_portais:
            # VERIFICAÇÃO DE GATILHO INTERNO ATIVO (Padrão True caso não esteja no JSON)
            esta_ativo = config.PORTAIS_ATIVOS.get(modulo_nome, True)
            
            if not esta_ativo:
                log(f"\n[Filtro] Ignorando portal '{modulo_nome.upper()}' (Desmarcado na Interface).")
                continue

            log(f"\n=======================================================")
            log(f"[Esteira] Acionando motor de busca ativo: {modulo_nome.upper()}")
            log(f"=======================================================")
            
            try:
                portal_ativo = importlib.import_module(f"portais.{modulo_nome}")
                if hasattr(portal_ativo, "varrer"):
                    portal_ativo.varrer(log, atualizar_tabela_func)
                else:
                    log(f"    [X] Erro Assinatura: '{modulo_nome}.py' sem função 'varrer'.")
            except Exception as err_modulo:
                log(f"    [X] Falha no motor '{modulo_nome}': {err_modulo}")
                traceback.print_exc()

        log("\n[Esteira] Todos os portais selecionados foram varridos. Processando IA...")
        processador.consumir_fila_pendente_ia(log, atualizar_tabela_func)

    except Exception as e: 
        log(f"[X] Erro interno crítico no orquestrador: {e}")
        traceback.print_exc()
    
    log("\n[App Backend] Sincronização e triagem de portais concluídas!")
    callback_fim()
