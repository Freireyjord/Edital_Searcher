import smtplib
import threading
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from tkinter import messagebox

import customtkinter as ctk

# 🔍 AJUSTE DE IMPORTAÇÃO: Busca as configurações e o motor de e-mail da pasta 'core'
from core import config
from core import email_engine

# Variáveis globais auxiliares de controle visual em memória
_lista_tags_memoria = []
_scroll_container = None
_entry_tag_widget = None
_btn_enviar_manual = None

def construir_interface_aba_relatorio(tab_alvo, app_instancia):
    global _lista_tags_memoria, _scroll_container, _entry_tag_widget, _btn_enviar_manual
    
    # 1. Carrega primeiro as configurações locais salvas no config_app.json da máquina
    config.carregar_configuracoes_salvas()
    email_local = getattr(config, "EMAIL_RELATORIO", "").strip()
    
    # Valores padrão iniciais caso não encontre nada na nuvem
    email_banco = email_local
    chk_banco = getattr(config, "FILTRAR_RELATORIO_POR_TAGS", False)
    _lista_tags_memoria = list(getattr(config, "TAGS_RELATORIO", []))
    
    # 🔥 CARREGAMENTO VIA NUVEM INTELIGENTE (MULTI-USUÁRIO): 
    if email_local:
        try:
            resposta_nuvem = config.supabase.table("configuracoes_relatorio").select("*").eq("email_destino", email_local.lower()).execute()
            if resposta_nuvem.data and len(resposta_nuvem.data) > 0:
                dados_nuvem = resposta_nuvem.data[0]
                email_banco = dados_nuvem.get("email_destino", email_local)
                chk_banco = dados_nuvem.get("filtrar_por_tags", chk_banco)
                tags_brutas = dados_nuvem.get("tags_exclusivas", "")
                _lista_tags_memoria = [t.strip() for t in tags_brutas.split(",") if t.strip()]
        except Exception as e_nuvem:
            print(f"[Aviso] Não foi possível sincronizar dados da nuvem na inicialização: {e_nuvem}")

    # Configura a grade da aba principal para expandir horizontalmente
    tab_alvo.grid_columnconfigure(0, weight=1)
    tab_alvo.grid_rowconfigure(0, weight=1)

    frame_central = ctk.CTkFrame(tab_alvo, border_width=1, border_color="#3a3d42")
    frame_central.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
    
    frame_central.grid_columnconfigure(0, weight=1, minsize=450)
    frame_central.grid_columnconfigure(1, weight=1, minsize=450)
    frame_central.grid_rowconfigure(0, weight=1)

    # ==============================================================================
    # 🏠 PAINEL DA ESQUERDA: CONFIGURAÇÕES E DISPAROS
    # ==============================================================================
    panel_esquerdo = ctk.CTkFrame(frame_central, fg_color="transparent")
    panel_esquerdo.grid(row=0, column=0, padx=20, pady=15, sticky="nsew")

    lbl_secao_title = ctk.CTkLabel(panel_esquerdo, text="ASSINATURA DE MONITORAMENTO SEMANAL", font=ctk.CTkFont(family="Arial", size=14, weight="bold"), text_color="#1f6aa5")
    lbl_secao_title.pack(anchor="w", pady=(5, 5))

    lbl_desc = ctk.CTkLabel(
        panel_esquerdo, 
        text="Cadastre o seu e-mail institucional. O sistema coletará os editais\npublicados nos últimos 7 dias direto do banco para disparar o resumo.",
        font=ctk.CTkFont(family="Arial", size=11), text_color="#a5a5a5", justify="left"
    )
    lbl_desc.pack(anchor="w", pady=(0, 15))

    lbl_mail = ctk.CTkLabel(panel_esquerdo, text="Seu endereço de E-mail Destinatário:", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
    lbl_mail.pack(anchor="w", pady=(5, 2))

    entry_email = ctk.CTkEntry(panel_esquerdo, width=420, placeholder_text="seu_email@fieb.org.br", corner_radius=0, font=("Arial", 11))
    entry_email.pack(anchor="w", pady=(0, 10))
    entry_email.insert(0, email_banco)

    var_filtrar_tags = ctk.BooleanVar(value=chk_banco)
    chk_filtrar_tags = ctk.CTkCheckBox(panel_esquerdo, text="Filtrar e-mail usando as tags exclusivas do relatório\n(Caso desmarcado, enviará todas as novas capturas)", variable=var_filtrar_tags, corner_radius=0, font=ctk.CTkFont(family="Arial", size=11))
    chk_filtrar_tags.pack(anchor="w", pady=(10, 15))

    ctk.CTkFrame(panel_esquerdo, height=2, fg_color="#3a3d42", width=420).pack(anchor="w", pady=10)

    btn_salvar = ctk.CTkButton(panel_esquerdo, text="SALVAR PREFERÊNCIAS", corner_radius=0, font=ctk.CTkFont(family="Arial", size=11, weight="bold"), fg_color="#27ae60", hover_color="#219653", width=420, height=32, command=lambda: _acao_salvar_config_relatorio(entry_email, var_filtrar_tags, app_instancia))
    btn_salvar.pack(anchor="w", pady=4)

    _btn_enviar_manual = ctk.CTkButton(panel_esquerdo, text="ATIVAÇÃO DO E-MAIL / ENVIO IMEDIATO DE RELATÓRIO", corner_radius=0, font=ctk.CTkFont(family="Arial", size=11, weight="bold"), fg_color="#1f6aa5", hover_color="#144e78", width=420, height=32, command=lambda: _acao_enviar_relatorio_manual_thread(app_instancia, entry_email))
    _btn_enviar_manual.pack(anchor="w", pady=4)

    btn_cancelar_assinatura = ctk.CTkButton(
        panel_esquerdo, 
        text="CANCELAR MINHA ASSINATURA", 
        corner_radius=0, 
        font=ctk.CTkFont(family="Arial", size=11, weight="bold"), 
        fg_color="#c0392b", 
        hover_color="#962d22", 
        width=420, 
        height=32, 
        command=lambda: _acao_solicitar_cancelamento(entry_email, app_instancia)
    )
    btn_cancelar_assinatura.pack(anchor="w", pady=(15, 4))
    # ==============================================================================
    # 🏷️ PAINEL DA DIREITA: GERENCIAMENTO DE TAGS EXCLUSIVAS
    # ==============================================================================
    panel_direito = ctk.CTkFrame(frame_central, fg_color="transparent")
    panel_direito.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")
    panel_direito.grid_rowconfigure(2, weight=1) 
    panel_direito.grid_columnconfigure(0, weight=1)

    lbl_tags_rel = ctk.CTkLabel(panel_direito, text="Tags de Filtragem Exclusivas do E-mail:", font=ctk.CTkFont(family="Arial", size=12, weight="bold"), text_color="#1f6aa5")
    lbl_tags_rel.grid(row=0, column=0, sticky="w", pady=(5, 2))

    _entry_tag_widget = ctk.CTkEntry(panel_direito, placeholder_text="Pressione Enter ou Vírgula para adicionar uma palavra...", corner_radius=0, font=("Arial", 11))
    _entry_tag_widget.grid(row=1, column=0, sticky="ew", pady=(0, 5))

    _scroll_container = ctk.CTkScrollableFrame(panel_direito, corner_radius=0, fg_color="#1e1e1e")
    _scroll_container.grid(row=2, column=0, sticky="nsew", pady=(0, 5))

    _entry_tag_widget.bind("<Return>", lambda e: _adicionar_tag_relatorio_evt())
    _entry_tag_widget.bind(",", lambda e: _adicionar_tag_relatorio_evt())

    _renderizar_tags_relatorio_tela()

def _renderizar_tags_relatorio_tela():
    global _lista_tags_memoria, _scroll_container
    for widget in _scroll_container.winfo_children():
        widget.destroy()

    LARGURA_MAXIMA = 390
    largura_acumulada = 0
    linha_atual = ctk.CTkFrame(_scroll_container, fg_color="transparent")
    linha_atual.pack(anchor="w", fill="x", pady=1)

    for tag_texto in _lista_tags_memoria:
        largura_tag = (len(tag_texto) * 8) + 42
        if largura_acumulada + largura_tag > LARGURA_MAXIMA and largura_acumulada > 0:
            linha_atual = ctk.CTkFrame(_scroll_container, fg_color="transparent")
            linha_atual.pack(anchor="w", fill="x", pady=1)
            largura_acumulada = 0

        tag_box = ctk.CTkFrame(linha_atual, fg_color="#2980b9", corner_radius=12)
        tag_box.pack(side="left", padx=2, pady=1)

        lbl_t = ctk.CTkLabel(tag_box, text=tag_texto, font=ctk.CTkFont(family="Arial", size=9, weight="bold"), text_color="white")
        lbl_t.pack(side="left", padx=(6, 3), pady=1)

        def remover_tag_rel(t=tag_texto):
            if t in _lista_tags_memoria:
                _lista_tags_memoria.remove(t)
                _renderizar_tags_relatorio_tela()

        btn_del = ctk.CTkButton(tag_box, text="✕", width=14, height=14, corner_radius=7, fg_color="transparent", hover_color="#c0392b", font=("Arial", 8, "bold"), command=remover_tag_rel)
        btn_del.pack(side="right", padx=(0, 3), pady=1)
        largura_acumulada += largura_tag

def _adicionar_tag_relatorio_evt():
    global _lista_tags_memoria, _entry_tag_widget
    texto = _entry_tag_widget.get().strip().replace(",", "")
    if texto:
        if texto not in _lista_tags_memoria:
            _lista_tags_memoria.append(texto)
            _renderizar_tags_relatorio_tela()
        _entry_tag_widget.delete(0, "end")
    return "break"
def _acao_salvar_config_relatorio(entry_email, var_filtrar_tags, app_instancia):
    global _lista_tags_memoria
    _adicionar_tag_relatorio_evt()
    email_digitado = entry_email.get().strip()
    deve_filtrar_tags = var_filtrar_tags.get()

    if not email_digitado or "@" not in email_digitado or "." not in email_digitado:
        messagebox.showerror("E-mail Inválido", "Por favor, insira um endereço de e-mail válido.")
        return

    tags_formatadas_banco = ",".join(_lista_tags_memoria)

    try:
        payload = {
            "email_destino": email_digitado,
            "filtrar_por_tags": deve_filtrar_tags,
            "tags_exclusivas": tags_formatadas_banco
        }
        
        email_pesquisa = email_digitado.lower().strip()
        checar_registro = config.supabase.table("configuracoes_relatorio").select("id").eq("email_destino", email_pesquisa).execute()
        
        if checar_registro.data and len(checar_registro.data) > 0:
            id_existente = checar_registro.data[0]["id"]
            config.supabase.table("configuracoes_relatorio").update(payload).eq("id", id_existente).execute()
            app_instancia.lbl_status.configure(text=f"Status: Filtros updated para {email_digitado}.")
        else:
            config.supabase.table("configuracoes_relatorio").insert(payload).execute()
            app_instancia.lbl_status.configure(text=f"Status: Nova assinatura criada para {email_digitado}.")

        config.salvar_configuracoes_usuario(
            lista_palavras=config.PALAVRAS_CHAVE, 
            dicionario_portais=config.PORTAIS_ATIVOS, 
            email_destino=email_digitado, 
            filtrar_tags=deve_filtrar_tags,
            lista_tags_relatorio=_lista_tags_memoria
        )

        messagebox.showinfo("Sucesso", "Preferências do relatório sincronizadas na nuvem e salvas localmente!")

    except Exception as e:
        erro_msg = str(e).lower()
        if "23505" in erro_msg or "unique" in erro_msg or "duplicate" in erro_msg:
            messagebox.showwarning(
                "E-mail Duplicado", 
                f"O endereço '{email_digitado}' já está cadastrado no monitoramento.\n\n"
                "Para alterar as suas tags, modifique os campos e clique em 'SALVAR PREFERÊNCIAS' novamente."
            )
        else:
            messagebox.showerror("Erro de Sincronização", f"Não foi possível conectar ao servidor do Supabase:\n{e}")

def _acao_enviar_relatorio_manual_thread(app_instancia, entry_email_widget):
    global _btn_enviar_manual
    _btn_enviar_manual.configure(state="disabled", text="ENVIANDO RELATÓRIO...")
    app_instancia.lbl_status.configure(text="Status: Compilando editais dos últimos 7 dias...")
    
    thread_envio = threading.Thread(target=lambda: _executar_envio_manual_background(app_instancia, entry_email_widget))
    thread_envio.daemon = True
    thread_envio.start()

def _executar_envio_manual_background(app_instancia, entry_email_widget):
    global _btn_enviar_manual
    try:
        email_atual = entry_email_widget.get().strip()

        if not email_atual or "@" not in email_atual:
            messagebox.showerror("E-mail Inválido", "Por favor, digite um e-mail válido no campo de texto antes de solicitar o envio.")
            return

        sucesso = email_engine.compilar_e_enviar_relatorio_semanal(
            email_alvo=email_atual, 
            log_func=lambda msg: app_instancia.lbl_status.configure(text=f"Status: {msg}")
        )
        
        if sucesso:
            messagebox.showinfo("Sucesso", f"O relatório semanal foi enviado com sucesso para {email_atual}!")
        else:
            messagebox.showwarning("Aviso", "O relatório não pôde ser enviado. Verifique se existem editais ativos nos últimos 7 dias com as tags selecionadas.")
            
    except Exception as err:
        messagebox.showerror("Erro de Disparo", f"Falha interna ao tentar acionar o motor de e-mails: {err}")
    finally:
        _btn_enviar_manual.configure(state="normal", text="ATIVAÇÃO DO E-MAIL / ENVIO IMEDIATO DE RELATÓRIO")

def _acao_solicitar_cancelamento(entry_email, app_instancia):
    email_digitado = entry_email.get().strip().lower()

    if not email_digitado or "@" not in email_digitado or "." not in email_digitado:
        messagebox.showerror("E-mail Inválido", "Por favor, digite o seu e-mail cadastrado para poder cancelar.")
        return

    try:
        checar = config.supabase.table("configuracoes_relatorio").select("id").eq("email_destino", email_digitado).execute()
        if not checar.data:
            messagebox.showwarning("Não Localizado", f"O e-mail '{email_digitado}' não possui uma assinatura ativa no sistema.")
            return

        token_gerado = str(random.randint(100000, 999999))
        config.supabase.table("configuracoes_relatorio").update({"token_cancelamento": token_gerado}).eq("email_destino", email_digitado).execute()

        msg_corpo = f"""
        <html><body>
            <h2 style='color: #c0392b;'>SOLICITAÇÃO DE CANCELAMENTO DE RELATÓRIO</h2>
            <p>Você solicitou o cancelamento da sua assinatura de monitoramento semanal de editais.</p>
            <p>Utilize o código de segurança abaixo no aplicativo para confirmar a exclusão:</p>
            <div style='font-size: 24px; font-weight: bold; background: #f4f4f4; padding: 10px; width: 150px; text-align: center; border: 1px solid #ccc; letter-spacing: 2px;'>
                {token_gerado}
            </div>
            <p style='color: #777; font-size: 11px; margin-top: 20px;'>Se você não solicitou este cancelamento, ignore este e-mail de segurança.</p>
        </body></html>
        """

        msg = MIMEMultipart()
        msg['From'] = email_engine.SMTP_REMETENTE
        msg['To'] = email_digitado
        msg['Subject'] = "🔒 Código de Segurança - Cancelamento de Relatório PCE"
        msg.attach(MIMEText(msg_corpo, 'html', 'utf-8'))
        
        servidor = smtplib.SMTP(email_engine.SMTP_SERVIDOR, email_engine.SMTP_PORTA, timeout=30)
        servidor.sendmail(email_engine.SMTP_REMETENTE, email_digitado, msg.as_string())
        servidor.quit()

        app_instancia.lbl_status.configure(text=f"Status: Código enviado para {email_digitado}.")
        _abrir_janela_validacao_token(email_digitado, app_instancia)

    except Exception as e:
        messagebox.showerror("Erro de Comunicação", f"Falha ao processar cancelamento: {e}")

def _abrir_janela_validacao_token(email_usuario, app_instancia):
    top_token = ctk.CTkToplevel(app_instancia)
    top_token.title("Confirmar Cancelamento")
    top_token.geometry("340x200")
    top_token.resizable(False, False)
    top_token.transient(app_instancia)
    top_token.grab_set()

    lbl_info = ctk.CTkLabel(top_token, text=f"Insira o código de 6 dígitos enviado para:\n{email_usuario}", font=("Arial", 11), justify="center")
    lbl_info.pack(pady=(20, 10))

    entry_token = ctk.CTkEntry(top_token, width=160, font=("Arial", 16, "bold"), justify="center", placeholder_text="000000")
    entry_token.pack(pady=5)

    def processar_confirmacao():
        token_digitado = entry_token.get().strip()
        try:
            resposta = config.supabase.table("configuracoes_relatorio").select("token_cancelamento").eq("email_destino", email_usuario).execute()
            if r := resposta.data:
                token_banco = r[0].get("token_cancelamento")
                if token_digitado == token_banco and token_banco is not None:
                    config.supabase.table("configuracoes_relatorio").delete().eq("email_destino", email_usuario).execute()
                    app_instancia.lbl_status.configure(text="Status: Assinatura cancelada com sucesso.")
                    messagebox.showinfo("Cancelado", "Sua assinatura foi removida da base de dados com sucesso!")
                    top_token.destroy()
                else:
                    messagebox.showerror("Erro de Validação", "O código inserido está incorreto. Tente novamente.")
            else:
                messagebox.showerror("Erro", "Erro ao recuperar dados da sessão de cancelamento.")
                top_token.destroy()
        except Exception as err:
            messagebox.showerror("Erro no Banco", f"Falha ao validar: {err}")

    btn_validar = ctk.CTkButton(top_token, text="CONFIRMAR EXCLUSÃO", fg_color="#c0392b", hover_color="#962d22", font=ctk.CTkFont(family="Arial", size=11, weight="bold"), command=processar_confirmacao)
    btn_validar.pack(pady=15)
