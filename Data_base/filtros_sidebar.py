import customtkinter as ctk
import unicodedata
from tkcalendar import Calendar
import config

def normalizar_texto(texto):
    """Remove acentos, converte para minúsculo e limpa espaços extras."""
    if not texto:
        return ""
    texto = str(texto).strip().lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

class SidebarFiltros(ctk.CTkFrame):
    def __init__(self, master, app_callback, **kwargs):
        # Define largura fixa industrial para o painel lateral esquerdo
        super().__init__(master, width=290, corner_radius=0, border_width=1, border_color="#3a3d42", **kwargs)
        self.grid_propagate(False)
        
        self.app = app_callback  # Referência da tela principal para atualizar os dados

        lbl_pop_title = ctk.CTkLabel(self, text="FILTROS LOCAIS ATIVOS", font=ctk.CTkFont(family="Arial", size=13, weight="bold"))
        lbl_pop_title.pack(pady=(15, 10))
        
        # --- SEÇÃO 1: CALENDÁRIO ---
        frame_datas = ctk.CTkFrame(self, corner_radius=0, border_width=1, border_color="#2a2d32")
        frame_datas.pack(fill="x", padx=15, pady=5)
        
        lbl_d = ctk.CTkLabel(frame_datas, text="Intervalo de Prazos:", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
        lbl_d.pack(anchor="w", padx=15, pady=(10, 5))
        
        txt_d_min = self.app.filtro_data_min if self.app.filtro_data_min else "DATA INICIAL"
        self.btn_min = ctk.CTkButton(frame_datas, text=txt_d_min, corner_radius=0, fg_color="#2c3e50", command=lambda: self.selecionar_data_calendario("min"))
        self.btn_min.pack(fill="x", padx=15, pady=4)
        
        txt_d_max = self.app.filtro_data_max if self.app.filtro_data_max else "DATA FINAL"
        self.btn_max = ctk.CTkButton(frame_datas, text=txt_d_max, corner_radius=0, fg_color="#2c3e50", command=lambda: self.selecionar_data_calendario("max"))
        self.btn_max.pack(fill="x", padx=15, pady=(4, 15))

        # --- SEÇÃO 2: PORTAIS ---
        frame_matriz = ctk.CTkFrame(self, corner_radius=0, border_width=1, border_color="#2a2d32", height=180)
        frame_matriz.pack(fill="x", padx=15, pady=5)
        frame_matriz.pack_propagate(False)
        
        frame_header = ctk.CTkFrame(frame_matriz, height=26, corner_radius=0, fg_color="#1f6aa5")
        frame_header.pack(fill="x", side="top")
        
        lbl_h2 = ctk.CTkLabel(frame_header, text="PORTAIS DE ORIGEM", font=ctk.CTkFont(family="Arial", size=10, weight="bold"), text_color="white")
        lbl_h2.pack(anchor="w", padx=10, pady=2)
        
        scroll_portais = ctk.CTkScrollableFrame(frame_matriz, corner_radius=0, fg_color="transparent")
        scroll_portais.pack(fill="both", expand=True, padx=2, pady=2)

        arquivos_portais = ["cnpq", "finep", "fundep"]
        self.dic_vars_locais = {}
        for idx, portal_nome in enumerate(arquivos_portais):
            bg_linha = "#2a2d32" if idx % 2 == 0 else "#212325"
            frame_linha = ctk.CTkFrame(scroll_portais, height=30, corner_radius=0, fg_color=bg_linha)
            frame_linha.pack(fill="x", side="top", pady=1)
            
            estado_atual = config.PORTAIS_ATIVOS.get(portal_nome, True)
            v_loc = ctk.BooleanVar(value=estado_atual)
            self.dic_vars_locais[portal_nome] = v_loc
            
            chk = ctk.CTkCheckBox(frame_linha, text="", variable=v_loc, width=20, corner_radius=0)
            chk.pack(side="left", padx=10, pady=4)
            
            lbl_pname = ctk.CTkLabel(frame_linha, text=portal_nome.upper(), font=ctk.CTkFont(family="Arial", size=10, weight="bold"), text_color="#e0e0e0")
            lbl_pname.pack(side="left", padx=5, pady=4)

        # --- SEÇÃO 3: PALAVRAS-CHAVE (ALTURA FIXADA PARA NÃO EMPURRAR OS BOTÕES) ---
        frame_keywords = ctk.CTkFrame(self, corner_radius=0, border_width=1, border_color="#2a2d32")
        frame_keywords.pack(fill="x", padx=15, pady=5)
        
        lbl_kw = ctk.CTkLabel(frame_keywords, text="Tags de Busca (Enter ou Vírgula):", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
        lbl_kw.pack(anchor="w", padx=15, pady=(10, 3))
        
        self.entry_tag = ctk.CTkEntry(frame_keywords, placeholder_text="Adicionar palavra...", corner_radius=0, font=("Arial", 11))
        self.entry_tag.pack(fill="x", padx=15, pady=(0, 5))

        # Mudança essencial: altura máxima de 110px fixada para travar o crescimento na lateral
        self.scroll_tags = ctk.CTkScrollableFrame(frame_keywords, height=110, corner_radius=0, fg_color="#1e1e1e")
        self.scroll_tags.pack(fill="x", padx=15, pady=(0, 10))

        self.lista_tags = list(config.PALAVRAS_CHAVE)

        self.entry_tag.bind("<Return>", self.adicionar_tag_evt)
        self.entry_tag.bind(",", self.adicionar_tag_evt)
        self.renderizar_tags()

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

    def aplicar_filtros_acao(self):
        self.adicionar_tag_evt()
        config.PORTAIS_ATIVOS = {k: v.get() for k, v in self.dic_vars_locais.items()}
        config.salvar_configuracoes_usuario(self.lista_tags, config.PORTAIS_ATIVOS)
        self.app.filtro_portais = config.PORTAIS_ATIVOS
        self.app.atualizar_tabela_local()
        self.app.alternar_sidebar_filtros()
        
    def limpar_filtros_acao(self):
        self.app.filtro_data_min = ""
        self.app.filtro_data_max = ""
        self.app.filtro_portais = {}
        self.app.atualizar_tabela_local()
        self.app.alternar_sidebar_filtros()

    def resetar_tags_visuais(self):
        """Atualiza a lista local e redesenha as tags na tela após a limpeza."""
        self.lista_tags = list(config.PALAVRAS_CHAVE)
        self.renderizar_tags()
