import smtplib, threading

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from tkinter import messagebox

import customtkinter as ctk

import config # Conecta ao config.py local do Grupo App

# ==============================================================================
# 🔐 CONFIGURAÇÕES DE RELAY CORPORATIVO INTERNO - FIEB
# ==============================================================================
SMTP_SERVIDOR = "fieb-org-br.mail.protection.outlook.com"
SMTP_PORTA = 25
SMTP_REMETENTE = "joao.freire@fbter.org.br"
SMTP_SENHA = ""

# Variáveis globais auxiliares de controle visual em memória
_lista_tags_memoria = []
_scroll_container = None
_entry_tag_widget = None
_btn_enviar_manual = None

def normalizar_texto_report(texto):
    import unicodedata
    if not texto: return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def construir_interface_aba_relatorio(tab_alvo, app_instancia):
    global _lista_tags_memoria, _scroll_container, _entry_tag_widget, _btn_enviar_manual
    
    # 🔥 CARREGAMENTO VIA NUVEM: Puxa o estado atual salvo no banco de dados
    try:
        resposta_nuvem = config.supabase.table("configuracoes_relatorio").select("*").eq("id", 1).execute()
        if resposta_nuvem.data:
            dados_nuvem = resposta_nuvem.data[0]
            email_banco = dados_nuvem.get("email_destino", "")
            chk_banco = dados_nuvem.get("filtrar_por_tags", False)
            tags_brutas = dados_nuvem.get("tags_exclusivas", "")
            _lista_tags_memoria = [t.strip() for t in tags_brutas.split(",") if t.strip()]
        else:
            email_banco = ""
            chk_banco = False
            _lista_tags_memoria = []
    except:
        email_banco = ""
        chk_banco = False
        _lista_tags_memoria = []
    
    config.carregar_configuracoes_salvas()
    _lista_tags_memoria = list(getattr(config, "TAGS_RELATORIO", []))

    # Configura a grade da aba principal para expandir horizontalmente
    tab_alvo.grid_columnconfigure(0, weight=1)
    tab_alvo.grid_rowconfigure(0, weight=1)

    frame_central = ctk.CTkFrame(tab_alvo, border_width=1, border_color="#3a3d42")
    frame_central.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
    
    # Divide o frame central em duas colunas iguais (Esquerda: Configs | Direita: Tags)
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
        text="Cadastre o seu e-mail institucional. O sistema de segundo plano coletará os\neditais publicados nos últimos 7 dias direto do banco para disparar o resumo.",
        font=ctk.CTkFont(family="Arial", size=11), text_color="#a5a5a5", justify="left"
    )
    lbl_desc.pack(anchor="w", pady=(0, 15))

    lbl_mail = ctk.CTkLabel(panel_esquerdo, text="Seu endereço de E-mail Destinatário:", font=ctk.CTkFont(family="Arial", size=11, weight="bold"))
    lbl_mail.pack(anchor="w", pady=(5, 2))

    entry_email = ctk.CTkEntry(panel_esquerdo, width=420, placeholder_text="seu_email@fieb.org.br", corner_radius=0, font=("Arial", 11))
    entry_email.pack(anchor="w", pady=(0, 10))
    entry_email.insert(0, getattr(config, "EMAIL_RELATORIO", ""))

    var_filtrar_tags = ctk.BooleanVar(value=getattr(config, "FILTRAR_RELATORIO_POR_TAGS", False))
    chk_filtrar_tags = ctk.CTkCheckBox(panel_esquerdo, text="Filtrar e-mail usando as tags exclusivas do relatório\n(Caso desmarcado, enviará todas as novas capturas)", variable=var_filtrar_tags, corner_radius=0, font=ctk.CTkFont(family="Arial", size=11))
    chk_filtrar_tags.pack(anchor="w", pady=(10, 15))

    # Linha divisória interna estática antes dos botões de ação
    ctk.CTkFrame(panel_esquerdo, height=2, fg_color="#3a3d42", width=420).pack(anchor="w", pady=10)

    btn_salvar = ctk.CTkButton(panel_esquerdo, text="SALVAR PREFERÊNCIAS", corner_radius=0, font=ctk.CTkFont(family="Arial", size=11, weight="bold"), fg_color="#27ae60", hover_color="#219653", width=420, height=32, command=lambda: _acao_salvar_config_relatorio(entry_email, var_filtrar_tags, app_instancia))
    btn_salvar.pack(anchor="w", pady=4)

    _btn_enviar_manual = ctk.CTkButton(panel_esquerdo, text="ATIVAÇÃO DO E-MAIL / ENVIO IMEDIATO DE RELATÓRIO", corner_radius=0, font=ctk.CTkFont(family="Arial", size=11, weight="bold"), fg_color="#1f6aa5", hover_color="#144e78", width=420, height=32, command=lambda: _acao_enviar_relatorio_manual_thread(app_instancia))
    _btn_enviar_manual.pack(anchor="w", pady=4)

    # ==============================================================================
    # 🏷️ PAINEL DA DIREITA: GERENCIAMENTO DE TAGS EXCLUSIVAS
    # ==============================================================================
    panel_direito = ctk.CTkFrame(frame_central, fg_color="transparent")
    panel_direito.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")
    panel_direito.grid_rowconfigure(2, weight=1) # Faz o scroll de tags expandir verticalmente
    panel_direito.grid_columnconfigure(0, weight=1)

    lbl_tags_rel = ctk.CTkLabel(panel_direito, text="Tags de Filtragem Exclusivas do E-mail:", font=ctk.CTkFont(family="Arial", size=12, weight="bold"), text_color="#1f6aa5")
    lbl_tags_rel.grid(row=0, column=0, sticky="w", pady=(5, 2))

    _entry_tag_widget = ctk.CTkEntry(panel_direito, placeholder_text="Pressione Enter ou Vírgula para adicionar uma palavra...", corner_radius=0, font=("Arial", 11))
    _entry_tag_widget.grid(row=1, column=0, sticky="ew", pady=(0, 5))

    # O container de exibição de tags agora ocupa toda a altura útil restante da coluna
    _scroll_container = ctk.CTkScrollableFrame(panel_direito, corner_radius=0, fg_color="#1e1e1e")
    _scroll_container.grid(row=2, column=0, sticky="nsew", pady=(0, 5))

    # Vincula os gatilhos de teclado diretamente na nova estrutura de grid
    _entry_tag_widget.bind("<Return>", lambda e: _adicionar_tag_relatorio_evt())
    _entry_tag_widget.bind(",", lambda e: _adicionar_tag_relatorio_evt())

    # Redesenha a lista de tags guardadas
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

    if email_digitado and ("@" not in email_digitado or "." not in email_digitado):
        messagebox.showerror("E-mail Inválido", "Por favor, insira um endereço de e-mail válido.")
        return

    # Transforma a lista de tags em uma string única separada por vírgulas para o banco
    tags_formatadas_banco = ",".join(_lista_tags_memoria)

    # 🔥 SALVAMENTO EM NUVEM: Sincroniza diretamente com o Supabase usando o cliente config.supabase
    try:
        payload = {
            "email_destino": email_digitado,
            "filtrar_por_tags": deve_filtrar_tags,
            "tags_exclusivas": tags_formatadas_banco
        }
        
        # Tenta atualizar o registro ID 1. Se não existir, faz o insert.
        checar_registro = config.supabase.table("configuracoes_relatorio").select("id").eq("id", 1).execute()
        if checar_registro.data:
            config.supabase.table("configuracoes_relatorio").update(payload).eq("id", 1).execute()
        else:
            payload["id"] = 1
            config.supabase.table("configuracoes_relatorio").insert(payload).execute()

        app_instancia.lbl_status.configure(text=f"Status: Configurações de relatório sincronizadas na nuvem.")
        messagebox.showinfo("Sucesso", "Preferências do relatório salvas na nuvem com sucesso!")
    except Exception as e:
        messagebox.showerror("Erro de Banco", f"Não foi possível salvar na nuvem: {e}")

