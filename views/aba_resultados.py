import json
from datetime import datetime
from tkinter import ttk
import customtkinter as ctk

# 🔍 IMPORTAÇÃO DOS MÓDULOS DE CORE E OUTRAS VIEWS
from core import config
from views.filtros_sidebar import SidebarFiltros, normalizar_texto
from views.colunas_sidebar import SidebarColunas

def inicializar_aba_resultados(app):
    """
    Acopla os atributos de controle e monta a interface base de ferramentas,
    tabela e painel de leitura dentro da aba EDITAIS ENCONTRADOS.
    """
    # Mapeia as variáveis de controle local herdadas
    app.sidebar_filtros = None
    app.sidebar_visivel = False
    app.btn_aplicar_topo = None
    app.btn_limpar_topo = None
    
    app.colunas_visiveis = ["titulo", "portal", "datas", "vigencia_projeto", "palavra_chave"]
    app.ultima_ordenacao = {"coluna": None, "reverse": False}

    # 🛠️ BARRA DE FERRAMENTAS SUPERIOR
    app.frame_ferramentas = ctk.CTkFrame(app.tab_resultados, height=45, corner_radius=0, fg_color="transparent")
    app.frame_ferramentas.grid(row=0, column=1, padx=5, pady=(5, 5), sticky="ew")
    
    app.btn_filtro_funil = ctk.CTkButton(
        app.frame_ferramentas, text="CONFIGURAR PARAMETROS E FILTROS", corner_radius=0,
        font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
        fg_color="#34495e", hover_color="#2c3e50", width=250, command=app.alternar_sidebar_filtros
    )
    app.btn_filtro_funil.pack(side="left", padx=5, pady=5)

    app.btn_colunas_toggle = ctk.CTkButton(
        app.frame_ferramentas, text="CONFIGURAR COLUNAS", corner_radius=0,
        font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
        fg_color="#34495e", hover_color="#2c3e50", width=180, command=app.alternar_sidebar_colunas
    )
    app.btn_colunas_toggle.pack(side="right", padx=5, pady=5)

    app.lbl_filtros_ativos = ctk.CTkLabel(
        app.frame_ferramentas, text="Filtros: Operando com base nas suas tags locais.", 
        font=ctk.CTkFont(family="Arial", size=11, slant="italic"), text_color="#95a5a6"
    )
    app.lbl_filtros_ativos.pack(side="left", padx=15, pady=5)

    # 📊 CONFIGURAÇÃO DA TABELA TREEVIEW
    app.tabela = ttk.Treeview(app.tab_resultados, show="headings", style="Treeview")
    app.scroll_y_tabela = ttk.Scrollbar(app.tab_resultados, orient="vertical", command=app.tabela.yview)
    app.tabela.configure(yscrollcommand=app.scroll_y_tabela.set)
    
    reconfigurar_colunas_tabela(app)
    app.tabela.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
    app.scroll_y_tabela.grid(row=1, column=3, sticky="ns")
    
    app.tabela.bind("<<TreeviewSelect>>", app.evento_linha_selecionada)
    app.tabela.bind("<Double-1>", app.abrir_link_edital)

    # 📖 PAINEL DE LEITURA EMBUTIDO (RESUMO IA)
    app.frame_detalhes = ctk.CTkFrame(app.tab_resultados, corner_radius=0, border_width=1, border_color="#3a3d42")
    app.frame_detalhes.grid(row=2, column=1, padx=(5, 0), pady=(10, 5), sticky="nsew")
    
    lbl_titulo_detalhes = ctk.CTkLabel(
        app.frame_detalhes, text="RESUMO EXPANDIDO DO EDITAL SELECIONADO (GERADO POR IA)", 
        font=ctk.CTkFont(family="Arial", size=12, weight="bold"), text_color="#1f6aa5"
    )
    lbl_titulo_detalhes.pack(anchor="w", padx=15, pady=8)
    
    app.txt_detalhes_escopo = ctk.CTkTextbox(
        app.frame_detalhes, font=("Arial", 12), wrap="word", corner_radius=0, border_width=1, border_color="#2a2d32"
    )
    app.txt_detalhes_escopo.pack(fill="both", expand=True, padx=15, pady=(0, 15))
    app.txt_detalhes_escopo.insert("1.0", "Nenhum edital selecionado na tabela superior.")
    app.txt_detalhes_escopo.configure(state="disabled")
