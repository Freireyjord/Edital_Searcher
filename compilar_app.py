import os
import shutil
import subprocess
import sys

def compilar():
    print("=== INICIANDO PROCESSO DE COMPILAÇÃO CORPORATIVA ===")
    
    script_principal = "app_main.py"
    nome_executavel = "PCE"
    arquivo_icone = "app_icone.ico"
    
    if not os.path.exists(script_principal):
        print(f"[X] ERRO: O arquivo central {script_principal} não foi encontrado na raiz.")
        sys.exit(1)

    # 💡 ALTERADO: Chamamos o PyInstaller como um módulo do Python atual (sys.executable)
    # Isso evita problemas com caminhos de PATH e mapeamentos do Windows Apps
    comando = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        f"--name={nome_executavel}",
        "--windowed",
        "--add-data=core;core",
        "--add-data=views;views",
        script_principal
    ]

    if os.path.exists(arquivo_icone):
        print(f"[✓] Ícone '{arquivo_icone}' localizado. Aplicando ao design do app...")
        # Índices alterados para acomodar o 'sys.executable -m PyInstaller' no começo do vetor
        comando.insert(3, f"--icon={arquivo_icone}")
        comando.insert(4, f"--add-data={arquivo_icone};.")
    else:
        print(f"[⚠️ AVISO] Arquivo '{arquivo_icone}' não foi encontrado. O app usará o ícone padrão.")

    print(f"[*] Executando o build do PyInstaller para o '{nome_executavel}'...")
    try:
        # Adicionado shell=True para garantir compatibilidade máxima com o PowerShell/CMD corporativo
        subprocess.run(comando, check=True, shell=True)
        print("\n[v] Executável gerado com sucesso na pasta 'dist/PCE/'!")
    except subprocess.CalledProcessError as e:
        print(f"\n[X] Falha crítica durante a execução do PyInstaller: {e}")
        print("[i] Dica: Certifique-se de que o PyInstaller está instalado executando: pip install pyinstaller")
        sys.exit(1)

    print("\n=== PRÓXIMOS PASSOS ===")
    print("1. Certifique-se de incluir o 'smtp_config.json' do relay dentro da pasta 'dist/PCE/'.")
    print("2. Compacte o conteúdo da pasta 'PCE' em um arquivo chamado 'PCE.zip' para disponibilizar no GitHub Releases.")

if __name__ == "__main__":
    compilar()
