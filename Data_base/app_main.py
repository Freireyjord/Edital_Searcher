import json
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
import re

# Importação da biblioteca para o calendário financeiro
from tkcalendar import Calendar

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

        # ------------------ PAINEL SUPERIOR INDUSTRIAL (CANTOS RETOS) ------------------
        self.frame_topo = ctk.CTkFrame(self, corner_radius=0, border_width=1, border_color="#3a3d42")
        self.frame_topo.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        
        self.lbl_titulo = ctk.CTkLabel(
            self.frame_topo, text="PESQUISA INTELIGENTE DE EDITAIS (PRODUÇÃO)", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold")
        )
        self.lbl_titulo.pack(side="left", padx=15, pady=15)

        # Botão agora apenas atualiza a tabela com o banco de dados
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

        # ------------------ PAINEL CENTRAL SIMPLIFICADO ------------------
        self.abas = ctk.CTkTabview(self, corner_radius=0)
        self.abas.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        
        self.tab_resultados = self.abas.add("EDITAIS ENCONTRADOS")

        self.tab_resultados.grid_rowconfigure(0, weight=1) 
        self.tab_resultados.grid_rowconfigure(1, weight=4) 
        self.tab_resultados.grid_rowconfigure(2, weight=3) 
        self.tab_resultados.grid_columnconfigure(0, weight=1)
        
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
        frame_ferramentas = ctk.CTkFrame(self.tab_resultados, height=45, corner_radius=0, fg_color="transparent")
        frame_ferramentas.grid(row=0, column=0, padx=5, pady=(5, 5), sticky="ew")
        
        self.btn_filtro_funil = ctk.CTkButton(
            frame_ferramentas, text="CONFIGURAR PARAMETROS E FILTROS", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            fg_color="#34495e", hover_color="#2c3e50", width=250, command=self.abrir_popup_filtros
        )
        self.btn_filtro_funil.pack(side="left", padx=5, pady=5)

        self.lbl_filtros_ativos = ctk.CTkLabel(
            frame_ferramentas, text="Filtros: Operando com base nas suas tags locais.", 
            font=ctk.CTkFont(family="Arial", size=11, slant="italic"), text_color="#95a5a6"
        )
        self.lbl_filtros_ativos.pack(side="left", padx=15, pady=5)

    def configurar_painel_leitura_embutido(self):
        self.frame_detalhes = ctk.CTkFrame(self.tab_resultados, corner_radius=0, border_width=1, border_color="#3a3d42")
        self.frame_detalhes.grid(row=2, column=0, padx=5, pady=(10, 5), sticky="nsew")
        
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
    def abrir_popup_filtros(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Configuracoes de Filtros")
        popup.geometry("680x600")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        
        lbl_pop_title = ctk.CTkLabel(popup, text="PARAMETROS DE FILTRO LOCAL", font=ctk.CTkFont(family="Arial", size=14, weight="bold"))
        lbl_pop_title.pack(pady=(15, 10))
        
        frame_superior = ctk.CTkFrame(popup, fg_color="transparent")
        frame_superior.pack(fill="x", padx=20, pady=5)
        
        # Filtro de Datas (Calendário)
        frame_datas = ctk.CTkFrame(frame_superior, corner_radius=0, border_width=1, border_color="#3a3d42", width=310, height=200)
        frame_datas.pack(side="left", fill="both", expand=True, padx=(0, 5))
        frame_datas.pack_propagate(False)
        
        lbl_d = ctk.CTkLabel(frame_datas, text="Filtrar por intervalo de prazos:", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
        lbl_d.pack(anchor="w", padx=15, pady=(15, 10))
        
        def selecionar_data_calendario(btn_alvo, tipo):
            top_cal = ctk.CTkToplevel(popup)
            top_cal.title("Calendario")
            top_cal.geometry("280x280")
            top_cal.resizable(False, False)
            top_cal.transient(popup)
            top_cal.grab_set()

            cal = Calendar(top_cal, selectmode='day', locale='pt_BR', date_pattern='dd/mm/yyyy')
            cal.pack(pady=10, fill="both", expand=True)

            def confirmar_data():
                data_sel = cal.get_date()
                btn_alvo.configure(text=data_sel)
                if tipo == "min": self.filtro_data_min = data_sel
                else: self.filtro_data_max = data_sel
                top_cal.destroy()

            btn_conf = ctk.CTkButton(top_cal, text="CONFIRMAR", corner_radius=0, font=ctk.CTkFont(family="Arial", size=11, weight="bold"), command=confirmar_data)
            btn_conf.pack(pady=5)

        txt_d_min = self.filtro_data_min if self.filtro_data_min else "DATA INICIAL"
        btn_min = ctk.CTkButton(frame_datas, text=txt_d_min, corner_radius=0, fg_color="#2c3e50", command=lambda: selecionar_data_calendario(btn_min, "min"))
        btn_min.pack(fill="x", padx=15, pady=5)
        
        lbl_ate = ctk.CTkLabel(frame_datas, text="ate", font=ctk.CTkFont(family="Arial", size=11))
        lbl_ate.pack(pady=2)
        
        txt_d_max = self.filtro_data_max if self.filtro_data_max else "DATA FINAL"
        btn_max = ctk.CTkButton(frame_datas, text=txt_d_max, corner_radius=0, fg_color="#2c3e50", command=lambda: selecionar_data_calendario(btn_max, "max"))
        btn_max.pack(fill="x", padx=15, pady=5)
        # Filtro de Portais (Lado Direito da Janela)
        frame_matriz = ctk.CTkFrame(frame_superior, corner_radius=0, border_width=1, border_color="#3a3d42", width=320, height=200)
        frame_matriz.pack(side="right", fill="both", expand=True, padx=(5, 0))
        frame_matriz.pack_propagate(False)
        
        frame_header = ctk.CTkFrame(frame_matriz, height=28, corner_radius=0, fg_color="#1f6aa5")
        frame_header.pack(fill="x", side="top")
        
        lbl_h2 = ctk.CTkLabel(frame_header, text="SELECIONAR PORTAIS DE ORIGEM", font=ctk.CTkFont(family="Arial", size=10, weight="bold"), text_color="white")
        lbl_h2.pack(anchor="w", padx=10, pady=3)
        
        scroll_portais = ctk.CTkScrollableFrame(frame_matriz, corner_radius=0, fg_color="transparent")
        scroll_portais.pack(fill="both", expand=True, padx=2, pady=2)

        arquivos_portais = ["cnpq", "finep", "fundep"]
        
        dic_vars_locais = {}
        for idx, portal_nome in enumerate(arquivos_portais):
            bg_linha = "#2a2d32" if idx % 2 == 0 else "#212325"
            frame_linha = ctk.CTkFrame(scroll_portais, height=34, corner_radius=0, fg_color=bg_linha)
            frame_linha.pack(fill="x", side="top", pady=1)
            
            estado_atual = config.PORTAIS_ATIVOS.get(portal_nome, True)
            v_loc = ctk.BooleanVar(value=estado_atual)
            dic_vars_locais[portal_nome] = v_loc
            
            chk = ctk.CTkCheckBox(frame_linha, text="", variable=v_loc, width=20, corner_radius=0)
            chk.pack(side="left", padx=15, pady=6)
            
            lbl_pname = ctk.CTkLabel(frame_linha, text=portal_nome.upper(), font=ctk.CTkFont(family="Arial", size=11, weight="bold"), text_color="#e0e0e0")
            lbl_pname.pack(side="left", padx=10, pady=6)
        # Sistema de Tags das Palavras-Chave locais (Parte Inferior da Janela)
        frame_keywords = ctk.CTkFrame(popup, corner_radius=0, border_width=1, border_color="#3a3d42")
        frame_keywords.pack(fill="x", padx=20, pady=10)
        
        lbl_kw = ctk.CTkLabel(frame_keywords, text="Palavras-Chave de Interesse (Pressione Enter/Virgula):", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
        lbl_kw.pack(anchor="w", padx=15, pady=(10, 5))
        
        entry_tag = ctk.CTkEntry(frame_keywords, placeholder_text="Digite um termo para filtrar a exibição da tabela...", corner_radius=0, font=("Arial", 11))
        entry_tag.pack(fill="x", padx=15, pady=(0, 5))

        scroll_tags = ctk.CTkScrollableFrame(frame_keywords, height=130, corner_radius=0, fg_color="#1e1e1e")
        scroll_tags.pack(fill="x", padx=15, pady=(0, 10))

        lista_tags = list(config.PALAVRAS_CHAVE)

        def renderizar_tags():
            for widget in scroll_tags.winfo_children():
                widget.destroy()

            LARGURA_MAXIMA_CONTAINER = 580
            largura_acumulada = 0

            linha_atual = ctk.CTkFrame(scroll_tags, fg_color="transparent")
            linha_atual.pack(anchor="w", fill="x", pady=2)

            for tag_texto in lista_tags:
                largura_estimada_tag = (len(tag_texto) * 8) + 42 

                if largura_acumulada + largura_estimada_tag > LARGURA_MAXIMA_CONTAINER and largura_acumulada > 0:
                    linha_atual = ctk.CTkFrame(scroll_tags, fg_color="transparent")
                    linha_atual.pack(anchor="w", fill="x", pady=2)
                    largura_acumulada = 0

                tag_box = ctk.CTkFrame(linha_atual, fg_color="#1f6aa5", corner_radius=12)
                tag_box.pack(side="left", padx=3, pady=2)

                lbl_t = ctk.CTkLabel(tag_box, text=tag_texto, font=ctk.CTkFont(family="Arial", size=10, weight="bold"), text_color="white")
                lbl_t.pack(side="left", padx=(8, 4), pady=2)

                def remover_tag(t=tag_texto):
                    if t in lista_tags:
                        lista_tags.remove(t)
                        renderizar_tags()

                btn_del = ctk.CTkButton(tag_box, text="✕", width=16, height=16, corner_radius=8, fg_color="transparent", hover_color="#c0392b", font=("Arial", 9, "bold"), command=remover_tag)
                btn_del.pack(side="right", padx=(0, 4), pady=2)

                largura_acumulada += largura_estimada_tag
        def adicionar_tag_evt(event=None):
            texto = entry_tag.get().strip().replace(",", "")
            if texto:
                if texto not in lista_tags:
                    lista_tags.append(texto)
                    renderizar_tags()
                entry_tag.delete(0, "end")
            return "break"

        entry_tag.bind("<Return>", adicionar_tag_evt)
        entry_tag.bind(",", adicionar_tag_evt)
        renderizar_tags()

        def aplicar_filtros_acao():
            adicionar_tag_evt()
        
            config.PORTAIS_ATIVOS = {k: v.get() for k, v in dic_vars_locais.items()}
            config.salvar_configuracoes_usuario(lista_tags, config.PORTAIS_ATIVOS)
            
            self.filtro_portais = config.PORTAIS_ATIVOS
            self.atualizar_tabela_local()
            popup.destroy()
            
        def limpar_filtros_acao():
            self.filtro_data_min = ""
            self.filtro_data_max = ""
            self.filtro_portais = {}
            self.atualizar_tabela_local()
            popup.destroy()

        frame_botoes = ctk.CTkFrame(popup, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20, pady=(5, 15))

        btn_limpar = ctk.CTkButton(frame_botoes, text="LIMPAR FILTROS", corner_radius=0, fg_color="#c0392b", hover_color="#962d22", command=limpar_filtros_acao)
        btn_limpar.pack(side="left")
        btn_aplicar = ctk.CTkButton(frame_botoes, text="FILTRAR VISÃO", corner_radius=0, fg_color="#27ae60", hover_color="#219653", command=aplicar_filtros_acao)
        btn_aplicar.pack(side="right")

    def atualizar_tabela_local(self):
        # Limpa todas as linhas existentes na tabela antes de recarregar
        for item in self.tabela.get_children(): 
            self.tabela.delete(item)
            
        try:
            # 1. Puxa os dados atualizados direto do Supabase
            resposta = config.supabase.table("editais").select("*").execute()
            editais = resposta.data
            
            # Ordenação segura contra valores nulos
            editais_ordenados = sorted(
                editais, 
                key=lambda x: x.get("prazo_iso") if x.get("prazo_iso") is not None else "9999-12-31 23:59"
            )
            hoje = datetime.now().date()

            # Captura os limites de datas configurados na interface
            dt_corte_min = datetime.strptime(self.filtro_data_min, "%d/%m/%Y").date() if self.filtro_data_min else None
            dt_corte_max = datetime.strptime(self.filtro_data_max, "%d/%m/%Y").date() if self.filtro_data_max else None
            termos_filtro_usuario = [t.lower().strip() for t in config.PALAVRAS_CHAVE if t.strip()]

            for edital in editais_ordenados:
                # Captura o status convertendo para minúsculo e remove espaços extras
                status_bruto = edital.get("status_ia") or ""
                status_limpo = str(status_bruto).strip().lower()

                # Ignora editais descartados, vencidos ou que ainda estão pendentes de processamento
                if status_limpo in ["descartado_vencido", "pendente", ""]: 
                    continue

                # Filtro por Portal de Origem ativo/inativo
                portal_bruto = edital.get("portal", "N/A")
                modulo_chave = portal_bruto.split(" ")[0].strip().lower() if " " in portal_bruto else portal_bruto.strip().lower()
                
                if self.filtro_portais and not self.filtro_portais.get(modulo_chave, True): 
                    continue
                
                # --- TRATAMENTO E FORMATAÇÃO VISUAL INTELIGENTE DO PRAZO (MÓDULO CORRIGIDO) ---
                prazo_texto_bruto = edital.get("datas", "") or ""
                prazo_iso_bruto = edital.get("prazo_iso", "") or ""
                
                texto_prazo_formatado = "A consultar"
                dt_item = None

                # 1. Tenta decodificar o prazo estruturado gerado pela IA (Formato ISO)
                if prazo_iso_bruto and "9999" not in str(prazo_iso_bruto):
                    try:
                        # Extrai apenas a data pura (caso venha com carimbo de hora junto)
                        data_iso_limpa = str(prazo_iso_bruto).split(" ")[0].strip()
                        dt_item = datetime.strptime(data_iso_limpa, "%Y-%m-%d").date()
                        texto_prazo_formatado = f"Até {dt_item.strftime('%d/%m/%Y')}"
                    except Exception as e_date:
                        dt_item = None

                # 2. Caso a IA não tenha gerado um ISO válido, recorre a termos textuais comuns
                if not dt_item:
                    texto_ba = prazo_texto_bruto.lower()
                    if "contínuo" in texto_ba or "fluxo" in texto_ba:
                        texto_prazo_formatado = "Fluxo Contínuo"
                    else:
                        # Evita o corte cego [:30]. Limpa os prefixos e mantém o texto legível
                        texto_limpo = prazo_texto_bruto.replace("Envio de propostas ", "")
                        texto_limpo = texto_limpo.split(", às")[0].split(", as")[0].strip() # Oculta o horário
                        texto_prazo_formatado = texto_limpo if texto_limpo else "A consultar"

                # 3. Filtros cronológicos baseados no calendário da Interface
                if dt_item:
                    if dt_item < hoje: 
                        continue
                    if dt_corte_min and dt_item < dt_corte_min: 
                        continue
                    if dt_corte_max and dt_item > dt_corte_max: 
                        continue
 
                # Remove o excesso de texto caso o robô tenha trazido informações de horário muito longas
                if len(texto_prazo_formatado) > 40 and "até" in texto_prazo_formatado.lower():
                    texto_prazo_formatado = texto_prazo_formatado.split(",")[0] # Corta o "às 17:00" para caber na tabela

                # Filtros cronológicos baseados na data limite estruturada (apenas se dt_item foi mapeado)
                if dt_item:
                    if dt_item < hoje: continue
                    if dt_corte_min and dt_item < dt_corte_min: continue
                    if dt_corte_max and dt_item > dt_corte_max: continue

                # --- LÓGICA DO FILTRO DINÂMICO DE MATCH DE TAGS (IA vs USUÁRIO) ---
                tags_brutas_ia = edital.get("tags_ia", "") or ""
                lista_tags_edital = [tag.strip().lower() for tag in tags_brutas_ia.split(",") if tag.strip()]
                
                tags_encontradas_no_filtro = []
                for palavra_usuario in config.PALAVRAS_CHAVE:
                    palavra_usuario_limpa = palavra_usuario.strip().lower()
                    radical = palavra_usuario_limpa[:-1] if len(palavra_usuario_limpa) > 5 else palavra_usuario_limpa
                    
                    for tag_edital in lista_tags_edital:
                        if radical in tag_edital or tag_edital in palavra_usuario_limpa:
                            if palavra_usuario not in tags_encontradas_no_filtro:
                                tags_encontradas_no_filtro.append(palavra_usuario)

                # Só descarta por falta de palavra-chave se o usuário REALMENTE digitou algum termo
                if len(termos_filtro_usuario) > 0 and not tags_encontradas_no_filtro:
                    continue

                texto_coluna_termos = ", ".join(tags_encontradas_no_filtro) if tags_encontradas_no_filtro else "Geral / Amplo"

                # Insere os dados formatados perfeitamente nas colunas da Treeview
                self.tabela.insert(
                    "", "end", 
                    values=(portal_bruto, texto_prazo_formatado, texto_coluna_termos), 
                    tags=(edital.get("url", ""), json.dumps(edital))
                )
        except Exception as e: 
            print(f"Erro tabela nuvem: {e}")


    def configurar_tabela_resultados(self):
        colunas = ("portal", "datas", "palavra_chave")
        self.tabela = ttk.Treeview(self.tab_resultados, columns=colunas, show="headings", style="Treeview")
        self.tabela.heading("portal", text="Portal de Origem")
        self.tabela.heading("datas", text="Prazo / Submissao")
        self.tabela.heading("palavra_chave", text="Termos Correspondentes")
        self.tabela.column("portal", width=250, anchor="w")
        self.tabela.column("datas", width=200, anchor="center")
        self.tabela.column("palavra_chave", width=350, anchor="w")

        scroll_y = ttk.Scrollbar(self.tab_resultados, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll_y.set)
        self.tabela.grid(row=1, column=0, sticky="nsew")
        scroll_y.grid(row=1, column=1, sticky="ns")
        self.tabela.bind("<<TreeviewSelect>>", self.evento_linha_selecionada)
        self.tabela.bind("<Double-1>", self.abrir_link_edital)

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
