import customtkinter as ctk
from tkcalendar import Calendar

# 🔍 IMPORTAÇÃO DO ARQUIVO DE CONFIGURAÇÃO DO CORE
from core import config
from core.filtro_editais import normalizar_texto, portais_disponiveis  # noqa: F401 (normalizar_texto reexportado)


class SidebarFiltros(ctk.CTkFrame):
    def __init__(self, master, app_callback, **kwargs):
        # Largura fixa; a altura acompanha a janela (o conteúdo rola se não couber)
        super().__init__(master, width=290, corner_radius=0, border_width=1, border_color="#3a3d42", **kwargs)
        self.grid_propagate(False)
        self.pack_propagate(False)

        self.app = app_callback  # Referência de escopo da janela mestre

        # Todo o conteúdo fica num painel rolável: em telas de baixa resolução nada fica escondido.
        self.conteudo = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.conteudo.pack(fill="both", expand=True)

        lbl_pop_title = ctk.CTkLabel(self.conteudo, text="FILTROS LOCAIS ATIVOS", font=ctk.CTkFont(family="Arial", size=13, weight="bold"))
        lbl_pop_title.pack(pady=(10, 10))

        # --- SEÇÃO 1: INTERVALOS DE DATAS ---
        frame_datas = ctk.CTkFrame(self.conteudo, corner_radius=0, border_width=1, border_color="#2a2d32")
        frame_datas.pack(fill="x", padx=8, pady=5)

        lbl_d = ctk.CTkLabel(frame_datas, text="Intervalo de Prazos:", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
        lbl_d.pack(anchor="w", padx=12, pady=(10, 5))

        txt_d_min = self.app.filtro_data_min if self.app.filtro_data_min else "DATA INICIAL"
        self.btn_min = ctk.CTkButton(frame_datas, text=txt_d_min, corner_radius=0, fg_color="#2c3e50", command=lambda: self.selecionar_data_calendario("min"))
        self.btn_min.pack(fill="x", padx=12, pady=4)

        txt_d_max = self.app.filtro_data_max if self.app.filtro_data_max else "DATA FINAL"
        self.btn_max = ctk.CTkButton(frame_datas, text=txt_d_max, corner_radius=0, fg_color="#2c3e50", command=lambda: self.selecionar_data_calendario("max"))
        self.btn_max.pack(fill="x", padx=12, pady=(4, 12))

        # --- SEÇÃO 2: PORTAIS DE ORIGEM (descobertos a partir do Supabase) ---
        frame_matriz = ctk.CTkFrame(self.conteudo, corner_radius=0, border_width=1, border_color="#2a2d32")
        frame_matriz.pack(fill="x", padx=8, pady=5)

        frame_header = ctk.CTkFrame(frame_matriz, height=26, corner_radius=0, fg_color="#1f6aa5")
        frame_header.pack(fill="x", side="top")

        lbl_h2 = ctk.CTkLabel(frame_header, text="PORTAIS DE ORIGEM", font=ctk.CTkFont(family="Arial", size=10, weight="bold"), text_color="white")
        lbl_h2.pack(anchor="w", padx=10, pady=2)

        self.frame_lista_portais = ctk.CTkFrame(frame_matriz, corner_radius=0, fg_color="transparent")
        self.frame_lista_portais.pack(fill="x", padx=2, pady=2)

        self.dic_vars_locais = {}
        self._montar_lista_portais()

        # --- SEÇÃO 3: PALAVRAS-CHAVE ---
        frame_keywords = ctk.CTkFrame(self.conteudo, corner_radius=0, border_width=1, border_color="#2a2d32")
        frame_keywords.pack(fill="x", padx=8, pady=5)

        lbl_kw = ctk.CTkLabel(frame_keywords, text="Tags de Busca (Enter ou Vírgula):", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
        lbl_kw.pack(anchor="w", padx=12, pady=(10, 3))

        self.entry_tag = ctk.CTkEntry(frame_keywords, placeholder_text="Adicionar palavra...", corner_radius=0, font=("Arial", 11))
        self.entry_tag.pack(fill="x", padx=12, pady=(0, 5))

        # Container simples (sem rolagem própria: o painel externo já rola; evita roda do mouse duplicada)
        self.scroll_tags = ctk.CTkFrame(frame_keywords, height=50, corner_radius=0, fg_color="#1e1e1e")
        self.scroll_tags.pack(fill="x", padx=12, pady=(0, 10))

        self.lista_tags = list(config.PALAVRAS_CHAVE)

        self.entry_tag.bind("<Return>", self.adicionar_tag_evt)
        self.entry_tag.bind(",", self.adicionar_tag_evt)
        self.renderizar_tags()

    # ------------------------------------------------------------------ portais
    def _montar_lista_portais(self):
        """Desenha um checkbox por portal presente nos editais carregados do Supabase."""
        for widget in self.frame_lista_portais.winfo_children():
            widget.destroy()

        portais = portais_disponiveis(getattr(self.app, "cache_editais", []))
        if not portais:
            ctk.CTkLabel(
                self.frame_lista_portais, text="Nenhum portal carregado ainda.\nClique em ATUALIZAR TABELA.",
                font=ctk.CTkFont(family="Arial", size=10), text_color="#95a5a6", justify="left"
            ).pack(anchor="w", padx=10, pady=10)
            return

        for idx, (chave, rotulo) in enumerate(portais):
            bg_linha = "#2a2d32" if idx % 2 == 0 else "#212325"
            frame_linha = ctk.CTkFrame(self.frame_lista_portais, height=30, corner_radius=0, fg_color=bg_linha)
            frame_linha.pack(fill="x", side="top", pady=1)

            # Reaproveita a variável se o portal já estava na tela; portal novo nasce marcado
            # (ou com o estado salvo no config_app.json).
            v_loc = self.dic_vars_locais.get(chave)
            if v_loc is None:
                v_loc = ctk.BooleanVar(value=config.PORTAIS_ATIVOS.get(chave, True))
                self.dic_vars_locais[chave] = v_loc

            chk = ctk.CTkCheckBox(frame_linha, text="", variable=v_loc, width=20, corner_radius=0)
            chk.pack(side="left", padx=10, pady=4)

            lbl_pname = ctk.CTkLabel(frame_linha, text=rotulo.upper(), font=ctk.CTkFont(family="Arial", size=10, weight="bold"), text_color="#e0e0e0")
            lbl_pname.pack(side="left", padx=5, pady=4)

    def atualizar_portais(self):
        """Chamado quando a lista de editais é recarregada: portais novos aparecem sem mexer no código."""
        self._montar_lista_portais()

    # ------------------------------------------------------------------ calendário
    def selecionar_data_calendario(self, tipo):
        top_cal = ctk.CTkToplevel(self)
        top_cal.title("Calendario")
        top_cal.geometry("280x280")
        top_cal.resizable(False, False)
        top_cal.transient(self)
        top_cal.grab_set()

        cal = Calendar(top_cal, selectmode='day', locale='pt_BR', date_pattern='dd/mm/yyyy')
        cal.pack(pady=10, fill="both", expand=True)

        def confirmar_data():
            data_sel = cal.get_date()
            if tipo == "min":
                self.btn_min.configure(text=data_sel)
                self.app.filtro_data_min = data_sel
            else:
                self.btn_max.configure(text=data_sel)
                self.app.filtro_data_max = data_sel
            top_cal.destroy()

        btn_conf = ctk.CTkButton(top_cal, text="CONFIRMAR", corner_radius=0, font=ctk.CTkFont(family="Arial", size=11, weight="bold"), command=confirmar_data)
        btn_conf.pack(pady=5)

    # ------------------------------------------------------------------ tags
    def renderizar_tags(self):
        for widget in self.scroll_tags.winfo_children():
            widget.destroy()

        LARGURA_MAXIMA_CONTAINER = 210
        largura_acumulada = 0

        linha_atual = ctk.CTkFrame(self.scroll_tags, fg_color="transparent")
        linha_atual.pack(anchor="w", fill="x", pady=1)

        for tag_texto in self.lista_tags:
            largura_estimada_tag = (len(tag_texto) * 8) + 42

            if largura_acumulada + largura_estimada_tag > LARGURA_MAXIMA_CONTAINER and largura_acumulada > 0:
                linha_atual = ctk.CTkFrame(self.scroll_tags, fg_color="transparent")
                linha_atual.pack(anchor="w", fill="x", pady=1)
                largura_acumulada = 0

            tag_box = ctk.CTkFrame(linha_atual, fg_color="#1f6aa5", corner_radius=12)
            tag_box.pack(side="left", padx=2, pady=1)

            lbl_t = ctk.CTkLabel(tag_box, text=tag_texto, font=ctk.CTkFont(family="Arial", size=9, weight="bold"), text_color="white")
            lbl_t.pack(side="left", padx=(6, 3), pady=1)

            def remover_tag(t=tag_texto):
                if t in self.lista_tags:
                    self.lista_tags.remove(t)
                    self.renderizar_tags()

            btn_del = ctk.CTkButton(tag_box, text="✕", width=14, height=14, corner_radius=7, fg_color="transparent", hover_color="#c0392b", font=("Arial", 8, "bold"), command=remover_tag)
            btn_del.pack(side="right", padx=(0, 3), pady=1)

            largura_acumulada += largura_estimada_tag

    def adicionar_tag_evt(self, event=None):
        texto = self.entry_tag.get().strip().replace(",", "")
        if texto:
            if texto not in self.lista_tags:
                self.lista_tags.append(texto)
                self.renderizar_tags()
            self.entry_tag.delete(0, "end")
        return "break"

    def resetar_tags_visuais(self):
        """Atualiza a lista local e redesenha as tags na tela após a limpeza."""
        self.lista_tags = list(config.PALAVRAS_CHAVE)
        self.renderizar_tags()

    # ------------------------------------------------------------------ reset geral
    def resetar_tudo(self):
        """Volta a barra lateral ao estado 'sem filtros': datas, portais e tags."""
        self.btn_min.configure(text="DATA INICIAL")
        self.btn_max.configure(text="DATA FINAL")
        for variavel in self.dic_vars_locais.values():
            variavel.set(True)
        self.entry_tag.delete(0, "end")
        self.resetar_tags_visuais()