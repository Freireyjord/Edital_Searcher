import json, os, sys, zipfile, shutil, subprocess, requests
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime


# Importações externas existentes
from filtros_sidebar import SidebarFiltros, normalizar_texto
from colunas_sidebar import SidebarColunas  
import config

# --- GERENCIADOR DE VERSÃO E IDENTIFICAÇÃO DO GITHUB ---
VERSAO_ATUAL = "1.0.0"
GITHUB_USER = "Freireyjord"
GITHUB_REPO = "Edital_Searcher"

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

class AppSincronizador(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Painel de Consulta de Editais")
        self.geometry("1150x760") 
        self.minsize(1000, 700)

        # Variáveis globais de controle do funil de filtros
        self.filtro_portais = {}      
        self.filtro_data_min = ""     
        self.filtro_data_max = ""     

        self.grid_rowconfigure(1, weight=1) 
        self.grid_columnconfigure(0, weight=1)

        # ------------------ PAINEL SUPERIOR ------------------
        self.frame_topo = ctk.CTkFrame(self, corner_radius=0, border_width=1, border_color="#3a3d42")
        self.frame_topo.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        
        self.lbl_titulo = ctk.CTkLabel(
            self.frame_topo, text=f"PESQUISA INTELIGENTE DE EDITAIS (v{VERSAO_ATUAL})", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold")
        )
        self.lbl_titulo.pack(side="left", padx=15, pady=15)

        self.btn_sincronizar = ctk.CTkButton(
            self.frame_topo, text="ATUALIZAR TABELA", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"), command=self.acao_sincronizar
        )
        self.btn_sincronizar.pack(side="right", padx=15, pady=15)

        self.btn_abrir_link = ctk.CTkButton(
            self.frame_topo, text="ABRIR EDITAL", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            fg_color="#2b719e", hover_color="#1f5373", command=self.abrir_link_botao
        )
        self.btn_abrir_link.pack(side="right", padx=10, pady=15)

        # ------------------ PAINEL CENTRAL MULTI-COLUNAS ------------------
        self.abas = ctk.CTkTabview(self, corner_radius=0)
        self.abas.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        
        self.tab_resultados = self.abas.add("EDITAIS ENCONTRADOS")

        self.tab_resultados.grid_rowconfigure(0, weight=0) 
        self.tab_resultados.grid_rowconfigure(1, weight=4) 
        self.tab_resultados.grid_rowconfigure(2, weight=3) 
        
        self.tab_resultados.grid_columnconfigure(0, weight=0) 
        self.tab_resultados.grid_columnconfigure(1, weight=1) 

        self.sidebar_filtros = None
        self.sidebar_visivel = False
        self.btn_aplicar_topo = None
        self.btn_limpar_topo = None

        self.configurar_barra_ferramentas_resultados()
        self.configurar_tabela_resultados()
        self.configurar_painel_leitura_embutido()

        # ------------------ PAINEL INFERIOR ------------------
        self.frame_base = ctk.CTkFrame(self, height=35, corner_radius=0)
        self.frame_base.grid(row=2, column=0, sticky="ew") 
        
        self.lbl_status = ctk.CTkLabel(
            self.frame_base, text="Status: Sistema conectado ao Supabase. Filtros locais ativos.", 
            font=ctk.CTkFont(family="Arial", size=11)
        )
        self.lbl_status.pack(side="left", padx=15, pady=5)

        self.atualizar_tabela_local()

        # DISPARADOR DO MOTOR DE ATUALIZAÇÃO AUTOMÁTICA (2 segundos após abrir a tela)
        self.after(2000, self.verificar_atualizacoes_projeto)

    def configurar_barra_ferramentas_resultados(self):
        self.frame_ferramentas = ctk.CTkFrame(self.tab_resultados, height=45, corner_radius=0, fg_color="transparent")
        self.frame_ferramentas.grid(row=0, column=1, padx=5, pady=(5, 5), sticky="ew")
        
        self.btn_filtro_funil = ctk.CTkButton(
            self.frame_ferramentas, text="CONFIGURAR PARAMETROS E FILTROS", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            fg_color="#34495e", hover_color="#2c3e50", width=250, command=self.alternar_sidebar_filtros
        )
        self.btn_filtro_funil.pack(side="left", padx=5, pady=5)

        self.btn_colunas_toggle = ctk.CTkButton(
            self.frame_ferramentas, text="CONFIGURAR COLUNAS", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            fg_color="#34495e", hover_color="#2c3e50", width=180, command=self.alternar_sidebar_colunas
        )
        self.btn_colunas_toggle.pack(side="right", padx=5, pady=5)

        self.lbl_filtros_ativos = ctk.CTkLabel(
            self.frame_ferramentas, text="Filtros: Operando com base nas suas tags locais.", 
            font=ctk.CTkFont(family="Arial", size=11, slant="italic"), text_color="#95a5a6"
        )
        self.lbl_filtros_ativos.pack(side="left", padx=15, pady=5)

    def configurar_tabela_resultados(self):
        self.colunas_visiveis = ["titulo", "portal", "datas", "vigencia_projeto", "palavra_chave"]
        self.ultima_ordenacao = {"coluna": None, "reverse": False}
        
        self.tabela = ttk.Treeview(self.tab_resultados, show="headings", style="Treeview")
        self.scroll_y_tabela = ttk.Scrollbar(self.tab_resultados, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=self.scroll_y_tabela.set)
        
        self.reconfigurar_colunas_tabela()
        self.tabela.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        self.scroll_y_tabela.grid(row=1, column=3, sticky="ns")
        
        self.tabela.bind("<<TreeviewSelect>>", self.evento_linha_selecionada)
        self.tabela.bind("<Double-1>", self.abrir_link_edital)

    def reconfigurar_colunas_tabela(self):
        "Redesenha estruturalmente as colunas na Treeview incluindo a coluna Título."
        linhas_antigas = []
        for item in self.tabela.get_children():
            linhas_antigas.append((self.tabela.item(item, "values"), self.tabela.item(item, "tags")))

        self.tabela.configure(columns=tuple(self.colunas_visiveis))
        titulos = {"titulo": "Título do Edital", "portal": "Portal de Origem", "datas": "Prazo / Submissao", "vigencia_projeto": "Vigência", "palavra_chave": "Termos Correspondentes"}
        larguras = {"titulo": 220, "portal": 120, "datas": 120, "vigencia_projeto": 120, "palavra_chave": 350}
        alinhamentos = {"titulo": "w", "portal": "w", "datas": "center", "vigencia_projeto": "center", "palavra_chave": "w"}

        for col in self.colunas_visiveis:
            self.tabela.heading(col, text=titulos[col], command=lambda c=col: self.ordenar_por_coluna(c))
            self.tabela.column(col, width=larguras[col], anchor=alinhamentos[col])

        if linhas_antigas:
            self.atualizar_tabela_local()

    def ordenar_por_coluna(self, id_coluna):
        itens = [(self.tabela.set(item, id_coluna), item) for item in self.tabela.get_children("")]
        reverse = not self.ultima_ordenacao["reverse"] if self.ultima_ordenacao["coluna"] == id_coluna else False
        self.ultima_ordenacao = {"coluna": id_coluna, "reverse": reverse}

        def extrair_chave_ordenacao(par_item):
            valor_texto, id_item = par_item
            tags = self.tabela.item(id_item, "tags")
            if len(tags) >= 2:
                try:
                    edital_data = json.loads(tags[1])
                    if id_coluna == "datas":
                        iso_data = edital_data.get("prazo_iso")
                        if not iso_data or "9999" in str(iso_data):
                            return "9999-12-31" if not reverse else "0000-00-00"
                        return str(iso_data).split(" ")[0]
                    return str(edital_data.get(id_coluna, valor_texto)).strip().lower()
                except Exception:
                    pass
            return valor_texto.strip().lower()

        itens.sort(key=extrair_chave_ordenacao, reverse=reverse)
        for index, (_, item) in enumerate(itens):
            self.tabela.move(item, "", index)

    def configurar_painel_leitura_embutido(self):
        self.frame_detalhes = ctk.CTkFrame(self.tab_resultados, corner_radius=0, border_width=1, border_color="#3a3d42")
        self.frame_detalhes.grid(row=2, column=1, padx=(5, 0), pady=(10, 5), sticky="nsew")
        
        lbl_titulo = ctk.CTkLabel(
            self.frame_detalhes, text="RESUMO EXPANDIDO DO EDITAL SELECIONADO (GERADO POR IA)", 
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"), text_color="#1f6aa5"
        )
        lbl_titulo.pack(anchor="w", padx=15, pady=8)
        
        self.txt_detalhes_escopo = ctk.CTkTextbox(
            self.frame_detalhes, font=("Arial", 12), wrap="word", corner_radius=0, border_width=1, border_color="#2a2d32"
        )
        self.txt_detalhes_escopo.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.txt_detalhes_escopo.insert("1.0", "Nenhum edital selecionado na tabela superior.")
        self.txt_detalhes_escopo.configure(state="disabled")

    def alternar_sidebar_filtros(self):
        if self.sidebar_visivel:
            if self.sidebar_filtros:
                self.sidebar_filtros.grid_forget()
                self.sidebar_filtros.destroy()
                self.sidebar_filtros = None
            if self.btn_aplicar_topo: self.btn_aplicar_topo.pack_forget(); self.btn_aplicar_topo.destroy(); self.btn_aplicar_topo = None
            if self.btn_limpar_topo: self.btn_limpar_topo.pack_forget(); self.btn_limpar_topo.destroy(); self.btn_limpar_topo = None
            self.sidebar_visivel = False
            self.btn_filtro_funil.configure(fg_color="#34495e", text="CONFIGURAR PARAMETROS E FILTROS")
            self.lbl_filtros_ativos.pack(side="left", padx=15, pady=5)
        else:
            self.sidebar_visivel = True
            self.btn_filtro_funil.configure(fg_color="#1f6aa5", text="FECHAR CONFIGURAÇÕES")
            self.lbl_filtros_ativos.pack_forget()
            
            self.sidebar_filtros = SidebarFiltros(self.tab_resultados, app_callback=self)
            self.sidebar_filtros.grid(row=0, column=0, rowspan=3, padx=(5, 10), pady=5, sticky="nsew")
            
            self.btn_aplicar_topo = ctk.CTkButton(self.frame_ferramentas, text="APLICAR FILTROS", corner_radius=0, width=130, font=ctk.CTkFont(family="Arial", size=11, weight="bold"), fg_color="#27ae60", hover_color="#219653", command=self.executar_acao_filtrar)
            self.btn_aplicar_topo.pack(side="left", padx=5, pady=5)
            self.btn_limpar_topo = ctk.CTkButton(self.frame_ferramentas, text="LIMPAR", corner_radius=0, width=80, font=ctk.CTkFont(family="Arial", size=11, weight="bold"), fg_color="#c0392b", hover_color="#962d22", command=self.executar_acao_limpar)
            self.btn_limpar_topo.pack(side="left", padx=5, pady=5)

    def alternar_sidebar_colunas(self):
        if hasattr(self, 'sidebar_colunas_visivel') and self.sidebar_colunas_visivel:
            if hasattr(self, 'sidebar_colunas') and self.sidebar_colunas:
                self.sidebar_colunas.grid_forget()
                self.sidebar_colunas.destroy()
                self.sidebar_colunas = None
            self.sidebar_colunas_visivel = False
            self.btn_colunas_toggle.configure(fg_color="#34495e", text="CONFIGURAR COLUNAS")
        else:
            self.sidebar_colunas_visivel = True
            self.btn_colunas_toggle.configure(fg_color="#1f6aa5", text="FECHAR COLUNAS")
            self.sidebar_colunas = SidebarColunas(self.tab_resultados, app_callback=self)
            self.sidebar_colunas.grid(row=0, column=2, rowspan=3, padx=(10, 5), pady=5, sticky="nsew")

    def executar_acao_filtrar(self):
        if self.sidebar_filtros:
            self.sidebar_filtros.adicionar_tag_evt()
            config.PORTAIS_ATIVOS = {k: v.get() for k, v in self.sidebar_filtros.dic_vars_locais.items()}
            config.salvar_configuracoes_usuario(self.sidebar_filtros.lista_tags, config.PORTAIS_ATIVOS)
            self.filtro_portais = config.PORTAIS_ATIVOS
            self.atualizar_tabela_local()

    def executar_acao_limpar(self):
        self.filtro_data_min, self.filtro_data_max, self.filtro_portais = "", "", {}
        config.PALAVRAS_CHAVE = []
        config.salvar_configuracoes_usuario([], config.PORTAIS_ATIVOS)
        if self.sidebar_filtros:
            self.sidebar_filtros.btn_min.configure(text="DATA INICIAL")
            self.sidebar_filtros.btn_max.configure(text="DATA FINAL")
            self.sidebar_filtros.resetar_tags_visuais()
        self.atualizar_tabela_local()

    def atualizar_tabela_local(self):
        for item in self.tabela.get_children(): self.tabela.delete(item)
        try:
            resposta = config.supabase.table("editais").select("*").execute()
            editais = resposta.data if hasattr(resposta, 'data') else resposta
            editais_ordenados = sorted(editais, key=lambda x: x.get("prazo_iso") if x.get("prazo_iso") is not None else "9999-12-31 23:59")
            hoje = datetime.now().date()
            dt_corte_min = datetime.strptime(self.filtro_data_min, "%d/%m/%Y").date() if self.filtro_data_min else None
            dt_corte_max = datetime.strptime(self.filtro_data_max, "%d/%m/%Y").date() if self.filtro_data_max else None
            termos_filtro_usuario = [normalizar_texto(t) for t in config.PALAVRAS_CHAVE if t.strip()]
            editais_para_inserir = []

            for edital in editais_ordenados:
                status_limpo = str(edital.get("status_ia") or "").strip().lower()
                if status_limpo in ["descartado_vencido", "pendente", ""]: continue
                portal_bruto = edital.get("portal", "N/A")
                portal_limpo = str(portal_bruto).strip().lower()
                modulo_chave = portal_limpo.split(" ")[0] if " " in portal_limpo else portal_limpo
                if self.filtro_portais and not self.filtro_portais.get(modulo_chave, True): continue
                
                prazo_texto_bruto, prazo_iso_bruto = edital.get("datas", "") or "", edital.get("prazo_iso", "") or ""
                texto_prazo_formatado, dt_item = "A consultar", None

                if prazo_iso_bruto and "9999" not in str(prazo_iso_bruto):
                    try:
                        data_iso_limpa = str(prazo_iso_bruto).strip().split(" ")[0]
                        dt_item = datetime.strptime(data_iso_limpa, "%Y-%m-%d").date()
                        texto_prazo_formatado = f"Até {dt_item.strftime('%d/%m/%Y')}"
                    except: dt_item = None

                if not dt_item:
                    if "contínuo" in prazo_texto_bruto.lower() or "fluxo" in prazo_texto_bruto.lower(): texto_prazo_formatado = "Fluxo Contínuo"
                    else:
                        texto_limpo = prazo_texto_bruto.replace("Envio de propostas ", "").strip()
                        texto_limpo = texto_limpo.split(", às")[0] if ", às" in texto_limpo else (texto_limpo.split(", as")[0] if ", as" in texto_limpo else texto_limpo)
                        texto_prazo_formatado = texto_limpo.strip() if texto_limpo else "A consultar"

                if dt_item:
                    if dt_item < hoje or (dt_corte_min and dt_item < dt_corte_min) or (dt_corte_max and dt_item > dt_corte_max): continue
                if len(texto_prazo_formatado) > 40 and "até" in texto_prazo_formatado.lower(): texto_prazo_formatado = texto_prazo_formatado.split(",")[0]

                tags_brutas_ia = edital.get("tags_ia", "") or ""
                lista_tags_edital = [tag.strip() for tag in tags_brutas_ia.split(",") if tag.strip()]
                titulo_edital_limpo = normalizar_texto(edital.get("titulo", ""))
                tags_encontradas_no_filtro = []

                for palavra_usuario in config.PALAVRAS_CHAVE:
                    palavra_usuario_limpa = normalizar_texto(palavra_usuario)
                    if not palavra_usuario_limpa: continue
                    if palavra_usuario_limpa in titulo_edital_limpo:
                        if palavra_usuario not in tags_encontradas_no_filtro: tags_encontradas_no_filtro.append(palavra_usuario)
                        continue
                    for tag_edital in lista_tags_edital:
                        if palavra_usuario_limpa in normalizar_texto(tag_edital) or normalizar_texto(tag_edital) in palavra_usuario_limpa:
                            if palavra_usuario not in tags_encontradas_no_filtro: tags_encontradas_no_filtro.append(palavra_usuario)

                if len(termos_filtro_usuario) > 0 and not tags_encontradas_no_filtro: continue
                texto_coluna_termos = ", ".join(tags_encontradas_no_filtro) if tags_encontradas_no_filtro else "Geral / Amplo"
                
                mapa_valores_completos = {"titulo": edital.get("titulo") or "Edital sem título", "portal": portal_bruto, "datas": texto_prazo_formatado, "vigencia_projeto": edital.get("vigencia_projeto", "N/A") or "N/A", "palavra_chave": texto_coluna_termos}
                editais_para_inserir.append((len(tags_encontradas_no_filtro), mapa_valores_completos, edital))

            editais_para_inserir.sort(key=lambda x: x[0], reverse=True)
            for qtd, valores_completos, edital_obj in editais_para_inserir:
                self.tabela.insert("", "end", values=tuple(valores_completos[col] for col in self.colunas_visiveis), tags=(edital_obj.get("url", ""), json.dumps(edital_obj)))
        except Exception as e: print(f"Erro tabela nuvem: {e}")

    def acao_sincronizar(self):
        self.btn_sincronizar.configure(state="disabled", text="ATUALIZANDO...")
        self.lbl_status.configure(text="Status: Consultando base de editais no Supabase...")
        self.atualizar_tabela_local()
        self.btn_sincronizar.configure(state="normal", text="ATUALIZAR TABELA")
        self.lbl_status.configure(text="Status: Tabela sincronizada.")
        messagebox.showinfo("Concluido", "Tabela updated com sucesso.")

    def evento_linha_selecionada(self, event):
        item_selecionado = self.tabela.selection()
        if not item_selecionado: return
        tags = self.tabela.item(item_selecionado, "tags")
        if len(tags) >= 2:
            edital = json.loads(tags[1])
            texto_formatado = f"PORTAL DE ORIGEM: {edital.get('portal','N/A')}\nPRAZO DE SUBMISSAO: {edital.get('datas','N/A')}\nPRAZO DE EXECUÇÃO: {edital.get('vigencia_projeto','N/A')}\nTAGS DO EDITAL (IA): {edital.get('tags_ia','Nenhuma')}\nLINHA DE PESQUISA: {edital.get('pesquisa','N/A')}\nORCAMENTO / VERBA: {edital.get('subvencao','N/A')}\n\nRESUMO DO ESCOPO:\n{edital.get('escopo','N/A')}"
            self.txt_detalhes_escopo.configure(state="normal"); self.txt_detalhes_escopo.delete("1.0", "end"); self.txt_detalhes_escopo.insert("1.0", texto_formatado); self.txt_detalhes_escopo.configure(state="disabled")

    def abrir_link_edital(self, event):
        item_selecionado = self.tabela.selection()
        if item_selecionado:
            tags = self.tabela.item(item_selecionado, "tags")
            if tags: import webbrowser; webbrowser.open(tags[0])

    def abrir_link_botao(self):
        item = self.tabela.selection()
        if not item: messagebox.showwarning("Aviso", "Selecione um edital."); return
        tags = self.tabela.item(item, "tags")
        if len(tags) > 0: import webbrowser; webbrowser.open(tags[0])

    # --- NOVO MECANISMO DE ATUALIZAÇÃO BASEADO NO GITHUB RELEASES ---
    def verificar_atualizacoes_projeto(self):
        url_api = f"https://github.com{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
        try:
            resposta = requests.get(url_api, timeout=10)
            if resposta.status_code != 200: return
            
            dados_release = resposta.json()
            versao_nuvem = dados_release.get("tag_name", "").lower().replace("pce", "").replace("v", "").strip()
            versao_local_limpa = VERSAO_ATUAL.lower().replace("pce", "").replace("v", "").strip()

            if versao_nuvem and versao_nuvem > versao_local_limpa:
                pergunta = messagebox.askyesno(
                    "Atualização Disponível", 
                    f"Existe uma nova versão estável (v{versao_nuvem}) disponível no GitHub.\nDeseja atualizar o sistema automaticamente agora?"
                )
                if pergunta:
                    self.processar_download_update(dados_release)
        except Exception as e:
            print(f"Falha ao checar atualizações: {e}")

    def processar_download_update(self, dados_release):
        url_download_zip = None
        for asset in dados_release.get("assets", []):
            if "pce.zip" in asset.get("name", "").lower():
                url_download_zip = asset.get("browser_download_url")
                break

        if not url_download_zip:
            messagebox.showerror("Erro", "Arquivo empacotado 'PCE.zip' não foi encontrado nesta release.")
            return

        self.lbl_status.configure(text="Status: Baixando nova versão do painel...")
        self.update()

        try:
            diretorio_execucao = os.path.dirname(os.path.abspath(sys.argv))
            caminho_zip = os.path.join(diretorio_execucao, "pce_update_temp.zip")

            conteudo_zip = requests.get(url_download_zip, timeout=60).content
            with open(caminho_zip, "wb") as f: f.write(conteudo_zip)

            caminho_bat = os.path.join(diretorio_execucao, "script_patcher.bat")
            
            # --- CONTEÚDO DO .BAT COM MENSAGEM DE AVISO PERSONALIZADA ---
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
            with open(caminho_bat, "w", encoding="utf-8") as f_bat: f_bat.write(conteudo_bat)

            messagebox.showinfo("Pronto", "O download foi concluído! O sistema será reiniciado em instantes para concluir o patch.")
            
            # Dispara o arquivo em segundo plano e mata o processo Python principal
            subprocess.Popen(caminho_bat, shell=True)
            self.destroy()
            sys.exit(0)
            
        except Exception as err:
            messagebox.showerror("Erro Crítico", f"Falha na extração de arquivos: {err}")

if __name__ == "__main__":
    app = AppSincronizador()
    app.mainloop()
