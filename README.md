# Edital_Searcher

## Bibliotecas
pip install requests beautifulsoup4 selenium webdriver-manager google-genai pypdf pdf2image pytesseract

## Gerar .exe
pyinstaller --noconfirm --onefile --windowed --collect-all selenium --add-data "$(python -c 'import customtkinter, os; print(os.path.dirname(customtkinter.__file__))')/assets;customtkinter/assets" app_main.py
