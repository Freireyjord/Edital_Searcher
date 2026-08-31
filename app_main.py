import os
import json
import customtkinter as ctk
from tkinter import ttk, messagebox
import threading

# Importação dos módulos locais corrigidos
import config
import app_backend

# Configuração estética do CustomTkinter
ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

class AppSincronizador(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações de Janela
        self.title("Sincronizador Unificado de Portais e Editais")
        self.geometry("1100x750") 
        self.minsize(950, 600)

        # Layout Principal Simplificado (Aba agora expande totalmente)
        self.grid_rowconfigure(1, weight=1) # Apenas as abas ocupam o centro com peso máximo
        self.grid_columnconfigure(0, weight=1)

        # ------------------ PAINEL SUPERIOR (Controles) ------------------
        self.frame_topo = ctk.CTkFrame(self, corner_radius=10)
        self.frame_topo.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        
        self.lbl_titulo = ctk.CTkLabel(
            self.frame_topo, 
            text="Triagem Inteligente de Editais (CNPq, Fundep, Finep)", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_titulo.pack(side="left", padx=15, pady=15)

        self.btn_abrir_link = ctk.CTkButton(
            self.frame_topo,
            text="🌐 Abrir Link do Edital",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b719e",  
            hover_color="#1f5373",
            command=self.abrir_link_botao
        )
        self.btn_abrir_link.pack(side="right", padx=10, pady=15)

        self.btn_sincronizar = ctk.CTkButton(
            self.frame_topo,
            text="🔄 Iniciar Sincronização",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.acao_sincronizar
        )
        self.btn_sincronizar.pack(side="right", padx=15, pady=15)

        # ------------------ PAINEL CENTRAL (Abas) ------------------
        self.abas = ctk.CTkTabview(self)
        self.abas.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        
        self.tab_resultados = self.abas.add("📊 Editais Encontrados")
        self.tab_logs = self.abas.add("📋 Console de Varredura")
        self.tab_config = self.abas.add("⚙️ Configurações do Sistema")

        # Configuração Interna da Aba de Resultados (Dividida em 2 Linhas: Tabela e Resumo)
        self.tab_resultados.grid_rowconfigure(0, weight=3) # Linha 0: Tabela (maior)
        self.tab_resultados.grid_rowconfigure(1, weight=2) # Linha 1: Painel de Leitura (menor)
        self.tab_resultados.grid_columnconfigure(0, weight=1)
        
        # Monta a tabela e o painel de leitura embutidos na aba
        self.configurar_tabela_resultados()
        self.configurar_painel_leitura_embutido()

        # Configuração da Aba de Logs
        self.txt_logs = ctk.CTkTextbox(self.tab_logs, font=("Consolas", 12))
        self.txt_logs.pack(fill="both", expand=True, padx=5, pady=5)

        # Configuração da Aba de Configurações Visuais
        self.configurar_aba_configuracoes()

        # ------------------ PAINEL INFERIOR (Status) ------------------
        self.frame_base = ctk.CTkFrame(self, height=35, corner_radius=0)
        self.frame_base.grid(row=2, column=0, sticky="ew") # Agora fica na linha 2 do app geral
        
        self.lbl_status = ctk.CTkLabel(
            self.frame_base, 
            text="Sistema Pronto. Clique em sincronizar para iniciar a busca.", 
            font=ctk.CTkFont(size=12)
        )
        self.lbl_status.pack(side="left", padx=15, pady=5)

        # Inicialização do JSON
        import config
        caminho_json = config.CAMINHO_JSON_HISTORICO
        if not os.path.exists(caminho_json):
            try:
                with open(caminho_json, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Erro inicializacao JSON: {e}")

        self.atualizar_tabela_local()

    def configurar_painel_leitura_embutido(self):
        """Cria a área de leitura detalhada acoplada na parte inferior da aba de Resultados."""
        # Colocamos o frame apontando para self.tab_resultados e na linha 1 (row=1)
        self.frame_detalhes = ctk.CTkFrame(self.tab_resultados, corner_radius=10)
        self.frame_detalhes.grid(row=1, column=0, padx=5, pady=(10, 5), sticky="nsew")
        
        self.lbl_detalhes_titulo = ctk.CTkLabel(
            self.frame_detalhes, 
            text="📖 Resumo Ampliado do Edital Selecionado (Clique em um item da tabela acima para ler)", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#1f6aa5"
        )
        self.lbl_detalhes_titulo.pack(anchor="w", padx=15, pady=8)

        # Caixa de texto rica com quebra de linha por palavra automática
        self.txt_detalhes_escopo = ctk.CTkTextbox(
            self.frame_detalhes, 
            font=("Arial", 13), 
            wrap="word", 
            border_width=1,
            border_color="#3a3d42"
        )
        self.txt_detalhes_escopo.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.txt_detalhes_escopo.insert("1.0", "Nenhum edital selecionado no momento.")
        self.txt_detalhes_escopo.configure(state="disabled")


    def configurar_aba_configuracoes(self):
        """Constrói os formulários de edição com rolagem para evitar que componentes sumam."""
        self.tab_config.grid_columnconfigure(0, weight=1)
        self.tab_config.grid_rowconfigure(0, weight=1)
        
        # CONTAINER PRINCIPAL COM ROLAGEM AUTOMÁTICA (CTkScrollableFrame)
        canvas_config = ctk.CTkScrollableFrame(self.tab_config, corner_radius=0, fg_color="transparent")
        canvas_config.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        canvas_config.grid_columnconfigure(0, weight=1)
        
        # 1. Container da API Key
        frame_api = ctk.CTkFrame(canvas_config, corner_radius=8)
        # CORREÇÃO: Removido o fill="x" do grid. O sticky="ew" cuida de esticar horizontalmente.
        frame_api.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        
        lbl_api = ctk.CTkLabel(frame_api, text="Chave de API do Gemini (Google AI Studio):", font=ctk.CTkFont(weight="bold"))
        lbl_api.pack(anchor="w", padx=15, pady=(10, 2))
        
        self.txt_api_key = ctk.CTkEntry(frame_api, placeholder_text="Cole sua AI_KEY aqui...", width=600, show="*")
        self.txt_api_key.pack(anchor="w", padx=15, pady=(0, 15))
        self.txt_api_key.insert(0, config.API_KEY_GEMINI)
        
        # 2. Container das Palavras-Chave
        frame_palavras = ctk.CTkFrame(canvas_config, corner_radius=8)
        # CORREÇÃO: Removido o fill="x" do grid aqui também.
        frame_palavras.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        
        lbl_palavras = ctk.CTkLabel(
            frame_palavras, 
            text="Termos de Busca / Palavras-Chave (Separe as palavras por VÍRGULA):", 
            font=ctk.CTkFont(weight="bold")
        )
        lbl_palavras.pack(anchor="w", padx=15, pady=(10, 2))
        
        # Altura fixa definida para a caixa de texto para não quebrar o layout
        self.txt_palavras = ctk.CTkTextbox(frame_palavras, font=("Arial", 12), height=150)
        self.txt_palavras.pack(fill="x", padx=15, pady=(0, 15)) # Aqui o pack aceita o fill normalmente!
        
        texto_inicial_palavras = ", ".join(config.PALAVRAS_CHAVE)
        self.txt_palavras.insert("1.0", texto_inicial_palavras)
        
        # 3. Botão de Ação de Gravação
        self.btn_salvar_config = ctk.CTkButton(
            canvas_config,
            text="💾 Salvar Configurações",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144d78",
            height=40,
            command=self.acao_salvar_configuracoes
        )
        self.btn_salvar_config.grid(row=2, column=0, pady=20)


    def acao_salvar_configuracoes(self):
        """Captura os valores da tela, atualiza a memória ativa do config e grava no JSON."""
        nova_key = self.txt_api_key.get().strip()
        texto_palavras = self.txt_palavras.get("1.0", "end").strip()
        
        # Quebra o texto da caixa pelas vírgulas para remontar a lista limpa
        novas_palavras = [p.strip() for p in texto_palavras.split(",") if p.strip()]
        
        if not nova_key:
            messagebox.showwarning("Aviso", "A chave de API do Gemini não pode ficar em branco!")
            return
            
        if not novas_palavras:
            messagebox.showwarning("Aviso", "Você precisa digitar ao menos uma palavra-chave para a varredura!")
            return
            
        # Executa a gravação física no config.py
        sucesso = config.salvar_configuracoes_usuario(nova_key, novas_palavras)
        
        if sucesso:
            messagebox.showinfo("Sucesso", "Configurações gravadas com sucesso! Elas serão aplicadas na próxima sincronização.")
        else:
            messagebox.showerror("Erro I/O", "O Windows impediu a gravação do arquivo de configurações.")

    def configurar_tabela_resultados(self):
        """Monta o Treeview para exibição simplificada dos editais."""
        # Definimos apenas as 3 colunas essenciais
        colunas = ("portal", "datas", "palavra_chave")
        
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("Treeview", background="#2a2d32", fieldbackground="#2a2d32", foreground="white", rowheight=25)
        estilo.map("Treeview", background=[("selected", "#1f538d")])
        estilo.configure("Treeview.Heading", background="#1f6aa5", foreground="white", font=('Arial', 10, 'bold'))

        self.tabela = ttk.Treeview(self.tab_resultados, columns=colunas, show="headings", style="Treeview")
        
        # Cabeçalhos simplificados
        self.tabela.heading("portal", text="Portal")
        self.tabela.heading("datas", text="Prazo / Submissão")
        self.tabela.heading("palavra_chave", text="Palavra-Chave Gatilho")

        # Ajuste de larguras para preencher bem o espaço horizontal
        self.tabela.column("portal", width=250, anchor="w")
        self.tabela.column("datas", width=200, anchor="center")
        self.tabela.column("palavra_chave", width=350, anchor="w")

        scroll_y = ttk.Scrollbar(self.tab_resultados, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll_y.set)
        
        self.tabela.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        
        # Eventos vinculados
        self.tabela.bind("<<TreeviewSelect>>", self.evento_linha_selecionada)
        self.tabela.bind("<Double-1>", self.abrir_link_edital)

    def evento_linha_selecionada(self, event):
        """Gatilho acionado ao selecionar uma linha. Lê os metadados ocultos da tag."""
        item_selecionado = self.tabela.selection()
        if not item_selecionado:
            return

        # Recupera as tags guardadas na linha clicada
        tags = self.tabela.item(item_selecionado, "tags")
        if len(tags) >= 2:
            try:
                # Reconverte a string oculta de volta para um dicionário Python
                edital = json.loads(tags[1])
                
                portal = edital.get("portal", edital.get("Portal", "N/A"))
                prazo = edital.get("datas", edital.get("Prazo / Submissão", "Não encontrada"))
                linha_pesquisa = edital.get("pesquisa", edital.get("Linha de Pesquisa", "Não encontrada"))
                subvencao = edital.get("subvencao", edital.get("Orçamento / Subvenção", "Não encontrada"))
                resumo_completo = edital.get("escopo", edital.get("Resumo do Escopo Técnico", edital.get("Resumo do Escopo", "Não encontrado")))
                
                # Monta a ficha de leitura rica e organizada na área de texto inferior
                texto_formatado = (
                    f"🏛️ PORTAL DE ORIGEM: {portal}\n"
                    f"📅 PRAZO DE SUBMISSÃO: {prazo}\n"
                    f"🧬 LINHA DE PESQUISA: {linha_pesquisa}\n"
                    f"💰 ORÇAMENTO / SUBVENÇÃO: {subvencao}\n"
                    f"-------------------------------------------------------------------------------------------------------\n\n"
                    f"📝 RESUMO DO ESCOPO TÉCNICO COMPLETO:\n{resumo_completo}"
                )
                
                self.txt_detalhes_escopo.configure(state="normal")
                self.txt_detalhes_escopo.delete("1.0", "end")
                self.txt_detalhes_escopo.insert("1.0", texto_formatado)
                self.txt_detalhes_escopo.configure(state="disabled")
                
            except Exception as err:
                print(f"Erro ao decodificar dados do painel: {err}")


    def logs_callback(self, mensagem):
        """Injeta mensagens vindas do backend em tempo real no console visual."""
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert("end", f"{mensagem}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def acao_sincronizar(self):
        """Aciona os disparadores assíncronos protegendo a UI de travamentos."""
        self.btn_sincronizar.configure(state="disabled", text="⏳ Buscando...")
        self.lbl_status.configure(text="⏳ Buscando editais ativamente nos portais públicos...")
        
        self.abas.set("📋 Console de Varredura")
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.configure(state="disabled")
        
        def exibir_log(msg):
            print(msg)
            self.logs_callback(msg)

        threading.Thread(
            target=lambda: app_backend.rodar_automacao_unificada(self.finalizar_sincronizacao, exibir_log),
            daemon=True
        ).start()

    def finalizar_sincronizacao(self):
        """Devolve a conclusão do fluxo para a thread principal da UI."""
        self.after(0, self._concluir_ui)

    def _concluir_ui(self):
        self.btn_sincronizar.configure(state="normal", text="🔄 Iniciar Sincronização")
        self.lbl_status.configure(text="✅ Sincronização finalizada e dados atualizados!")
        self.atualizar_tabela_local()
        self.abas.set("📊 Editais Encontrados")
        messagebox.showinfo("Varredura Completa", "A busca terminou! Os novos editais compatíveis já foram processados.")

    def atualizar_tabela_local(self):
        """Lê o arquivo JSON unificado estruturado e renderiza na Grid simplificada."""
        for item in self.tabela.get_children():
            self.tabela.delete(item)

        caminho_json = config.CAMINHO_JSON_HISTORICO
        if not os.path.exists(caminho_json):
            return

        try:
            with open(caminho_json, "r", encoding="utf-8") as f:
                editais = json.load(f)
                
            editais_ordenados = sorted(editais, key=lambda x: x.get("prazo_ISO", "9999-12-31 23:59"))

            for edital in editais_ordenados:
                # Recupera o termo gatilho que salvamos no JSON provisório ou assume padrão
                termo = edital.get("palavra_chave", "Nativa do Portal")
                if "texto_extracao" in edital and not termo:
                    termo = "Aguardando Varredura..."

                # Insere apenas os 3 valores visíveis
                self.tabela.insert("", "end", values=(
                    edital.get("portal", edital.get("Portal", "N/A")),
                    edital.get("datas", edital.get("Prazo / Submissão", "Não encontrada")),
                    termo
                ), tags=(edital.get("url", ""), json.dumps(edital))) # Guardamos o JSON completo stringificado na tag[1]
                
        except Exception as e:
            self.logs_callback(f"[X] Erro ao carregar histórico na tabela visual: {e}")

    def abrir_link_edital(self, event):
        """Abre a URL pelo duplo clique."""
        item_selecionado = self.tabela.selection()
        if item_selecionado:
            tags = self.tabela.item(item_selecionado, "tags")
            if tags:
                import webbrowser
                webbrowser.open(tags[0])

    def abrir_link_botao(self):
        """Captura la línea seleccionada y abre el link."""
        item_selecionado = self.tabela.selection()
        if item_selecionado:
            tags = self.tabela.item(item_selecionado, "tags")
            if tags:
                import webbrowser
                webbrowser.open(tags[0])
        else:
            messagebox.showwarning("Aviso", "Por favor, clique em um edital na tabela primeiro para abrir o link!")

if __name__ == "__main__":
    app = AppSincronizador()
    app.mainloop()
