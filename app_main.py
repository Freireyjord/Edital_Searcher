import os
import json
import customtkinter as ctk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
import re
import sys

# Importação da biblioteca para o calendário financeiro
from tkcalendar import Calendar

import config
import app_backend
import processador

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

class AppSincronizador(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sincronizador Unificado de Portais e Editais")
        self.geometry("1150x760") 
        self.minsize(1000, 620)

        # Variáveis globais de controle do funil de filtros
        self.filtro_portais = {}      
        self.filtro_data_min = ""     
        self.filtro_data_max = ""     

        self.grid_rowconfigure(1, weight=1) 
        self.grid_columnconfigure(0, weight=1)

        # ------------------ PAINEL SUPERIOR INDUSTRIAL (CANTOS RETOS) ------------------
        # Definido corner_radius=0 para eliminar o aspecto arredondado
        self.frame_topo = ctk.CTkFrame(self, corner_radius=0, border_width=1, border_color="#3a3d42")
        self.frame_topo.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        
        self.lbl_titulo = ctk.CTkLabel(
            self.frame_topo, text="PESQUISA INTELIGENTE DE EDITAIS", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold")
        )
        self.lbl_titulo.pack(side="left", padx=15, pady=15)

        # Botões com cantos retos (corner_radius=0) e sem emotes
        self.btn_sincronizar = ctk.CTkButton(
            self.frame_topo, text="SINCRONIZAR PORTAIS", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"), command=self.acao_sincronizar
        )
        self.btn_sincronizar.pack(side="right", padx=15, pady=15)

        self.btn_abrir_link = ctk.CTkButton(
            self.frame_topo, text="ABRIR EDITAL", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            fg_color="#2b719e", hover_color="#1f5373", command=self.abrir_link_botao
        )
        self.btn_abrir_link.pack(side="right", padx=10, pady=15)
        
        # COMENTE OU ATIVE A LINHA ABAIXO PARA O EXECUTÁVEL COMPARTILHADO DA SUA EQUIPE
        # self.btn_sincronizar.configure(state="disabled", text="ACESSO CENTRALIZADO")

        # ------------------ PAINEL CENTRAL SIMPLIFICADO ------------------
        self.abas = ctk.CTkTabview(self, corner_radius=0)
        self.abas.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        
        self.tab_resultados = self.abas.add("EDITAIS ENCONTRADOS")
        self.tab_logs = self.abas.add("CONSOLE DE VARREDURA")

        self.tab_resultados.grid_rowconfigure(0, weight=1) 
        self.tab_resultados.grid_rowconfigure(1, weight=4) 
        self.tab_resultados.grid_rowconfigure(2, weight=3) 
        self.tab_resultados.grid_columnconfigure(0, weight=1)
        
        self.configurar_barra_ferramentas_resultados()
        self.configurar_tabela_resultados()
        self.configurar_painel_leitura_embutido()

        # Console de logs com fonte monoespaçada limpa
        self.txt_logs = ctk.CTkTextbox(self.tab_logs, font=("Consolas", 11), corner_radius=0)
        self.txt_logs.pack(fill="both", expand=True, padx=5, pady=5)

        # ------------------ PAINEL INFERIOR ------------------
        self.frame_base = ctk.CTkFrame(self, height=35, corner_radius=0)
        self.frame_base.grid(row=2, column=0, sticky="ew") 
        
        self.lbl_status = ctk.CTkLabel(
            self.frame_base, text="Status: Sistema operacional. Ajuste os parametros no painel de filtros.", 
            font=ctk.CTkFont(family="Arial", size=11)
        )
        self.lbl_status.pack(side="left", padx=15, pady=5)

        self.mapa_checkboxes_vars = {}
        self.atualizar_tabela_local()

        self.bloqueio_diario_ativo = False
        self.after(3000, lambda: threading.Thread(target=self.disparar_esteira_ia_segura, name="esteira_ia_automatica", daemon=True).start())
        self.ativar_atualizador_ciclico_1min()
    def configurar_barra_ferramentas_resultados(self):
        frame_ferramentas = ctk.CTkFrame(self.tab_resultados, height=45, corner_radius=0, fg_color="transparent")
        frame_ferramentas.grid(row=0, column=0, padx=5, pady=(5, 5), sticky="ew")
        
        # Botão de funil sem emoji e com cantos retos
        self.btn_filtro_funil = ctk.CTkButton(
            frame_ferramentas, text="CONFIGURAR PARAMETROS E FILTROS", corner_radius=0,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            fg_color="#34495e", hover_color="#2c3e50", width=250, command=self.abrir_popup_filtros
        )
        self.btn_filtro_funil.pack(side="left", padx=5, pady=5)

        self.lbl_filtros_ativos = ctk.CTkLabel(
            frame_ferramentas, text="Filtros: Parametros padrao ativos.", 
            font=ctk.CTkFont(family="Arial", size=11, slant="italic"), text_color="#95a5a6"
        )
        self.lbl_filtros_ativos.pack(side="left", padx=15, pady=5)

    def configurar_painel_leitura_embutido(self):
        self.frame_detalhes = ctk.CTkFrame(self.tab_resultados, corner_radius=0, border_width=1, border_color="#3a3d42")
        self.frame_detalhes.grid(row=2, column=0, padx=5, pady=(10, 5), sticky="nsew")
        
        lbl_titulo = ctk.CTkLabel(
            self.frame_detalhes, text="RESUMO EXPANDIDO DO EDITAL SELECIONADO", 
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
        """Painel de Filtros com layout lado a lado superior e palavras-chave na metade inferior."""
        popup = ctk.CTkToplevel(self)
        popup.title("Configuracoes de Varredura e Filtros")
        popup.geometry("680x520")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        
        lbl_pop_title = ctk.CTkLabel(popup, text="PARAMETROS DE FILTRO E VARREDURA", font=ctk.CTkFont(family="Arial", size=14, weight="bold"))
        lbl_pop_title.pack(pady=(15, 10))
        
        # --- CONTAINER METADE SUPERIOR (DIVIDIDO EM 2 COLUNAS) ---
        frame_superior = ctk.CTkFrame(popup, fg_color="transparent")
        frame_superior.pack(fill="x", padx=20, pady=5)
        
        # 1. CANTO SUPERIOR ESQUERDO: Filtro de Datas
        frame_datas = ctk.CTkFrame(frame_superior, corner_radius=0, border_width=1, border_color="#3a3d42", width=310, height=210)
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
        
        # 2. CANTO SUPERIOR DIREITO: Filtro de Sites (Portais) com Scrollbar
        frame_matriz = ctk.CTkFrame(frame_superior, corner_radius=0, border_width=1, border_color="#3a3d42", width=320, height=210)
        frame_matriz.pack(side="right", fill="both", expand=True, padx=(5, 0))
        frame_matriz.pack_propagate(False)
        
        # Cabeçalho Fixo
        frame_header = ctk.CTkFrame(frame_matriz, height=28, corner_radius=0, fg_color="#1f6aa5")
        frame_header.pack(fill="x", side="top")
        
        lbl_h2 = ctk.CTkLabel(frame_header, text="SELECIONAR PORTAIS DE ORIGEM", font=ctk.CTkFont(family="Arial", size=10, weight="bold"), text_color="white")
        lbl_h2.pack(anchor="w", padx=10, pady=3)
        
        # Container com Barra de Rolagem Automática (Scrollable)
        scroll_portais = ctk.CTkScrollableFrame(frame_matriz, corner_radius=0, fg_color="transparent")
        scroll_portais.pack(fill="both", expand=True, padx=2, pady=2)

        if getattr(sys, 'frozen', False): diretoria = os.path.join(sys._MEIPASS, "portais")
        else: diretoria = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portais")
        
        arquivos_portais = ["cnpq", "finep", "fundep"]
        if os.path.exists(diretoria):
            arquivos_portais = [f[:-3] for f in os.listdir(diretoria) if f.endswith(".py") and f != "__init__.py"]
        
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

        # --- METADE INFERIOR: Palavras-Chave ---
        frame_keywords = ctk.CTkFrame(popup, corner_radius=0, border_width=1, border_color="#3a3d42")
        frame_keywords.pack(fill="x", padx=20, pady=10)
        
        lbl_kw = ctk.CTkLabel(frame_keywords, text="Termos de Busca (Separe as palavras por virgula):", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
        lbl_kw.pack(anchor="w", padx=15, pady=(10, 5))
        
        txt_pop_palavras = ctk.CTkTextbox(frame_keywords, height=80, corner_radius=0, font=("Arial", 11))
        txt_pop_palavras.pack(fill="x", padx=15, pady=(0, 12))
        txt_pop_palavras.insert("1.0", ", ".join(config.PALAVRAS_CHAVE))

        # --- AÇÕES DO POPUP ---
        def aplicar_filtros_acao():
            texto_p = txt_pop_palavras.get("1.0", "end-1c").strip()
            novas_palavras = [p.strip() for p in texto_p.split(",") if p.strip()]
            if not novas_palavras:
                messagebox.showwarning("Aviso", "Defina ao menos uma palavra-chave para continuar.", parent=popup)
                return

            config.PORTAIS_ATIVOS = {k: v.get() for k, v in dic_vars_locais.items()}
            config.salvar_configuracoes_usuario(config.API_KEY_GEMINI, novas_palavras, config.PORTAIS_ATIVOS)
            
            self.filtro_portais = config.PORTAIS_ATIVOS
            ativos = ["Filtros em execucao:"]
            if self.filtro_data_min or self.filtro_data_max: ativos.append("Intervalo Cronologico")
            if [k for k, v in self.filtro_portais.items() if not v]: ativos.append("Motores Omitidos")
            
            self.lbl_filtros_ativos.configure(
                text=f"{' | '.join(ativos)}" if len(ativos) > 1 else "Filtros: Operando sob configuracao customizada.",
                text_color="#27ae60" if len(ativos) == 1 else "#e74c3c"
            )
            self.atualizar_tabela_local()
            popup.destroy()
            
        def limpar_filtros_acao():
            self.filtro_data_min = ""
            self.filtro_data_max = ""
            self.filtro_portais = {}
            btn_min.configure(text="DATA INICIAL")
            btn_max.configure(text="DATA FINAL")
            self.lbl_filtros_ativos.configure(text="Filtros: Parametros padrao ativos.", text_color="#95a5a6")
            self.atualizar_tabela_local()
            popup.destroy()

        frame_botoes = ctk.CTkFrame(popup, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20, pady=(5, 15))

        btn_limpar = ctk.CTkButton(frame_botoes, text="LIMPAR FILTROS", corner_radius=0, fg_color="#c0392b", hover_color="#962d22", command=limpar_filtros_acao)
        btn_limpar.pack(side="left")
        btn_aplicar = ctk.CTkButton(frame_botoes, text="GRAVAR E APLICAR", corner_radius=0, fg_color="#27ae60", hover_color="#219653", command=aplicar_filtros_acao)
        btn_aplicar.pack(side="right")

    def atualizar_tabela_local(self):
        for item in self.tabela.get_children(): self.tabela.delete(item)
        try:
            resposta = config.supabase.table("editais").select("*").execute()
            editais = resposta.data
            editais_ordenados = sorted(editais, key=lambda x: x.get("prazo_ISO", "9999-12-31 23:59"))
            hoje = datetime.now().date()

            dt_corte_min = datetime.strptime(self.filtro_data_min, "%d/%m/%Y").date() if self.filtro_data_min else None
            dt_corte_max = datetime.strptime(self.filtro_data_max, "%d/%m/%Y").date() if self.filtro_data_max else None

            for edital in editais_ordenados:
                if edital.get("status_ia") == "descartado_vencido": continue

                portal_bruto = edital.get("portal", "N/A")
                modulo_chave = portal_bruto.split(" ")[0].strip().lower() if " " in portal_bruto else portal_bruto.strip().lower()
                
                if self.filtro_portais and not self.filtro_portais.get(modulo_chave, True): continue
                
                prazo_texto = edital.get("datas", "")
                match_datas = re.findall(r"\d{2}/\d{2}/\d{2,4}", prazo_texto)
                
                dt_item = None
                if match_datas:
                    try:
                        data_alvo_str = match_datas[-1].strip()
                        dt_item = datetime.strptime(data_alvo_str, "%d/%m/%y").date() if len(data_alvo_str.split("/")[-1]) == 2 else datetime.strptime(data_alvo_str, "%d/%m/%Y").date()
                    except: pass

                if dt_item and dt_item < hoje: continue
                if dt_item:
                    if dt_corte_min and dt_item < dt_corte_min: continue
                    if dt_corte_max and dt_item > dt_corte_max: continue

                termo = edital.get("palavra_chave", "Nativa")
                self.tabela.insert("", "end", values=(portal_bruto, prazo_texto, termo), tags=(edital.get("url", ""), json.dumps(edital)))
        except Exception as e: print(f"Erro tabela nuvem: {e}")

    def ativar_atualizador_ciclico_1min(self):
        if not self.bloqueio_diario_ativo:
            threading.Thread(target=self.disparar_esteira_ia_segura, name="esteira_ia_automatica", daemon=True).start()
        self.after(60000, self.ativar_atualizador_ciclico_1min)

    def disparar_esteira_ia_segura(self):
        if self.bloqueio_diario_ativo: return
        def logger_provisorio(msg): self.logs_callback(f"[Fila Automatica] {msg}")
        status = processador.consumir_fila_pendente_ia(logger_provisorio, self.forcar_atualizacao_tabela_ui)
        if status == "bloqueio_diario":
            self.bloqueio_diario_ativo = True
            self.lbl_status.configure(text="Status: Fila em background suspensa - Limite de cota atingido.")

    def configurar_tabela_resultados(self):
        colunas = ("portal", "datas", "palavra_chave")
        self.tabela = ttk.Treeview(self.tab_resultados, columns=colunas, show="headings", style="Treeview")
        self.tabela.heading("portal", text="Portal de Origem")
        self.tabela.heading("datas", text="Prazo / Submissao")
        self.tabela.heading("palavra_chave", text="Termo Ativado")
        self.tabela.column("portal", width=250, anchor="w")
        self.tabela.column("datas", width=200, anchor="center")
        self.tabela.column("palavra_chave", width=350, anchor="w")

        scroll_y = ttk.Scrollbar(self.tab_resultados, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll_y.set)
        self.tabela.grid(row=1, column=0, sticky="nsew")
        scroll_y.grid(row=1, column=1, sticky="ns")
        self.tabela.bind("<<TreeviewSelect>>", self.evento_linha_selecionada)
        self.tabela.bind("<Double-1>", self.abrir_link_edital)

    def forcar_atualizacao_tabela_ui(self): self.after(0, self.atualizar_tabela_local)

    def logs_callback(self, mensagem):
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert("end", f"{mensagem}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def evento_linha_selecionada(self, event):
        item_selecionado = self.tabela.selection()
        if not item_selecionado: return
        tags = self.tabela.item(item_selecionado, "tags")
        if len(tags) >= 2:
            try:
                edital = json.loads(tags)
                texto_formatado = (
                    f"PORTAL DE ORIGEM: {edital.get('portal', 'N/A')}\n"
                    f"PRAZO DE SUBMISSAO: {edital.get('datas', 'Nao encontrada')}\n"
                    f"LINHA DE PESQUISA: {edital.get('pesquisa', 'Nao encontrada')}\n"
                    f"ORCAMENTO / SUBVENCAO: {edital.get('subvencao', 'Nao encontrada')}\n"
                    f"--------------------------------------------------------------------------------\n\n"
                    f"RESUMO DO ESCOPO TECNICO COMPLETO:\n{edital.get('escopo', 'Nao encontrado')}"
                )
                self.txt_detalhes_escopo.configure(state="normal")
                self.txt_detalhes_escopo.delete("1.0", "end")
                self.txt_detalhes_escopo.insert("1.0", texto_formatado)
                self.txt_detalhes_escopo.configure(state="disabled")
            except Exception as err: print(f"Erro painel: {err}")

    def acao_sincronizar(self):
        self.btn_sincronizar.configure(state="disabled", text="AGUARDE...")
        self.lbl_status.configure(text="Status: Varrendo portais ativos no Supabase...")
        self.abas.set("CONSOLE DE VARREDURA")
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.configure(state="disabled")
        def exibir_log(msg): self.logs_callback(msg)
        threading.Thread(
            target=lambda: app_backend.rodar_automacao_unificada(
                self.finalizar_sincronizacao, exibir_log, self.forcar_atualizacao_tabela_ui
            ), name="varredura_manual_selenium", daemon=True
        ).start()

    def finalizar_sincronizacao(self): self.after(0, self._concluir_ui)

    def _concluir_ui(self):
        self.btn_sincronizar.configure(state="normal", text="SINCRONIZAR PORTAIS")
        self.lbl_status.configure(text="Status: Dados atualizados e integrados com sucesso na nuvem SQL!")
        self.atualizar_tabela_local()
        self.abas.set("EDITAIS ENCONTRADOS")
        messagebox.showinfo("Concluido", "Varredura finalizada.")

    def abrir_link_edital(self, event):
        item_selecionado = self.tabela.selection()
        if item_selecionado:
            tags = self.tabela.item(item_selecionado, "tags")
            if tags: import webbrowser; webbrowser.open(tags)

    def abrir_link_botao(self):
        item_selecionado = self.tabela.selection()
        if item_selecionado:
            tags = self.tabela.item(item_selecionado, "tags")
            if tags: import webbrowser; webbrowser.open(tags)
        else: messagebox.showwarning("Aviso", "Selecione um edital na tabela antes de prosseguir.")

if __name__ == "__main__":
    app = AppSincronizador()
    app.mainloop()
