import webbrowser
import customtkinter as ctk
from tkinter import messagebox

# 🔍 IMPORTAÇÃO COMPLETA DA ARQUITETURA DE PASTAS ATUALIZADA
from core import config, updater
from views import aba_resultados, aba_relatorio

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

class AppSincronizador(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Painel de Consulta de Editais")
        self._ajustar_janela_a_tela()

        # Variáveis de controle do funil de filtros locais
        self.filtro_portais = {}      
        self.filtro_data_min = ""     
        self.filtro_data_max = ""     

        self.grid_rowconfigure(1, weight=1) 
        self.grid_columnconfigure(0, weight=1)

        # ==============================================================================
        # 🛠️ PAINEL SUPERIOR DE COMANDOS GLOBAIS
        # ==============================================================================
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

        # ==============================================================================
        # 🗂️ GERENCIADOR DE ABAS CENTRALIZADO
        # ==============================================================================
        self.abas = ctk.CTkTabview(self, corner_radius=0)
        self.abas.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        
        self.tab_resultados = self.abas.add("EDITAIS ENCONTRADOS")
        self.tab_relatorio = self.abas.add("CONFIGURAR RELATÓRIO SEMANAL")

        # Configura as proporções internas da primeira aba de resultados
        self.tab_resultados.grid_rowconfigure(0, weight=0) 
        self.tab_resultados.grid_rowconfigure(1, weight=4, minsize=130)
        self.tab_resultados.grid_rowconfigure(2, weight=3, minsize=120)
        self.tab_resultados.grid_columnconfigure(0, weight=0) 
        self.tab_resultados.grid_columnconfigure(1, weight=1) 

        # 🚀 CONSTRUÇÃO DA ABA 1: Terceiriza para o módulo views/aba_resultados.py
        aba_resultados.inicializar_aba_resultados(self)
        
        # 🚀 CONSTRUÇÃO DA ABA 2: Terceiriza para o módulo views/aba_relatorio.py
        aba_relatorio.construir_interface_aba_relatorio(self.tab_relatorio, self)
        # ==============================================================================
        # 🧾 PAINEL INFERIOR DE STATUS E DE VERSÃO DO SISTEMA
        # ==============================================================================
        self.frame_base = ctk.CTkFrame(self, height=35, corner_radius=0)
        self.frame_base.grid(row=2, column=0, sticky="ew") 
        
        self.lbl_status = ctk.CTkLabel(
            self.frame_base, text="Status: Sistema conectado ao Supabase. Filtros locais ativos.", 
            font=ctk.CTkFont(family="Arial", size=11)
        )
        self.lbl_status.pack(side="left", padx=15, pady=5)

        # 1. TEXTO FIXO DA VERSÃO (Canto direito extremo, sem link)
        self.lbl_versao_num = ctk.CTkLabel(
            self.frame_base, 
            text=f"v{updater.VERSAO_ATUAL}",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color="#718096"
        )
        self.lbl_versao_num.pack(side="right", padx=(2, 15), pady=5)

        def abrir_link(event):
            webbrowser.open_new("https://github.com/Freireyjord/Edital_Searcher/discussions/categories/q-a")
        def ao_entrar(event):
            self.lbl_QA.configure(text_color="#144e78")
        def ao_sair(event):
            self.lbl_QA.configure(text_color="#1f6aa5")

        # 2. COMPONENTE CLICÁVEL EXCLUSIVO DO LINK Q&A (Colado ao lado esquerdo do número da versão)
        self.lbl_QA = ctk.CTkLabel(
            self.frame_base, 
            text="Q&A",
            font=ctk.CTkFont(family="Arial", size=11, underline=True), 
            text_color="#1f6aa5", 
            cursor="hand2" 
        )
        self.lbl_QA.bind("<Button-1>", abrir_link)
        self.lbl_QA.bind("<Enter>", ao_entrar)
        self.lbl_QA.bind("<Leave>", ao_sair)
        self.lbl_QA.pack(side="right", padx=(10, 2), pady=5)

        # Inicializa o carregamento dos registros na tabela local e dispara o validador de update
        aba_resultados.atualizar_tabela_local(self)
        self.after(2000, lambda: updater.verificar_e_aplicar_atualizacao(self.lbl_status, self))

    def _ajustar_janela_a_tela(self):
        """
        Dimensiona a janela conforme a resolução e a escala do Windows (notebooks de baixa
        resolução e escala 125%/150%): nunca maior que a tela e centralizada. Em telas pequenas
        abre maximizada.
        """
        escala = 1.0
        try:
            escala = float(self._get_window_scaling())
        except Exception:
            try:
                escala = self.winfo_fpixels("1i") / 96
            except Exception:
                pass
        escala = escala or 1.0

        tela_w, tela_h = self.winfo_screenwidth(), self.winfo_screenheight()   # pixels físicos
        logica_w, logica_h = tela_w / escala, tela_h / escala

        largura = int(min(1150, logica_w * 0.96))
        altura = int(min(760, logica_h * 0.88))      # reserva espaço p/ barra de tarefas e título
        self.minsize(min(820, largura), min(540, altura))

        x = max(0, int((tela_w - largura * escala) / 2))
        y = max(0, int((tela_h - altura * escala) / 2) - 20)
        self.geometry(f"{largura}x{altura}+{x}+{y}")

        if logica_w < 1280 or logica_h < 800:
            self.after(150, self._maximizar)

    def _maximizar(self):
        try:
            self.state("zoomed")
        except Exception:
            pass

    # ==============================================================================
    # 🎛️ MÉTODOS PONTES: REPASSAM O COMANDO PARA A LOGICA DENTRO DA PASTA VIEWS
    # ==============================================================================
    def alternar_sidebar_filtros(self):
        aba_resultados.alternar_sidebar_filtros(self)

    def alternar_sidebar_colunas(self):
        aba_resultados.alternar_sidebar_colunas(self)

    def reconfigurar_colunas_tabela(self):
        aba_resultados.reconfigurar_colunas_tabela(self)

    def executar_acao_filtrar(self):
        if self.sidebar_filtros:
            self.sidebar_filtros.adicionar_tag_evt()
            config.PORTAIS_ATIVOS = {k: v.get() for k, v in self.sidebar_filtros.dic_vars_locais.items()}
            config.salvar_configuracoes_usuario(
                self.sidebar_filtros.lista_tags, 
                config.PORTAIS_ATIVOS, 
                getattr(config, "EMAIL_RELATORIO", ""), 
                getattr(config, "FILTRAR_RELATORIO_POR_TAGS", False),
                getattr(config, "TAGS_RELATORIO", [])
            )
            self.filtro_portais = config.PORTAIS_ATIVOS
            aba_resultados.reaplicar_filtros_locais(self)
    def executar_acao_limpar(self):
        """Limpa TODOS os filtros (datas, portais e tags) e restaura a barra lateral."""
        self.filtro_data_min, self.filtro_data_max, self.filtro_portais = "", "", {}
        config.PALAVRAS_CHAVE = []
        config.PORTAIS_ATIVOS = {}      # vazio = todos os portais habilitados (inclusive os novos)
        config.salvar_configuracoes_usuario(
            [], 
            config.PORTAIS_ATIVOS, 
            getattr(config, "EMAIL_RELATORIO", ""), 
            getattr(config, "FILTRAR_RELATORIO_POR_TAGS", False),
            getattr(config, "TAGS_RELATORIO", [])
        )
        if self.sidebar_filtros:
            self.sidebar_filtros.resetar_tudo()
        aba_resultados.reaplicar_filtros_locais(self)

    def atualizar_tabela_local(self):
        aba_resultados.atualizar_tabela_local(self)

    def acao_sincronizar(self):
        """Recarrega a base de editais da nuvem em segundo plano."""
        self.btn_sincronizar.configure(state="disabled", text="ATUALIZANDO...")

        def ao_concluir(erro):
            self.btn_sincronizar.configure(state="normal", text="ATUALIZAR TABELA")
            if erro is None:
                messagebox.showinfo("Concluído", "Tabela atualizada com sucesso.")
            else:
                messagebox.showerror("Falha na atualização", f"Não foi possível consultar a base de editais:\n{erro}")

        aba_resultados.atualizar_tabela_local(self, ao_concluir=ao_concluir)

    def evento_linha_selecionada(self, event):
        aba_resultados.exibir_resumo_linha_selecionada(self)

    def abrir_link_edital(self, event):
        item_selecionado = self.tabela.selection()
        if item_selecionado:
            tags = self.tabela.item(item_selecionado, "tags")
            if tags and len(tags) > 0:
                webbrowser.open(tags[0])

    def abrir_link_botao(self):
        item = self.tabela.selection()
        if not item:
            messagebox.showwarning("Aviso", "Selecione um edital na tabela antes de abrir.")
            return
        tags = self.tabela.item(item, "tags")
        if tags and len(tags) > 0:
            webbrowser.open(tags[0])


# ==============================================================================
# 🚀 PONTO DE ENTRADA DO APLICATIVO CORPORATIVO
# ==============================================================================
if __name__ == "__main__":
    app = AppSincronizador()
    app.mainloop()