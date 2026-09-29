import smtplib, unicodedata

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# Importa o config que está na mesma pasta (core) para ler o cliente Supabase e variáveis
from core import config

# ==============================================================================
# 🔐 CONFIGURAÇÕES DE RELAY CORPORATIVO INTERNO - FIEB
# ==============================================================================
SMTP_SERVIDOR = "fieb-org-br.mail.protection.outlook.com"
SMTP_PORTA = 25
SMTP_REMETENTE = "joao.freire@fbter.org.br"
SMTP_SENHA = ""

def normalizar_texto_report(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def compilar_e_enviar_relatorio_semanal(email_alvo, log_func):
    """
    Processa a busca de editais dos últimos 7 dias na tabela do Supabase,
    filtra de acordo com as preferências do e-mail informado e realiza 
    o disparo do relatório formatado em HTML via Relay corporativo.
    """
    log_func(f"Puxando configurações de assinatura para {email_alvo} no Supabase...")
    
    if not email_alvo:
        log_func("[⚠️ ABORTADO] E-mail nulo enviado para o motor de compilação.")
        return False

    # 🔥 LEITURA EM NUVEM DINÂMICA (MULTI-USUÁRIO): Busca estritamente pelo e-mail informado
    try:
        resposta_config = config.supabase.table("configuracoes_relatorio").select("*").eq("email_destino", email_alvo.lower().strip()).execute()
        if not resposta_config.data or len(resposta_config.data) == 0:
            log_func(f"[⚠️ ABORTADO] Nenhuma assinatura ativa localizada para o e-mail: {email_alvo}")
            return False
            
        dados_config = resposta_config.data[0]
        id_registro = dados_config.get("id") # Captura o ID real deste usuário no banco
        email_destinatario = dados_config.get("email_destino", "").strip()
        deve_filtrar_tags = dados_config.get("filtrar_por_tags", False)
        tags_brutas_banco = dados_config.get("tags_exclusivas", "")
        
        termos_relatorio_usuario = [normalizar_texto_report(t) for t in tags_brutas_banco.split(",") if t.strip()]
    except Exception as e:
        log_func(f"[X] Falha crítica ao ler parâmetros do banco no servidor: {e}")
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

        # 🔥 GRAVAÇÃO INTELIGENTE DE INFRAESTRUTURA: Atualiza carimbo usando o ID dinâmico real da linha
        try:
            hoje_data = datetime.now().strftime("%Y-%m-%d")
            config.supabase.table("configuracoes_relatorio").update({"ultimo_envio": hoje_data}).eq("id", id_registro).execute()
            log_func("[✓] Data do último envio registrada com sucesso no banco de dados.")
        except Exception as e_banco:
            log_func(f"[⚠️ AVISO] E-mail enviado, mas falhou ao gravar data no banco: {e_banco}")

        return True
    except Exception as e:
        log_func(f"[X] Erro SMTP FIEB: {e}")
        return False