def _acao_enviar_relatorio_manual_thread(app_instancia):
    global _btn_enviar_manual
    _btn_enviar_manual.configure(state="disabled", text="ENVIANDO RELATÓRIO...")
    app_instancia.lbl_status.configure(text="Status: Compilando editais dos últimos 7 dias...")
    
    thread_envio = threading.Thread(target=lambda: _executar_envio_manual_background(app_instancia))
    thread_envio.daemon = True
    thread_envio.start()

def _executar_envio_manual_background(app_instancia):
    global _btn_enviar_manual
    try:
        sucesso = compilar_e_enviar_relatorio_semanal(lambda msg: app_instancia.lbl_status.configure(text=f"Status: {msg}"))
        if sucesso:
            messagebox.showinfo("Sucesso", "O relatório semanal foi enviado com sucesso via Relay FIEB!")
        else:
            messagebox.showwarning("Aviso", "O relatório não pôde ser enviado. Verifique se existem editais ativos nos últimos 7 dias.")
    except Exception as err:
        messagebox.showerror("Erro de Disparo", f"Falha interna ao tentar acionar o motor de e-mails: {err}")
    finally:
        _btn_enviar_manual.configure(state="normal", text="ATIVAÇÃO DO E-MAIL / ENVIO IMEDIATO DE RELATÓRIO")

