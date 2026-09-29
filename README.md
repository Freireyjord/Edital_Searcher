# 🔍 Painel de Consulta de Editais (PCE)

O **Painel de Consulta de Editais (PCE)** é uma aplicação desktop corporativa desenvolvida em Python para centralizar, filtrar e monitorar editais públicos de fomento e inovação tecnológicos. Integrado nativamente com o banco de dados em nuvem **Supabase** e o sistema de Relay de e-mails corporativo, o ecossistema permite o acompanhamento em tempo real de novas oportunidades de mercado.

---

## 🚀 Principais Recursos

- **Interface Gráfica Moderna (GUI):** Desenvolvida com `customtkinter`, oferecendo uma experiência de usuário polida e suporte nativo ao modo escuro/claro do sistema operacional.
- **Sincronização em Nuvem:** Integração direta com tabelas de dados do **Supabase** para buscar editais processados por IA e ler assinaturas de usuários em tempo real.
- **Sistema Avançado de Filtros Locais:**
  - Busca por tags e palavras-chave dinâmicas (com suporte a remoção visual e normalização de strings).
  - Filtros por portais de origem específicos (CNPq, FINEP, FUNDEP, Petrobras).
  - Controle de intervalos de prazos usando calendário integrado (`tkcalendar`).
- **Gerenciamento Dinâmico de Colunas:** Permite ocultar e ordenar colunas da tabela (`Treeview`) dinamicamente sem quebrar a interface gráfica.
- **Relatório Semanal Automatizado:** Motor interno integrado ao SMTP Relay que compila editais dos últimos 7 dias e envia e-mails formatados em HTML baseado nas preferências de cada colaborador.
- **Fluxo de Cancelamento Seguro:** Sistema de segurança de exclusão de assinaturas por validação atômica de Token de 6 dígitos enviado por e-mail.
- **Atualizador Automático Atômico (Auto-Updater):** O sistema verifica atualizações diretamente nas *Releases estáveis* da API do GitHub, baixa arquivos binários temporários comprimidos e executa um script patcher (`.bat`) assíncrono para auto-substituição do executável sem interrupção manual.

---

## 📁 Estrutura do Projeto

O projeto adota uma arquitetura modularizada separando regras de negócios e configurações centrais da interface visual:

```text
Edital_Searcher/
│
├── app_main.py                 # Ponto de entrada principal da aplicação (AppSincronizador)
├── config_app.json             # Preferências e tags salvas localmente no computador do usuário
│
├── core/                       # Módulos centrais de infraestrutura de dados
│   ├── config.py               # Inicializador do cliente Supabase e persistência do JSON local
│   ├── email_engine.py         # Motor de compilação, normalização e disparo de relatórios HTML
│   └── updater.py              # Validador de versões via GitHub API e injeção do script patcher
│
└── views/                      # Camada de componentes visuais do CustomTkinter
    ├── aba_resultados.py       # Gerenciamento da aba principal, ordenação de dados e resumos de IA
    ├── aba_relatorio.py        # Painel de assinaturas, gerenciador de tags e fluxos de token
    ├── filtros_sidebar.py      # Painel lateral esquerdo para filtros de data, portais e termos
    └── colunas_sidebar.py      # Painel lateral direito para exibição seletiva de colunas
```

---

## 🛠️ Pré-requisitos & Tecnologias

Antes de rodar o projeto localmente, certifique-se de possuir instalado:
- **Python 3.10 ou superior**
- Banco de dados configurado no **Supabase** (Tabelas: `editais` e `configuracoes_relatorio`)

### Dependências principais:
- `customtkinter` (Interface gráfica)
- `supabase` (Cliente de conexão com o banco de dados)
- `requests` (Chamadas HTTP para API do GitHub)
- `tkcalendar` (Componente visual de calendário)

---

## 🔄 Fluxo do Mecanismo de Atualização

Para gerar novas versões compatíveis com o atualizador automático do sistema:
1. Altere a constante `VERSAO_ATUAL` no arquivo `core/updater.py` (ex: `"1.0.3"`).
2. Gere o executável congelado do sistema (utilizando ferramentas como o `PyInstaller`).
3. Empacote os arquivos binários gerados na pasta de destino em um arquivo compactado obrigatoriamente chamado **`PCE.zip`**.
4. Crie uma nova **Release** no seu repositório do GitHub com a correspondente Tag da versão (ex: `v1.0.3`) e anexe o arquivo `PCE.zip` nos Assets da release.
5. O aplicativo instalado nas máquinas clientes detectará a alteração via API do GitHub no próximo ciclo de inicialização.

---

## 📝 Licença e Uso Corporativo

Este software foi desenvolvido para otimização de fluxos de análise e inteligência de mercado de editais. 
Todos os direitos reservados à infraestrutura interna de tecnologia associada.
