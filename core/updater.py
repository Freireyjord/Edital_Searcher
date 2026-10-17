import hashlib
import os
import re
import subprocess
import sys
import threading

import requests
from tkinter import messagebox

# --- GERENCIADOR DE VERSÃO E IDENTIFICAÇÃO DO GITHUB ---
VERSAO_ATUAL = "1.1.0"
GITHUB_USER = "Freireyjord"
GITHUB_REPO = "Edital_Searcher"

# CORREÇÃO: a API fica em api.github.com (github.com/repos/... devolve 404 e o
# atualizador ignorava a falha silenciosamente, então nunca atualizava).
URL_API_RELEASE = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
PREFIXO_DOWNLOAD_VALIDO = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/"
HEADERS = {"User-Agent": "PCE-App-Updater-FIEB", "Accept": "application/vnd.github+json"}


def _versao_tupla(texto):
    """'v1.0.10' -> (1, 0, 10). Comparar como string diria que '1.0.9' > '1.0.10'."""
    return tuple(int(n) for n in re.findall(r"\d+", texto or ""))


def _diretorio_app():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def verificar_e_aplicar_atualizacao(lbl_status_widget, window_instancia):
    """Checa o GitHub em segundo plano (a janela não congela se a rede estiver lenta)."""
    def tarefa():
        try:
            resposta = requests.get(URL_API_RELEASE, headers=HEADERS, timeout=10)
            if resposta.status_code != 200:
                # 403 costuma ser limite de requisições anônimas (60/h por IP; rede corporativa compartilha IP)
                print(f"[Updater] GitHub respondeu {resposta.status_code}. Ignorando atualização.")
                return
            dados = resposta.json()
            nuvem = _versao_tupla(dados.get("tag_name", ""))
            local = _versao_tupla(VERSAO_ATUAL)
            print(f"[Updater] Local: {local} | Nuvem: {nuvem}")
            if nuvem and nuvem > local:
                window_instancia.after(0, lambda: _perguntar_e_atualizar(dados, nuvem, lbl_status_widget, window_instancia))
        except Exception as e:
            print(f"Falha ao checar atualizações no GitHub: {e}")

    threading.Thread(target=tarefa, daemon=True).start()


def _perguntar_e_atualizar(dados_release, versao_nuvem, lbl_status_widget, window_instancia):
    versao_txt = ".".join(map(str, versao_nuvem))
    if messagebox.askyesno(
        "Atualização Disponível",
        f"Existe uma nova versão estável (v{versao_txt}) disponível no GitHub.\n"
        "Deseja atualizar o sistema automaticamente agora?",
    ):
        _processar_download_e_patch(dados_release, lbl_status_widget, window_instancia)


def _sha256_esperado(dados_release, asset_zip):
    """
    Hash do PCE.zip publicado. Fontes, em ordem:
    1) campo 'digest' do asset (GitHub calcula automaticamente: 'sha256:<hex>');
    2) asset 'PCE.zip.sha256' anexado à release.
    """
    digest = (asset_zip.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        return digest.split(":", 1)[1].strip().lower()

    for asset in dados_release.get("assets", []):
        if asset.get("name", "").lower() == "pce.zip.sha256":
            r = requests.get(asset["browser_download_url"], headers=HEADERS, timeout=15)
            if r.status_code == 200 and r.text.strip():
                return r.text.strip().split()[0].lower()
    return None


def _ps_literal(caminho):
    """Escapa aspas simples para uso dentro de '...' no PowerShell."""
    return caminho.replace("'", "''")


def _processar_download_e_patch(dados_release, lbl_status_widget, window_instancia):
    """Baixa PCE.zip, valida o SHA-256 e injeta o patcher .bat de auto-substituição."""
    asset_zip = next((a for a in dados_release.get("assets", []) if a.get("name", "").lower() == "pce.zip"), None)
    if not asset_zip:
        messagebox.showerror("Erro", "Arquivo empacotado 'PCE.zip' não foi localizado nesta release.")
        return

    url_zip = asset_zip.get("browser_download_url", "")
    if not url_zip.startswith(PREFIXO_DOWNLOAD_VALIDO):
        messagebox.showerror("Atualização bloqueada", "O link de download não pertence ao repositório oficial do PCE.")
        return

    try:
        hash_esperado = _sha256_esperado(dados_release, asset_zip)
    except Exception:
        hash_esperado = None
    if not hash_esperado:
        messagebox.showerror(
            "Atualização bloqueada",
            "A release não traz o hash SHA-256 do PCE.zip, então a integridade não pode ser verificada.\n\n"
            "Anexe um arquivo 'PCE.zip.sha256' à release (Windows: certutil -hashfile PCE.zip SHA256).",
        )
        return

    if lbl_status_widget:
        lbl_status_widget.configure(text="Status: Baixando nova versão do painel corporativo...")
    window_instancia.update()

    diretorio = _diretorio_app()
    caminho_zip = os.path.join(diretorio, "pce_update_temp.zip")

    try:
        sha = hashlib.sha256()
        with requests.get(url_zip, headers=HEADERS, timeout=(10, 120), stream=True) as r:
            r.raise_for_status()
            with open(caminho_zip, "wb") as f:
                for pedaco in r.iter_content(chunk_size=262144):
                    f.write(pedaco)
                    sha.update(pedaco)

        if sha.hexdigest().lower() != hash_esperado:
            os.remove(caminho_zip)
            messagebox.showerror("Atualização bloqueada", "O arquivo baixado não confere com o hash SHA-256 publicado. A atualização foi cancelada.")
            return

        nome_exe = os.path.basename(sys.executable) if getattr(sys, "frozen", False) else "PCE.exe"
        caminho_bat = os.path.join(diretorio, "script_patcher.bat")

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
powershell -Command "Expand-Archive -LiteralPath '{_ps_literal(caminho_zip)}' -DestinationPath '{_ps_literal(diretorio)}' -Force"
echo  [v] Arquivos substituidos com sucesso!
echo  [*] Limpando arquivos temporarios...
del "{caminho_zip}"
echo  [v] Tudo pronto! Inicializando o novo PCE...
start "" "{os.path.join(diretorio, nome_exe)}"
del "%~f0"
"""
        with open(caminho_bat, "w", encoding="utf-8") as f_bat:
            f_bat.write(conteudo_bat)

        messagebox.showinfo("Pronto", "O download foi concluído e verificado! O sistema será reiniciado para aplicar a atualização.")
        subprocess.Popen(caminho_bat, shell=True)
        window_instancia.destroy()
        sys.exit(0)

    except Exception as err:
        try:
            if os.path.exists(caminho_zip):
                os.remove(caminho_zip)
        except OSError:
            pass
        messagebox.showerror("Erro Crítico", f"Falha ao baixar/aplicar a atualização: {err}")