def compilar_e_enviar_relatorio_semanal(log_func):
    log_func("Puxando configurações de assinatura de e-mail do Supabase...")
    
    # 🔥 LEITURA EM NUVEM: O robô isolado lê os dados que o usuário postou na tabela
    try:
        resposta_config = config.supabase.table("configuracoes_relatorio").select("*").eq("id", 1).execute()
        if not resposta_config.data:
            log_func("[⚠️ ABORTADO] Nenhuma assinatura de e-mail ativa localizada na tabela configuracoes_relatorio.")
            return False
            
        dados_config = resposta_config.data[0]
        email_destinatario = dados_config.get("email_destino", "").strip()
        deve_filtrar_tags = dados_config.get("filtrar_por_tags", False)
        tags_brutas_banco = dados_config.get("tags_exclusivas", "")
        
        termos_relatorio_usuario = [normalizar_texto_report(t) for t in tags_brutas_banco.split(",") if t.strip()]
    except Exception as e:
        log_func(f"[X] Falha crítica ao ler parâmetros do banco no servidor: {e}")
        return False

    if not email_destinatario:
        log_func("[⚠️ ABORTADO] E-mail do destinatário está em branco no banco de dados.")
        return False

    hoje = datetime.now()
    uma_semana_atras = hoje - timedelta(days=7)
    data_corte_iso = uma_semana_atras.strftime("%Y-%m-%dT%H:%M:%S")

    log_func(f"Compilando editais para: {email_destinatario} | Filtro ativo: {deve_filtrar_tags}")

    try:
        # Busca no banco tudo o que foi gerado com sucesso nos últimos 7 dias pelos robôs
        resposta = config.supabase.table("editais").select("*").gte("created_at", data_corte_iso).eq("status_ia", "CONCLUIDO").execute()
        editais_capturados = resposta.data if hasattr(resposta, 'data') else resposta
    except Exception as e:
        log_func(f"[X] Falha ao consultar tabela editais: {e}")
        return False

    if not editais_capturados:
        log_func("[✨] Nenhum edital novo inserido no banco nos últimos 7 dias. Envio cancelado.")
        return True

    editais_filtrados = []
    for edital in editais_capturados:
        if deve_filtrar_tags and len(termos_relatorio_usuario) > 0:
            tags_ia = [normalizar_texto_report(t) for t in (edital.get("tags_ia", "") or "").split(",") if t.strip()]
            titulo = normalizar_texto_report(edital.get("titulo", ""))
            
            corresponde = False
            for termo in termos_relatorio_usuario:
                if termo in titulo: corresponde = True; break
                if any(termo in tag or tag in termo for tag in tags_ia): corresponde = True; break
            if not corresponde: continue

        editais_filtrados.append(edital)

    if not editais_filtrados:
        log_func("[✨] Os robôs acharam editais, mas nenhum bate com as tags salvas pelo usuário.")
        return True

    html_corpo = f"""
    <html><head><style>
        body {{ font-family: Arial, sans-serif; margin:0; padding:20px; color:#333; background-color:#f8f9fa; }}
        .container {{ max-width:800px; margin:0 auto; background:#fff; padding:30px; border:1px solid #e2e8f0; }}
        .header {{ border-bottom:3px solid #1f6aa5; padding-bottom:15px; margin-bottom:25px; }}
        .header h2 {{ color:#1f6aa5; margin:0; font-size:22px; }}
        .card {{ border:1px solid #e2e8f0; border-left:5px solid #27ae60; padding:15px; margin-bottom:20px; background:#fafbfc; }}
        .card h3 {{ margin:0 0 10px 0; font-size:16px; color:#2d3748; }}
        .meta {{ font-size:12px; color:#4a5568; margin-bottom:10px; line-height:1.6; }}
        .escopo {{ font-size:13px; color:#4a5568; text-align:justify; line-height:1.5; background:#fff; padding:10px; border:1px solid #edf2f7; }}
        .btn-link {{ display:inline-block; background-color:#1f6aa5; color:#ffffff !important; text-decoration:none; padding:6px 12px; font-size:12px; font-weight:bold; margin-top:10px; }}
        .footer {{ font-size:11px; color:#a0aec0; text-align:center; margin-top:30px; border-top:1px solid #e2e8f0; padding-top:15px; }}
    </style></head><body>
        <div class="container">
            <div class="header">
                <h2>RELATÓRIO SEMANAL DE NOVOS EDITAIS</h2>
                <p>Compilado automatizado de oportunidades — Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
            </div>
    """
    for item in editais_filtrados:
        html_corpo += f"""
            <div class="card">
                <h3>{item.get('titulo', 'Edital sem título')}</h3>
                <div class="meta">
                    <strong>Portal:</strong> {item.get('portal', 'N/A')} | <strong>Prazo:</strong> {item.get('datas', 'A consultar')}<br>
                    <strong>Vigência:</strong> {item.get('vigencia_projeto', 'N/A')} | <strong>Verba:</strong> {item.get('subvencao', 'N/A')}<br>
                    <strong>Tags:</strong> <i>{item.get('tags_ia', 'Geral')}</i>
                </div>
                <div class="escopo"><strong>Resumo:</strong> {item.get('escopo', 'Sem resumo.')}</div>
                <a href="{item.get('url', '#')}" class="btn-link" target="_blank">VISUALIZAR EDITAL FONTE</a>
            </div>
        """
    html_corpo += "</div></body></html>"

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_REMETENTE
        msg['To'] = email_destinatario
        msg['Subject'] = f"📋 Relatório PCE Semanal - {len(editais_filtrados)} Novos Editais Encontrados"
        msg.attach(MIMEText(html_corpo, 'html', 'utf-8'))
        
        servidor = smtplib.SMTP(SMTP_SERVIDOR, SMTP_PORTA, timeout=30)
        servidor.sendmail(SMTP_REMETENTE, email_destinatario, msg.as_string())
        servidor.quit()
        return True
    except Exception as e:
        log_func(f"[X] Erro SMTP FIEB: {e}")
        return False
