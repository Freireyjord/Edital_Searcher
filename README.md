# 🔍 Painel de Consulta de Editais (PCE)

O **Painel de Consulta de Editais (PCE)** é uma aplicação desktop corporativa desenvolvida em Python para centralizar, filtrar e monitorar editais públicos de fomento e inovação tecnológica. Integrado nativamente com o banco de dados em nuvem **Supabase** e o sistema de Relay de e-mails corporativo, o ecossistema permite o acompanhamento em tempo real de novas oportunidades de mercado.

---

## 🚀 Principais Recursos

- **Interface Gráfica Moderna (GUI):** Desenvolvida com `customtkinter`, oferecendo suporte nativo ao modo escuro/claro do sistema operacional e redimensionamento inteligente para telas de baixa resolução.
- **Sincronização em Nuvem:** Integração direta com tabelas de dados do **Supabase** para buscar editais processados por IA e ler preferências de usuários em tempo real de forma assíncrona.
- **Sistema Avançado de Filtros Locais:**
  - Busca por tags e palavras-chave dinâmicas com renderização visual de chips customizados.
  - Filtros por portais de origem extraídos dinamicamente da base de dados (CNPq, FINEP, FUNDEP, Petrobras, etc.).
  - Controle de intervalos de prazos usando calendário integrado (`tkcalendar`).
- **Gerenciamento Dinâmico de Colunas:** Permite ocultar e ordenar colunas da tabela (`Treeview`) dinamicamente com ajuste automático de proporção para eliminar barras de rolagem horizontais desnecessárias.
- **Relatório Semanal Automatizado com Fatiamento:** Motor interno integrado ao SMTP Relay que compila editais dos últimos 7 dias e envia e-mails formatados em HTML. Possui mecanismo de fatiamento inteligente (máximo de 20 editais por bloco) para evitar rejeição nos servidores corporativos.
- **Fluxo de Cancelamento Seguro:** Sistema de segurança de exclusão de assinaturas por validação atômica de Token de 6 dígitos enviado por e-mail (CSPRNG).
- **Atualizador Automático Atômico (Auto-Updater):** O sistema verifica atualizações diretamente nas *Releases estáveis* da API do GitHub em segundo plano, valida a integridade do pacote via hash SHA-256 e executa um script patcher (`.bat`) assíncrono para auto-substituição do executável sem interrupção manual.

---

## 📁 Estrutura do Projeto

O projeto adota uma arquitetura modularizada, separando regras de negócios e infraestrutura de dados da camada visual de componentes:

```text
App PCE/
│
├── app_main.py                 # Ponto de entrada principal da aplicação (AppSincronizador)
├── compilar_app.py             # Script de automação do build com PyInstaller e suporte a ícones
├── app_icone.ico               # Ícone oficial da aplicação
├── config_app.json             # Preferências e tags salvas localmente no computador do usuário
│
├── core/                       # Módulos centrais de infraestrutura e dados
│   ├── config.py               # Inicializador do cliente Supabase e persistência do JSON local
│   ├── editais_repo.py         # Consultas paginadas e otimizadas ao banco de dados Supabase
│   ├── filtro_editais.py       # Regras puras de filtragem, normalização e ordenação de dados
│   ├── email_engine.py         # Motor de compilação de HTML, fatiamento e disparo de relatórios SMTP
│   └── updater.py              # Validador de versões via GitHub API, download seguro e injeção do patcher
│
└── views/                      # Camada de componentes visuais do CustomTkinter
    ├── aba_resultados.py       # Gerenciamento da aba principal, ordenação e exibição de resumos de IA
    ├── aba_relatorio.py        # Painel de assinaturas, gerenciador de tags e fluxos de token
    ├── filtros_sidebar.py      # Painel lateral esquerdo para filtros de data, portais e termos
    └── colunas_sidebar.py      # Painel lateral direito para exibição seletiva de colunas
```

---

## 🛠️ Pré-requisitos & Tecnologias

Antes de rodar ou compilar o projeto localmente, certifique-se de possuir instalado:
- **Python 3.10 ou superior** (Testado e homologado até a versão 3.13)
- Banco de dados configurado no **Supabase** (Tabelas: `editais` e `configuracoes_relatorio`)

### Dependências principais:
- `customtkinter` (Interface gráfica moderna)
- `tkcalendar` e `babel` (Componente visual de calendário e localização de data)
- `supabase` (Cliente de conexão com o banco de dados em nuvem)
- `requests` (Chamadas HTTP para API do GitHub)
- `pyinstaller` (Ferramenta de congelamento de binários)

---

## 📦 Processo de Compilação Corporativa

Para gerar a pasta de distribuição final estável do aplicativo contendo o executável congelado com a identidade visual da empresa, utilize o script automatizado de build:

1. Certifique-se de que o PyInstaller está instalado no ambiente do seu interpretador Python:
   ```powershell
   python -m pip install pyinstaller
   ```
2. Execute o script de automação na raiz do projeto:
   ```powershell
   python compilar_app.py
   ```
3. O build completo será gerado no diretório `dist/PCE/`.

> **Nota de Infraestrutura:** Lembre-se de fornecer o arquivo de credenciais do Relay corporativo local (`smtp_config.json`) dentro da pasta resultante antes de zipar o pacote para os colaboradores.

---

## 🔄 Mecanismo de Atualização Automática

Para disponibilizar uma nova versão compatível com o atualizador automático em background:

1. Atualize a constante `VERSAO_ATUAL` no arquivo `core/updater.py` (ex: `"1.1.1"`).
2. Execute o script `compilar_app.py` para gerar os novos binários atualizados.
3. Compacte o **conteúdo interno** da pasta gerada em `dist/PCE/` em um arquivo chamado estritamente **`PCE.zip`**.
4. Calcule o hash SHA-256 do arquivo gerado para validação de integridade. No Windows PowerShell, execute:
   ```powershell
   certutil -hashfile PCE.zip SHA256
   ```
5. Crie uma nova **Release** no seu repositório do GitHub com a respectiva Tag da versão (ex: `v1.1.1`).
6. Anexe o arquivo **`PCE.zip`** e um arquivo de texto contendo o hash chamado **`PCE.zip.sha256`** nos Assets da release. O aplicativo cliente detectará a nova versão de forma atômica no próximo ciclo de inicialização.

---

## 📝 Licença e Uso Corporativo

Este software foi desenvolvido para otimização de fluxos de análise e inteligência de mercado de editais. Todos os direitos reservados à infraestrutura interna de tecnologia associada.
