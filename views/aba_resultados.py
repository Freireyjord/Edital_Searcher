import json, threading

from datetime import datetime
from tkinter import ttk
import customtkinter as ctk

from core import config, editais_repo
from core.filtro_editais import aplicar_filtros
from views.filtros_sidebar import SidebarFiltros
from views.colunas_sidebar import SidebarColunas

def inicializar_aba_resultados(app):
    app.sidebar_filtros = None
    app.sidebar_visivel = False
    app.btn_aplicar_topo = None
    app.btn_limpar_topo = None
    
    # 🚨 ALTERADO: O sistema agora nasce com o estado de minimizado ativo
    app.detalhes_minimizado = True

    app.colunas_visiveis = ["titulo", "portal", "prazo_iso", "palavra_chave"]
    app.ultima_ordenacao = {"coluna": None, "reverse": False}
    app.cache_editais = []      
    app.cache_detalhes = {}     
    app._carregando = False

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

    # Lógica do botão de alternar estado do painel
    def alternar_painel_resumo():
        if app.detalhes_minimizado:
            app.tab_resultados.grid_rowconfigure(1, weight=4, minsize=130)
            app.tab_resultados.grid_rowconfigure(2, weight=3, minsize=120)
            app.frame_detalhes.grid(row=2, column=1, padx=(5, 0), pady=(10, 5), sticky="nsew")
            app.btn_minimizar_resumo.configure(text="OCULTAR RESUMO IA ▼")
            app.detalhes_minimizado = False
        else:
            app.frame_detalhes.grid_forget()
            app.tab_resultados.grid_rowconfigure(2, weight=0, minsize=0)
            app.tab_resultados.grid_rowconfigure(1, weight=1)
            app.btn_minimizar_resumo.configure(text="MOSTRAR RESUMO IA ▲")
            app.detalhes_minimizado = True

    # 🚨 ALTERADO: Texto padrão alterado para "MOSTRAR RESUMO IA ▲" para casar com a inicialização
    app.btn_minimizar_resumo = ctk.CTkButton(
        app.frame_ferramentas, text="MOSTRAR RESUMO IA ▲", corner_radius=12,
        font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
        fg_color="#1f6aa5", hover_color="#144e78", width=160, height=26,
        command=alternar_painel_resumo
    )
    app.btn_minimizar_resumo.pack(side="left", padx=30, pady=5)

    app.lbl_filtros_ativos = ctk.CTkLabel(
        app.frame_ferramentas, text="Filtros: Ativos.", 
        font=ctk.CTkFont(family="Arial", size=11, slant="italic"), text_color="#95a5a6"
    )
    app.lbl_filtros_ativos.pack(side="left", padx=15, pady=5)

    # 📊 CONFIGURAÇÃO DA TABELA TREEVIEW
    app.frame_tabela = ctk.CTkFrame(app.tab_resultados, corner_radius=0, fg_color="transparent")
    app.frame_tabela.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
    app.frame_tabela.grid_rowconfigure(0, weight=1)
    app.frame_tabela.grid_columnconfigure(0, weight=1)

    app.tabela = ttk.Treeview(app.frame_tabela, show="headings", style="Treeview")
    app.scroll_y_tabela = ttk.Scrollbar(app.frame_tabela, orient="vertical", command=app.tabela.yview)
    app.tabela.configure(yscrollcommand=app.scroll_y_tabela.set)

    reconfigurar_colunas_tabela(app)
    app.tabela.grid(row=0, column=0, sticky="nsew")
    app.scroll_y_tabela.grid(row=0, column=1, sticky="ns")
    
    app.tabela.bind("<<TreeviewSelect>>", app.evento_linha_selecionada)
    app.tabela.bind("<Double-1>", app.abrir_link_edital)

    # 📖 PAINEL DE LEITURA EMBUTIDO (RESUMO IA)
    app.frame_detalhes = ctk.CTkFrame(app.tab_resultados, corner_radius=0, border_width=1, border_color="#3a3d42")
    
    app.tab_resultados.grid_rowconfigure(2, weight=0, minsize=0)
    app.tab_resultados.grid_rowconfigure(1, weight=1) # Tabela ganha foco total
    
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



