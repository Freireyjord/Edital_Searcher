# Edital_Searcher

## Bibliotecas
pip install google-genai customtkinter selenium pypdf pdf2image pytesseract tkcalendar babel requests beautifulsoup4


## Gerar .exe
pyinstaller --noconfirm --onefile --windowed --collect-all selenium --add-data "tesseract_bin;tesseract_bin" --add-data "C:\Users\joao.freire\Documents\Codigos\.venv\Lib\site-packages\customtkinter;customtkinter/" app_main.py
