import os, sys, subprocess, requests

from tkinter import messagebox

# --- GERENCIADOR DE VERSÃO E IDENTIFICAÇÃO DO GITHUB ---
VERSAO_ATUAL = "1.0.2"
GITHUB_USER = "Freireyjord"
GITHUB_REPO = "Edital_Searcher"

def verificar_e_aplicar_atualizacao(lbl_status_widget, window_instancia):
    """Consulta o servidor de APIs do GitHub de forma segura para validar novas versões."""
    # 🔥 CORREÇÃO: Apontando para o endpoint correto de dados (://github.com)
    url_api = f"https://github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
    
    try:
        # Enviando um User-Agent padrão (Obrigatório para o firewall do GitHub não rejeitar a requisição)
        headers = {"User-Agent": "PCE-App-Updater-FIEB"}
        resposta = requests.get(url_api, headers=headers, timeout=10)
        
        # 🔥 VALIDAÇÃO: Se o servidor rejeitar a chamada, exibe o aviso limpo em vez de quebrar no .json()
        if resposta.status_code != 200:
            print(f"[Updater] O GitHub retornou status de recusa {resposta.status_code}. Requisição ignorada.")
            return False
            
        dados_release = resposta.json()
        versao_nuvem = dados_release.get("tag_name", "").lower().replace("pce", "").replace("v", "").strip()
        versao_local_limpa = VERSAO_ATUAL.lower().replace("pce", "").replace("v", "").strip()

        print(f"[Updater] Local: {versao_local_limpa} | Nuvem: {versao_nuvem}")

        if versao_nuvem > versao_local_limpa:
            pergunta = messagebox.askyesno(
                "Atualização Disponível", 
                f"Existe uma nova versão estável (v{versao_nuvem}) disponível no GitHub.\nDeseja atualizar o sistema automaticamente agora?"
            )
            if pergunta:
                _processar_download_e_patch(dados_release, lbl_status_widget, window_instancia)
                return True
                
    except Exception as e:
        print(f"Falha ao checar atualizações no GitHub: {e}")
    return False



def _processar_download_e_patch(dados_release, lbl_status_widget, window_instancia):
    """Baixa o pacote zip da release e injeta o script patcher .bat de auto-substituição."""
    url_download_zip = None
    for asset in dados_release.get("assets", []):
        if "pce.zip" in asset.get("name", "").lower():
            url_download_zip = asset.get("browser_download_url")
            break

    if not url_download_zip:
        messagebox.showerror("Erro", "Arquivo empacotado 'PCE.zip' não foi localizado nesta release.")
        return

    if lbl_status_widget:
        lbl_status_widget.configure(text="Status: Baixando nova versão do painel corporativo...")
    window_instancia.update()

    try:
        # Resolve caminhos relativos ao executável compilado ou script ativo
        caminho_atual = os.path.abspath(sys.argv[0])
        diretorio_execucao = os.path.dirname(caminho_atual)
        
        caminho_zip = os.path.join(diretorio_execucao, "pce_update_temp.zip")

        # Baixa os binários comprimidos da internet
        conteudo_zip = requests.get(url_download_zip, timeout=60).content
        with open(caminho_zip, "wb") as f: 
            f.write(conteudo_zip)

        caminho_bat = os.path.join(diretorio_execucao, "script_patcher.bat")
        
        # Cria o script de substituição atômica que fecha o app, descompacta e reabre o PCE.exe
        conteudo_bat = f"""@echo off
title ATUALIZADOR AUTOMATICO - PCE
mode con: cols=65 lines=10
color 0B
echo =============================================================
echo               PCE - ATUALIZACAO DO SISTEMA
echo =============================================================
echo  [!] Aguardando o encerramento do painel principal...
timeout /t 3 /nobreak > nul
cls
echo =============================================================
echo               PCE - ATUALIZACAO DO SISTEMA
echo =============================================================
echo  [*] Aplicando novos arquivos do sistema, aguarde...
powershell -Command "Expand-Archive -Path '{caminho_zip}' -DestinationPath '{diretorio_execucao}' -Force"
echo  [v] Arquivos substituidos com sucesso!
echo  [*] Limpando arquivos temporarios...
del "{caminho_zip}"
echo  [v] Tudo pronto! Inicializando o novo PCE...
start "" "{os.path.join(diretorio_execucao, 'PCE.exe')}"
del "%~f0"
"""
        with open(caminho_bat, "w", encoding="utf-8") as f_bat: 
            f_bat.write(conteudo_bat)

        messagebox.showinfo("Pronto", "O download foi concluído! O sistema será reiniciado em instantes para aplicar o patch.")
        
        # Executa em subprocesso desvinculado e mata a instância atual do Python
        subprocess.Popen(caminho_bat, shell=True)
        window_instancia.destroy()
        sys.exit(0)
        
    except Exception as err:
        messagebox.showerror("Erro Crítico", f"Falha na extração de arquivos do patch: {err}")
