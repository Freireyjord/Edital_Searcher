# Sistema Inteligente de Pesquisa e Triagem de Editais

Este sistema consiste em um ecossistema automatizado em Python projetado para a captura, triagem, análise e consulta inteligente de editais públicos de inovação, tecnologia e pesquisa. O software elimina o esforço humano de varredura manual, transformando editais complexos em dados estruturados, indexados e facilmente consultáveis por meio de uma interface desktop responsiva.

## Arquitetura do Sistema

O projeto é dividido de forma modular em duas esteiras principais:

*   **PARTE 1: Orquestração & Esteira de Dados (Backend)**
    *   `config.py`: Definições dinâmicas e credenciais globais.
    *   `processador.py`: Motor de inteligência integrada e rotinas de faxina.
    *   `worker_background.py`: Serviço de segundo plano e loop de varredura ativa.
    *   `extrator_base.py`: Raspagem de HTML/PDF e tratamento inteligente de tokens.

*   **PARTE 2: Disponibilização & Interface Visual (Frontend)**
    *   `app_main.py`: Dashboard principal com Treeview e visualizador embutido.
    *   `filtros_sidebar.py`: Painel retrátil esquerdo (Filtros cronológicos e Tags).
    *   `colunas_sidebar.py`: Painel retrátil direito (Gerenciador dinâmico de colunas).
    *   `config_app.py`: Persistência local de preferências do usuário (JSON).

---

## Como o Sistema Funciona

1. **Varredura e Raspagem:** O `worker_background.py` aciona motores plugáveis localizados na pasta `portais/` a cada 2 horas. O conteúdo textual (HTML ou PDFs complexos com suporte a OCR/Tesseract) é extraído de forma limpa pelo `extrator_base.py`.
2. **Estratégia de Janela de Contexto:** Para otimizar o consumo de tokens na IA, textos superiores a 25.000 caracteres passam por uma captura dupla inteligente (Cabeça + Cauda).
3. **Análise por IA (Enriquecimento):** O texto sucintado é submetido ao modelo da API do Gemini através de um prompt restritivo que proíbe tags genéricas e gera estritamente um JSON estruturado contendo prazos, vigências, linhas de pesquisa, subvenção econômica e *tags_ia*.
4. **Armazenamento em Nuvem:** Os registros são gravados com status `PENDENTE` e atualizados para `CONCLUIDO` no banco de dados Supabase. Editais com prazos vencidos são limpos automaticamente da base ativa por uma rotina de faxina programada.
5. **Painel de Consulta:** A interface em CustomTkinter consome a base e utiliza um **Algoritmo de Ranqueamento por Aderência**, ordenando os editais dinamicamente no topo de acordo com a quantidade de correspondências (*matches*) encontradas entre as tags de busca locais e os metadados do edital.

---

## Tecnologias Utilizadas

* **Linguagem:** Python 3.11+
* **Interface Gráfica:** CustomTkinter (Temas responsivos e componentes industriais)
* **Orquestração de IA:** Google GenAI SDK
* **Persistência de Dados:** Banco de Dados Supabase (PostgreSQL Cloud)
* **Visão Computacional / OCR:** PyTesseract & PDF2Image (Para leitura de editais digitalizados em imagem)
* **Análise de Texto:** PyPDF, PDFMiner & BeautifulSoup4
