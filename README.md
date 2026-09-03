# Edital_Searcher

## Bibliotecas
pip install customtkinter tkcalendar requests bs4 selenium pytesseract pypdf pdf2image google

## Gerar .exe
pyinstaller --noconfirm --onefile --windowed --collect-all selenium --add-data "tesseract_bin;tesseract_bin" --add-data "C:\Users\joao.freire\Documents\Codigos\.venv\Lib\site-packages\customtkinter;customtkinter/" app_main.py
