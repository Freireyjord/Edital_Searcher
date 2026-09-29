import customtkinter as ctk

class SidebarColunas(ctk.CTkFrame):
    def __init__(self, master, app_callback, **kwargs):
        # Define a largura fixa para a barra lateral direita de controle de colunas
        super().__init__(master, width=220, corner_radius=0, border_width=1, border_color="#3a3d42", **kwargs)
        self.grid_propagate(False)
        
        self.app = app_callback  # Referência da janela principal (app_main.py)

        lbl_title = ctk.CTkLabel(self, text="EXIBIÇÃO DE COLUNAS", font=ctk.CTkFrame(family="Arial", size=13, weight="bold")._font if hasattr(self, '_font') else ctk.CTkFont(family="Arial", size=13, weight="bold"))
        lbl_title.pack(pady=(15, 15))

        # Mapeamento das colunas internas do Treeview e seus nomes amigáveis para a interface do usuário
        self.colunas_info = {
            "titulo": "Título do Edital",
            "portal": "Portal de Origem",
            "datas": "Prazo / Submissão",
            "vigencia_projeto": "Vigência",
            "palavra_chave": "Termos Correspondentes"
        }

        # Cria as caixas de seleção (CheckBox) para cada coluna do sistema
        for id_coluna, nome_amigavel in self.colunas_info.items():
            frame_linha = ctk.CTkFrame(self, height=35, corner_radius=0, fg_color="transparent")
            frame_linha.pack(fill="x", padx=15, pady=2)
            
            # Verifica dinamicamente se a coluna está visível atualmente no estado global do app
            esta_ativa = id_coluna in self.app.colunas_visiveis
            var_chk = ctk.BooleanVar(value=esta_ativa)
            
            chk = ctk.CTkCheckBox(
                frame_linha, text=nome_amigavel, variable=var_chk, corner_radius=0,
                font=ctk.CTkFont(family="Arial", size=11),
                command=lambda cid=id_coluna, v=var_chk: self.alternar_coluna(cid, v.get())
            )
            chk.pack(side="left", padx=5, pady=5)

    def alternar_coluna(self, id_coluna, deve_exibir):
        """Adiciona ou remove a coluna da lista visível e força o redesenho dinâmico da tabela."""
        # Importa o reconstrutor dinâmico apenas no momento da execução para evitar importação circular
        from views import aba_resultados

        if deve_exibir:
            if id_coluna not in self.app.colunas_visiveis:
                # Mantém a ordenação de colunas original e previsível baseada no dicionário original
                ordem_original = list(self.colunas_info.keys())
                self.app.colunas_visiveis.append(id_coluna)
                self.app.colunas_visiveis.sort(key=lambda x: ordem_original.index(x))
        else:
            if id_coluna in self.app.colunas_visiveis:
                # Regra de Segurança: Impede que o usuário oculte TODAS as colunas e quebre a interface gráfica
                if len(self.app.colunas_visiveis) <= 1:
                    return
                self.app.colunas_visiveis.remove(id_coluna)
        
        # Invoca o motor de visualização para redesenhar as colunas e reinserir as linhas limpas
        aba_resultados.reconfigurar_colunas_tabela(self.app)
