import json
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
import re

# Importações externas existentes
from filtros_sidebar import SidebarFiltros, normalizar_texto
from colunas_sidebar import SidebarColunas  
import config

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

class AppSincronizador(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Painel de Consulta de Editais")
        self.geometry("1150x760") 
        self.minsize(1000, 620)

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
            self.frame_topo, text="PESQUISA INTELIGENTE DE EDITAIS", 
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
        
        # Grid Inteligente: Coluna 0 é dinâmica (sidebar), Coluna 1 expande e ocupa tudo
        self.tab_resultados.grid_columnconfigure(0, weight=0) 
        self.tab_resultados.grid_columnconfigure(1, weight=1) 

        self.sidebar_filtros = None
        self.sidebar_visivel = False
        
        # Variáveis para guardar a referência dos botões dinâmicos do topo
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
    def configurar_barra_ferramentas_resultados(self):
        # Guardamos a referência do frame para poder anexar os botões dinâmicos nele
        self.frame_ferramentas = ctk.CTkFrame(self.tab_resultados, height=45, corner_radius=0, fg_color="transparent")
        self.frame_ferramentas.grid(row=0, column=1, padx=5, pady=(5, 5), sticky="ew")
        
        # Botão de Filtros (Fica no lado esquerdo da barra)
        self.btn_filtro_funil = ctk.CTkButton(
            self.frame_ferramentas, text="CONFIGURAR PARAMETROS E FILTROS", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            fg_color="#34495e", hover_color="#2c3e50", width=250, command=self.alternar_sidebar_filtros
        )
        self.btn_filtro_funil.pack(side="left", padx=5, pady=5)

        # Botão de Colunas (Fica no lado direito da barra)
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
        # Define o estado inicial contendo a coluna titulo em primeiro lugar
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
        """Redesenha estruturalmente as colunas na Treeview incluindo a coluna Título."""
        linhas_antigas = []
        for item in self.tabela.get_children():
            linhas_antigas.append((self.tabela.item(item, "values"), self.tabela.item(item, "tags")))

        self.tabela.configure(columns=tuple(self.colunas_visiveis))
        
        # Mapeamento estendido contendo as dimensões industriais do Título
        titulos = {"titulo": "Título do Edital", "portal": "Portal de Origem", "datas": "Prazo / Submissao", "vigencia_projeto": "Vigência", "palavra_chave": "Termos Correspondentes"}
        larguras = {"titulo": 220, "portal": 120, "datas": 120, "vigencia_projeto": 120, "palavra_chave": 350}
        alinhamentos = {"titulo": "w", "portal": "w", "datas": "center", "vigencia_projeto": "center", "palavra_chave": "w"}

        for col in self.colunas_visiveis:
            self.tabela.heading(col, text=titulos[col], command=lambda c=col: self.ordenar_por_coluna(c))
            self.tabela.column(col, width=larguras[col], anchor=alinhamentos[col])

        if linhas_antigas:
            self.atualizar_tabela_local()

    def ordenar_por_coluna(self, id_coluna):
        """Ordena a Treeview de forma alfabética ou cronológica exata baseado nas tags internas."""
        itens = [(self.tabela.set(item, id_coluna), item) for item in self.tabela.get_children("")]
        
        if self.ultima_ordenacao["coluna"] == id_coluna:
            reverse = not self.ultima_ordenacao["reverse"]
        else:
            reverse = False
            
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
        """Alterna a exibição anexando o frame importado à esquerda e os botões de ação na barra superior."""
        if self.sidebar_visivel:
            if self.sidebar_filtros:
                self.sidebar_filtros.grid_forget()
                self.sidebar_filtros.destroy()
                self.sidebar_filtros = None
            
            if self.btn_aplicar_topo:
                self.btn_aplicar_topo.pack_forget()
                self.btn_aplicar_topo.destroy()
                self.btn_aplicar_topo = None
            if self.btn_limpar_topo:
                self.btn_limpar_topo.pack_forget()
                self.btn_limpar_topo.destroy()
                self.btn_limpar_topo = None
                
            self.sidebar_visivel = False
            self.btn_filtro_funil.configure(fg_color="#34495e", text="CONFIGURAR PARAMETROS E FILTROS")
            self.lbl_filtros_ativos.pack(side="left", padx=15, pady=5)
        else:
            self.sidebar_visivel = True
            self.btn_filtro_funil.configure(fg_color="#1f6aa5", text="FECHAR CONFIGURAÇÕES")
            self.lbl_filtros_ativos.pack_forget()
            
            self.sidebar_filtros = SidebarFiltros(self.tab_resultados, app_callback=self)
            self.sidebar_filtros.grid(row=0, column=0, rowspan=3, padx=(5, 10), pady=5, sticky="nsew")
            
            self.btn_aplicar_topo = ctk.CTkButton(
                self.frame_ferramentas, text="APLICAR FILTROS", corner_radius=0, width=130,
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                fg_color="#27ae60", hover_color="#219653", command=self.executar_acao_filtrar
            )
            self.btn_aplicar_topo.pack(side="left", padx=5, pady=5)

            self.btn_limpar_topo = ctk.CTkButton(
                self.frame_ferramentas, text="LIMPAR", corner_radius=0, width=80,
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                fg_color="#c0392b", hover_color="#962d22", command=self.executar_acao_limpar
            )
            self.btn_limpar_topo.pack(side="left", padx=5, pady=5)

    def alternar_sidebar_colunas(self):
        """Controla a abertura/fechamento do painel de colunas acoplado à direita (Coluna 2)."""
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
        """Dispara a lógica de salvamento e recarrega a tabela mantendo a sidebar aberta."""
        if self.sidebar_filtros:
            self.sidebar_filtros.adicionar_tag_evt()
            config.PORTAIS_ATIVOS = {k: v.get() for k, v in self.sidebar_filtros.dic_vars_locais.items()}
            config.salvar_configuracoes_usuario(self.sidebar_filtros.lista_tags, config.PORTAIS_ATIVOS)
            self.filtro_portais = config.PORTAIS_ATIVOS
            self.atualizar_tabela_local()

    def executar_acao_limpar(self):
        """Limpa as restrições cronológicas, portais e reseta as tags locais."""
        self.filtro_data_min = ""
        self.filtro_data_max = ""
        self.filtro_portais = {}
        
        config.PALAVRAS_CHAVE = []
        config.salvar_configuracoes_usuario([], config.PORTAIS_ATIVOS)
        
        if self.sidebar_filtros:
            self.sidebar_filtros.btn_min.configure(text="DATA INICIAL")
            self.sidebar_filtros.btn_max.configure(text="DATA FINAL")
            self.sidebar_filtros.resetar_tags_visuais()
            
        self.atualizar_tabela_local()

    def atualizar_tabela_local(self):
        for item in self.tabela.get_children(): 
            self.tabela.delete(item)
            
        try:
            resposta = config.supabase.table("editais").select("*").execute()
            editais = resposta.data if hasattr(resposta, 'data') else resposta
            
            # Ordenação cronológica base inicial
            editais_ordenados = sorted(
                editais, 
                key=lambda x: x.get("prazo_iso") if x.get("prazo_iso") is not None else "9999-12-31 23:59"
            )
            hoje = datetime.now().date()

            dt_corte_min = datetime.strptime(self.filtro_data_min, "%d/%m/%Y").date() if self.filtro_data_min else None
            dt_corte_max = datetime.strptime(self.filtro_data_max, "%d/%m/%Y").date() if self.filtro_data_max else None
            termos_filtro_usuario = [normalizar_texto(t) for t in config.PALAVRAS_CHAVE if t.strip()]

            # Lista temporária para fazermos o ranking por relevância antes de renderizar
            editais_para_inserir = []

            for edital in editais_ordenados:
                status_bruto = edital.get("status_ia") or ""
                status_limpo = str(status_bruto).strip().lower()

                if status_limpo in ["descartado_vencido", "pendente", ""]: 
                    continue

                portal_bruto = edital.get("portal", "N/A")
                portal_limpo = str(portal_bruto).strip().lower()
                modulo_chave = portal_limpo.split(" ")[0] if " " in portal_limpo else portal_limpo
                
                if self.filtro_portais and not self.filtro_portais.get(modulo_chave, True): 
                    continue
                
                prazo_texto_bruto = edital.get("datas", "") or ""
                prazo_iso_bruto = edital.get("prazo_iso", "") or ""
                
                texto_prazo_formatado = "A consultar"
                dt_item = None

                if prazo_iso_bruto and "9999" not in str(prazo_iso_bruto):
                    try:
                        data_iso_limpa = str(prazo_iso_bruto).strip().split(" ")[0]
                        dt_item = datetime.strptime(data_iso_limpa, "%Y-%m-%d").date()
                        texto_prazo_formatado = f"Até {dt_item.strftime('%d/%m/%Y')}"
                    except Exception:
                        dt_item = None

                if not dt_item:
                    texto_ba = prazo_texto_bruto.lower()
                    if "contínuo" in texto_ba or "fluxo" in texto_ba:
                        texto_prazo_formatado = "Fluxo Contínuo"
                    else:
                        texto_limpo = prazo_texto_bruto.replace("Envio de propostas ", "").strip()
                        if ", às" in texto_limpo:
                            texto_limpo = texto_limpo.split(", às")[0]
                        elif ", as" in texto_limpo:
                            texto_limpo = texto_limpo.split(", as")[0]
                        texto_prazo_formatado = texto_limpo.strip() if texto_limpo else "A consultar"

                if dt_item:
                    if dt_item < hoje: continue
                    if dt_corte_min and dt_item < dt_corte_min: continue
                    if dt_corte_max and dt_item > dt_corte_max: continue

                if len(texto_prazo_formatado) > 40 and "até" in texto_prazo_formatado.lower():
                    texto_prazo_formatado = texto_prazo_formatado.split(",")[0]

                # --- MATCH INTELIGENTE EM TAGS E NO TÍTULO (PROCURA AMBOS) ---
                tags_brutas_ia = edital.get("tags_ia", "") or ""
                lista_tags_edital = [tag.strip() for tag in tags_brutas_ia.split(",") if tag.strip()]
                titulo_edital_limpo = normalizar_texto(edital.get("titulo", ""))
                
                tags_encontradas_no_filtro = []
                for palavra_usuario in config.PALAVRAS_CHAVE:
                    palavra_usuario_limpa = normalizar_texto(palavra_usuario)
                    if not palavra_usuario_limpa:
                        continue
                    
                    if palavra_usuario_limpa in titulo_edital_limpo:
                        if palavra_usuario not in tags_encontradas_no_filtro:
                            tags_encontradas_no_filtro.append(palavra_usuario)
                        continue
                    
                    for tag_edital in lista_tags_edital:
                        tag_edital_limpa = normalizar_texto(tag_edital)
                        if palavra_usuario_limpa in tag_edital_limpa or tag_edital_limpa in palavra_usuario_limpa:
                            if palavra_usuario not in tags_encontradas_no_filtro:
                                tags_encontradas_no_filtro.append(palavra_usuario)

                if len(termos_filtro_usuario) > 0 and not tags_encontradas_no_filtro:
                    continue

                texto_coluna_termos = ", ".join(tags_encontradas_no_filtro) if tags_encontradas_no_filtro else "Geral / Amplo"
                vigencia_projeto = edital.get("vigencia_projeto", "N/A") or "N/A"

                mapa_valores_completos = {
                    "titulo": edital.get("titulo") or "Edital sem título",
                    "portal": portal_bruto,
                    "datas": texto_prazo_formatado,
                    "vigencia_projeto": vigencia_projeto,
                    "palavra_chave": texto_coluna_termos
                }
                
                # Guarda a contagem numérica de matches obtidos para o ranking
                qtd_matches = len(tags_encontradas_no_filtro)
                editais_para_inserir.append((qtd_matches, mapa_valores_completos, edital))

            # --- ENGINE DE RELEVÂNCIA: Prioriza maior quantidade de matches primeiro ---
            editais_para_inserir.sort(key=lambda x: x[0], reverse=True)

            # Renderiza fisicamente na tela os dados já ranqueados
            for qtd, valores_completos, edital_obj in editais_para_inserir:
                valores_filtrados = tuple(valores_completos[col] for col in self.colunas_visiveis)
                self.tabela.insert(
                    "", "end", 
                    values=valores_filtrados, 
                    tags=(edital_obj.get("url", ""), json.dumps(edital_obj))
                )

        except Exception as e: 
            print(f"Erro tabela nuvem: {e}")

    def acao_sincronizar(self):
        self.btn_sincronizar.configure(state="disabled", text="ATUALIZANDO...")
        self.lbl_status.configure(text="Status: Consultando base de editais no Supabase...")
        self.atualizar_tabela_local()
        self.btn_sincronizar.configure(state="normal", text="ATUALIZAR TABELA")
        self.lbl_status.configure(text="Status: Tabela sincronizada.")
        messagebox.showinfo("Concluido", "Tabela atualizada com sucesso.")

    def evento_linha_selecionada(self, event):
        item_selecionado = self.tabela.selection()
        if not item_selecionado: return
        
        tags = self.tabela.item(item_selecionado, "tags")
        if len(tags) >= 2:
            edital = json.loads(tags[1])
            texto_formatado = (
                f"PORTAL DE ORIGEM: {edital.get('portal','N/A')}\n"
                f"PRAZO DE SUBMISSAO: {edital.get('datas','N/A')}\n"
                f"PRAZO DE EXECUÇÃO: {edital.get('vigencia_projeto','N/A')}\n" 
                f"TAGS DO EDITAL (IA): {edital.get('tags_ia','Nenhuma')}\n"
                f"LINHA DE PESQUISA: {edital.get('pesquisa','N/A')}\n"
                f"ORCAMENTO / VERBA: {edital.get('subvencao','N/A')}\n\n"
                f"RESUMO DO ESCOPO:\n{edital.get('escopo','N/A')}"
            )
            self.txt_detalhes_escopo.configure(state="normal")
            self.txt_detalhes_escopo.delete("1.0", "end")
            self.txt_detalhes_escopo.insert("1.0", texto_formatado)
            self.txt_detalhes_escopo.configure(state="disabled")

    def abrir_link_edital(self, event):
        item_selecionado = self.tabela.selection()
        if item_selecionado:
            tags = self.tabela.item(item_selecionado, "tags")
            if tags:
                import webbrowser
                webbrowser.open(tags[0])

    def abrir_link_botao(self):
        item = self.tabela.selection()
        if not item:
            messagebox.showwarning("Aviso", "Selecione um edital.")
            return
        tags = self.tabela.item(item, "tags")
        if len(tags) > 0:
            import webbrowser
            webbrowser.open(tags[0])

if __name__ == "__main__":
    app = AppSincronizador()
    app.mainloop()