def _formatar_iso_para_br(data_iso):
    if not data_iso:
        return "A consultar"
    try:
        return datetime.strptime(str(data_iso).split(" ")[0], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(data_iso)


def reconfigurar_colunas_tabela(app):
    """Reconstrói a estrutura e o cabeçalho das colunas visíveis da tabela sem rolagem horizontal."""
    linhas_antigas = []
    for item in app.tabela.get_children():
        linhas_antigas.append((app.tabela.item(item, "values"), app.tabela.item(item, "tags")))

    app.tabela.configure(columns=tuple(app.colunas_visiveis))
    
    titulos = {
        "titulo": "Título do Edital", 
        "portal": "Portal de Origem", 
        "prazo_iso": "Prazo de Submissão", 
        "palavra_chave": "Termos Correspondentes"
    }
    
    # 🚨 ALTERADO: Larguras em proporções balanceadas para fechar o layout perfeitamente
    larguras = {
        "titulo": 300, 
        "portal": 150, 
        "prazo_iso": 120, 
        "palavra_chave": 250
    }
    alinhamentos = {"titulo": "w", "portal": "w", "prazo_iso": "center", "palavra_chave": "w"}

    for col in app.colunas_visiveis:
        app.tabela.heading(col, text=titulos[col], command=lambda c=col: ordenar_por_coluna(app, c))
        
        # 🚨 CRÍTICO: stretch=True faz com que as colunas ocupem o espaço proporcional e matem a barra horizontal!
        app.tabela.column(
            col, 
            width=larguras.get(col, 150), 
            minwidth=70, 
            anchor=alinhamentos.get(col, "w"), 
            stretch=True
        )

    if linhas_antigas:
        reaplicar_filtros_locais(app)


def ordenar_por_coluna(app, id_coluna):
    """Ordena cronologicamente ou alfabeticamente as colunas."""
    itens = [(app.tabela.set(item, id_coluna), item) for item in app.tabela.get_children("")]
    reverse = not app.ultima_ordenacao["reverse"] if app.ultima_ordenacao["coluna"] == id_coluna else False
    app.ultima_ordenacao = {"coluna": id_coluna, "reverse": reverse}

    def extrair_chave_ordenacao(par_item):
        valor_texto, id_item = par_item
        tags = app.tabela.item(id_item, "tags")
        if len(tags) >= 2:
            try:
                edital_data = json.loads(tags[1])
                # 🚨 ALTERADO: Se for a coluna prazo_iso, ordena diretamente pela string ISO YYYY-MM-DD
                if id_coluna == "prazo_iso":
                    iso_data = edital_data.get("prazo_iso")
                    return str(iso_data).split(" ")[0] if iso_data else ("9999-12-31" if not reverse else "0000-00-00")
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

def atualizar_tabela_local(app, ao_concluir=None):
    """
    Baixa a lista de editais do Supabase em segundo plano (a janela não congela)
    e redesenha a tabela. `ao_concluir(erro)` é chamado na thread da interface.
    """
    if getattr(app, "_carregando", False):
        return
    app._carregando = True
    if hasattr(app, "lbl_status"):
        app.lbl_status.configure(text="Status: Consultando base de editais no Supabase...")

    def tarefa():
        try:
            editais, erro = editais_repo.buscar_editais_visiveis(), None
        except Exception as e:
            editais, erro = None, e
        try:
            app.after(0, lambda: _finalizar_carga(app, editais, erro, ao_concluir))
        except Exception:
            pass   # janela já foi fechada

    threading.Thread(target=tarefa, daemon=True).start()


def _finalizar_carga(app, editais, erro, ao_concluir):
    app._carregando = False
    if erro is None:
        app.cache_editais = editais
        app.cache_detalhes.clear()
        renderizar_tabela(app)
        _atualizar_status_contagem(app)
        if getattr(app, "sidebar_filtros", None):
            app.sidebar_filtros.atualizar_portais()   # portais novos do Supabase aparecem no filtro
    else:
        print(f"Erro tabela nuvem: {erro}")
        if hasattr(app, "lbl_status"):
            app.lbl_status.configure(text=f"Status: Falha ao consultar o Supabase: {erro}")
    if ao_concluir:
        ao_concluir(erro)


def reaplicar_filtros_locais(app):
    """Refiltra os dados que já estão em memória (tags, portais, datas, colunas)."""
    renderizar_tabela(app)
    _atualizar_status_contagem(app)

def _atualizar_status_contagem(app):
    if hasattr(app, "lbl_status"):
        exibidos = len(app.tabela.get_children())
        app.lbl_status.configure(text=f"Status: {exibidos} editais exibidos ({len(app.cache_editais)} abertos na base).")

def renderizar_tabela(app):
    for item in app.tabela.get_children():
        app.tabela.delete(item)

    linhas = aplicar_filtros(
        app.cache_editais,
        portais=app.filtro_portais,
        data_min=app.filtro_data_min,
        data_max=app.filtro_data_max,
        palavras_chave=config.PALAVRAS_CHAVE,
    )
    for _qtd, valores, edital in linhas:
        # 🚨 ALTERADO: Formata os valores exibidos usando prazo_iso
        valores_exibicao = dict(valores)
        if "prazo_iso" in valores_exibicao:
            valores_exibicao["prazo_iso"] = _formatar_iso_para_br(edital.get("prazo_iso"))
            
        app.tabela.insert(
            "", "end",
            values=tuple(valores_exibicao.get(col, "") for col in app.colunas_visiveis),
            tags=(edital.get("url", ""), json.dumps(edital)),
        )

def exibir_resumo_linha_selecionada(app):
    """Mostra os dados da linha, carrega o resumo sob demanda e força a abertura do painel se estiver minimizado."""
    item_selecionado = app.tabela.selection()
    if not item_selecionado:
        return
    tags = app.tabela.item(item_selecionado, "tags")
    if len(tags) < 2:
        return

    # Se o resumo estiver minimizado, força a expansão automática do painel
    if getattr(app, "detalhes_minimizado", False):
        app.tab_resultados.grid_rowconfigure(1, weight=4, minsize=130)
        app.tab_resultados.grid_rowconfigure(2, weight=3, minsize=120)
        app.frame_detalhes.grid(row=2, column=1, padx=(5, 0), pady=(10, 5), sticky="nsew")
        app.btn_minimizar_resumo.configure(text="OCULTAR RESUMO IA ▼")
        app.detalhes_minimizado = False

    edital = json.loads(tags[1])
    url = edital.get("url", "")
    detalhe = app.cache_detalhes.get(url)
    _mostrar_detalhe(app, edital, detalhe)

    if detalhe is None and url:
        def tarefa():
            try:
                det = editais_repo.buscar_detalhe(url)
            except Exception as e:
                det = {"_erro": str(e)}
            try:
                app.after(0, lambda: _detalhe_carregado(app, url, det))
            except Exception:
                pass
        threading.Thread(target=tarefa, daemon=True).start()


def _detalhe_carregado(app, url, detalhe):
    if "_erro" not in detalhe:
        app.cache_detalhes[url] = detalhe
    # só atualiza o painel se o usuário ainda estiver na mesma linha
    item = app.tabela.selection()
    if not item:
        return
    tags = app.tabela.item(item, "tags")
    if len(tags) < 2:
        return
    edital = json.loads(tags[1])
    if edital.get("url") == url:
        _mostrar_detalhe(app, edital, detalhe)


def _mostrar_detalhe(app, edital, detalhe):
    if detalhe is None:
        pesquisa = verba = "Carregando..."
        escopo = "Carregando resumo do edital..."
    elif "_erro" in detalhe:
        pesquisa = verba = "N/A"
        escopo = f"Não foi possível carregar o resumo: {detalhe['_erro']}"
    else:
        pesquisa = detalhe.get("pesquisa") or "N/A"
        verba = detalhe.get("subvencao") or "N/A"
        escopo = detalhe.get("escopo") or "N/A"

    texto_formatado = (
        f"PORTAL DE ORIGEM: {edital.get('portal','N/A')}\n"
        f"DATA DE INÍCIO (ABERTURA): {_formatar_iso_para_br(edital.get('inicio_edital'))}\n"
        f"PRAZO FINAL DE SUBMISSÃO: {_formatar_iso_para_br(edital.get('prazo_iso'))}\n"
        f"VIGÊNCIA/PRAZO DE EXECUÇÃO DO PROJETO: {edital.get('vigencia_projeto','N/A')}\n"
        f"TAGS DO EDITAL (IA): {edital.get('tags_ia') or 'Nenhuma'}\n"
        f"LINHA DE PESQUISA: {pesquisa}\n"
        f"ORÇAMENTO / VERBA: {verba}\n\n"
        f"RESUMO DO ESCOPO:\n{escopo}"
    )
    app.txt_detalhes_escopo.configure(state="normal")
    app.txt_detalhes_escopo.delete("1.0", "end")
    app.txt_detalhes_escopo.insert("1.0", texto_formatado)
    app.txt_detalhes_escopo.configure(state="disabled")