def reconfigurar_colunas_tabela(app):
    """Reconstrói a estrutura e o cabeçalho das colunas visíveis da tabela."""
    linhas_antigas = []
    for item in app.tabela.get_children():
        linhas_antigas.append((app.tabela.item(item, "values"), app.tabela.item(item, "tags")))

    app.tabela.configure(columns=tuple(app.colunas_visiveis))
    titulos = {
        "titulo": "Título do Edital", 
        "portal": "Portal de Origem", 
        "datas": "Prazo / Submissão", 
        "vigencia_projeto": "Vigência", 
        "palavra_chave": "Termos Correspondentes"
    }
    larguras = {"titulo": 220, "portal": 120, "datas": 120, "vigencia_projeto": 120, "palavra_chave": 350}
    alinhamentos = {"titulo": "w", "portal": "w", "datas": "center", "vigencia_projeto": "center", "palavra_chave": "w"}

    for col in app.colunas_visiveis:
        app.tabela.heading(col, text=titulos[col], command=lambda c=col: ordenar_por_coluna(app, c))
        app.tabela.column(col, width=larguras[col], anchor=alinhamentos[col])

    if linhas_antigas:
        atualizar_tabela_local(app)


def ordenar_por_coluna(app, id_coluna):
    """Ordena as linhas da tabela de forma dinâmica baseado na coluna clicada."""
    itens = [(app.tabela.set(item, id_coluna), item) for item in app.tabela.get_children("")]
    reverse = not app.ultima_ordenacao["reverse"] if app.ultima_ordenacao["coluna"] == id_coluna else False
    app.ultima_ordenacao = {"coluna": id_coluna, "reverse": reverse}

    def extrair_chave_ordenacao(par_item):
        valor_texto, id_item = par_item
        tags = app.tabela.item(id_item, "tags")
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
        app.tabela.move(item, "", index)


def alternar_sidebar_filtros(app):
    """Abre ou fecha o painel de filtros lateral esquerdo."""
    if app.sidebar_visivel:
        if app.sidebar_filtros:
            app.sidebar_filtros.grid_forget()
            app.sidebar_filtros.destroy()
            app.sidebar_filtros = None
        if app.btn_aplicar_topo: 
            app.btn_aplicar_topo.pack_forget()
            app.btn_aplicar_topo.destroy()
            app.btn_aplicar_topo = None
        if app.btn_limpar_topo: 
            app.btn_limpar_topo.pack_forget()
            app.btn_limpar_topo.destroy()
            app.btn_limpar_topo = None
        app.sidebar_visivel = False
        app.btn_filtro_funil.configure(fg_color="#34495e", text="CONFIGURAR PARAMETROS E FILTROS")
        app.lbl_filtros_ativos.pack(side="left", padx=15, pady=5)
    else:
        app.sidebar_visivel = True
        app.btn_filtro_funil.configure(fg_color="#1f6aa5", text="FECHAR CONFIGURAÇÕES")
        app.lbl_filtros_ativos.pack_forget()
        app.sidebar_filtros = SidebarFiltros(app.tab_resultados, app_callback=app)
        app.sidebar_filtros.grid(row=0, column=0, rowspan=3, padx=(5, 10), pady=5, sticky="nsew")
        
        app.btn_aplicar_topo = ctk.CTkButton(
            app.frame_ferramentas, text="APLICAR FILTROS", corner_radius=0, width=130, 
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"), fg_color="#27ae60", 
            hover_color="#219653", command=app.executar_acao_filtrar
        )
        app.btn_aplicar_topo.pack(side="left", padx=5, pady=5)
        
        app.btn_limpar_topo = ctk.CTkButton(
            app.frame_ferramentas, text="LIMPAR", corner_radius=0, width=80, 
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"), fg_color="#c0392b", 
            hover_color="#962d22", command=app.executar_acao_limpar
        )
        app.btn_limpar_topo.pack(side="left", padx=5, pady=5)


def alternar_sidebar_colunas(app):
    """Abre ou fecha o painel de exibição de colunas do lado direito."""
    if hasattr(app, 'sidebar_colunas_visivel') and app.sidebar_colunas_visivel:
        if hasattr(app, 'sidebar_colunas') and app.sidebar_colunas:
            app.sidebar_colunas.grid_forget()
            app.supabase_colunas = None
            app.sidebar_colunas.destroy()
            app.sidebar_colunas = None
        app.sidebar_colunas_visivel = False
        app.btn_colunas_toggle.configure(fg_color="#34495e", text="CONFIGURAR COLUNAS")
    else:
        app.sidebar_colunas_visivel = True
        app.btn_colunas_toggle.configure(fg_color="#1f6aa5", text="FECHAR COLUNAS")
        app.sidebar_colunas = SidebarColunas(app.tab_resultados, app_callback=app)
        app.sidebar_colunas.grid(row=0, column=2, rowspan=3, padx=(10, 5), pady=5, sticky="nsew")
