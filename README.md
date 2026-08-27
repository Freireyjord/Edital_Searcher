# Edital_Searcher

## Bibliotecas
pip install requests beautifulsoup4 selenium webdriver-manager google-genai pypdf pdf2image pytesseract

## Gerar .exe
pyinstaller --onefile --noconsole --hidden-import=PIL.Image --hidden-import=selenium.webdriver.chrome.options app_editais.py
