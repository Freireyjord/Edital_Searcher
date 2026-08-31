# Edital_Searcher

## Bibliotecas
pip install requests beautifulsoup4 selenium webdriver-manager google-genai pypdf pdf2image pytesseract

## Gerar .exe
pyinstaller --noconfirm --onefile --windowed --collect-all selenium --add-data "tesseract_bin;tesseract_bin" --add-data "C:\Users\joao.freire\Documents\Codigos\.venv\Lib\site-packages\customtkinter;customtkinter/" app_main.py