def atualizar_tabela_local(app):
    """Consulta o banco de dados Supabase e atualiza as linhas da Treeview com base nos filtros locais."""
    for item in app.tabela.get_children(): 
        app.tabela.delete(item)
    try:
        resposta = config.supabase.table("editais").select("*").execute()
        editais = resposta.data if hasattr(resposta, 'data') else resposta
        editais_ordenados = sorted(editais, key=lambda x: x.get("prazo_iso") if x.get("prazo_iso") is not None else "9999-12-31 23:59")
        
        hoje = datetime.now().date()
        dt_corte_min = datetime.strptime(app.filtro_data_min, "%d/%m/%Y").date() if app.filtro_data_min else None
        dt_corte_max = datetime.strptime(app.filtro_data_max, "%d/%m/%Y").date() if app.filtro_data_max else None
        termos_filtro_usuario = [normalizar_texto(t) for t in config.PALAVRAS_CHAVE if t.strip()]
        editais_para_inserir = []

        for edital in editais_ordenados:
            status_limpo = str(edital.get("status_ia") or "").strip().lower()
            if status_limpo in ["descartado_vencido", "pendente", "erro_sem_texto", "expirado", ""]: 
                continue

            portal_bruto = edital.get("portal", "N/A")
            portal_limpo = str(portal_bruto).strip().lower()
            
            modulo_chave = portal_limpo.split(" ")[0] if " " in portal_limpo else portal_limpo
            if app.filtro_portais and not app.filtro_portais.get(modulo_chave, True): 
                continue
            
            prazo_texto_bruto, prazo_iso_bruto = edital.get("datas", "") or "", edital.get("prazo_iso", "") or ""
            texto_prazo_formatated = "A consultar"
            dt_item = None

            if prazo_iso_bruto and "9999" not in str(prazo_iso_bruto):
                try:
                    data_iso_limpa = str(prazo_iso_bruto).strip().split(" ")[0]
                    dt_item = datetime.strptime(data_iso_limpa, "%Y-%m-%d").date()
                    texto_prazo_formatated = f"Até {dt_item.strftime('%d/%m/%Y')}"
                except: 
                    dt_item = None

            if not dt_item:
                if "contínuo" in prazo_texto_bruto.lower() or "fluxo" in prazo_texto_bruto.lower(): 
                    texto_prazo_formatated = "Fluxo Contínuo"
                else:
                    texto_limpo = prazo_texto_bruto.replace("Envio de propostas ", "").strip()
                    texto_limpo = texto_limpo.split(", às")[0] if ", às" in texto_limpo else (texto_limpo.split(", as")[0] if ", as" in texto_limpo else texto_limpo)
                    texto_prazo_formatated = texto_limpo.strip() if texto_limpo else "A consultar"

            if dt_item:
                if dt_item < hoje or (dt_corte_min and dt_item < dt_corte_min) or (dt_corte_max and dt_item > dt_corte_max): 
                    continue

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
                    if palavra_usuario_limpa in normalizar_texto(tag_edital) or normalizar_texto(tag_edital) in palavra_usuario_limpa:
                        if palavra_usuario not in tags_encontradas_no_filtro: 
                            tags_encontradas_no_filtro.append(palavra_usuario)

            if len(termos_filtro_usuario) > 0 and not tags_encontradas_no_filtro: 
                continue
            texto_coluna_termos = ", ".join(tags_encontradas_no_filtro) if tags_encontradas_no_filtro else "Geral / Amplo"
            
            mapa_valores_completos = {
                "titulo": edital.get("titulo") or "Edital sem título", 
                "portal": portal_bruto, 
                "datas": texto_prazo_formatated, 
                "vigencia_projeto": edital.get("vigencia_projeto", "N/A") or "N/A", 
                "palavra_chave": texto_coluna_termos
            }
            
            editais_para_inserir.append((len(tags_encontradas_no_filtro), mapa_valores_completos, edital))

        editais_para_inserir.sort(key=lambda x: x[0], reverse=True)
        for qtd, valores_completos, edital_obj in editais_para_inserir:
            app.tabela.insert(
                "", "end", 
                values=tuple(valores_completos[col] for col in app.colunas_visiveis), 
                tags=(edital_obj.get("url", ""), json.dumps(edital_obj))
            )
    except Exception as e: 
        print(f"Erro tabela nuvem: {e}")


def exibir_resumo_linha_selecionada(app):
    """Captura o item ativo na Treeview e exibe o resumo textual formatado da IA no painel inferior."""
    item_selecionado = app.tabela.selection()
    if not item_selecionado: 
        return
    tags = app.tabela.item(item_selecionado, "tags")
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
        app.txt_detalhes_escopo.configure(state="normal")
        app.txt_detalhes_escopo.delete("1.0", "end")
        app.txt_detalhes_escopo.insert("1.0", texto_formatado)
        app.txt_detalhes_escopo.configure(state="disabled")
