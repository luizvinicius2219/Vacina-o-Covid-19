import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path


# =====================================================================
# CARREGAR VARIÁVEIS DO .ENV
# =====================================================================

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
PLANILHAS_FOLDER = os.getenv("PLANILHAS_FOLDER")


# =====================================================================
# ABRIR NAVEGADOR
# =====================================================================
navegador = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
navegador.get("https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_Vacina_C19/SEIDIGI_DEMAS_Vacina_C19.html#")
navegador.maximize_window()


def send_multiple_keys(navegador, key, times):
    for _ in range(times):
        navegador.switch_to.active_element.send_keys(key)
        time.sleep(1)


# =====================================================================
# FUNÇÕES GERAIS (APENAS 1 VEZ)
# =====================================================================

def get_last_planilha(path):
    arquivos = [
        f for f in os.listdir(path)
        if f.lower().endswith((".xlsx", ".xls", ".csv"))
    ]
    if not arquivos:
        raise Exception("Nenhuma planilha encontrada na pasta de downloads.")

    arquivos = sorted(
        arquivos,
        key=lambda x: os.path.getmtime(os.path.join(path, x)),
        reverse=True
    )
    return os.path.join(path, arquivos[0])


def ler_arquivo(arquivo):
    if arquivo.lower().endswith(".csv"):
        return pd.read_csv(arquivo, sep=";", encoding="latin1")
    return pd.read_excel(arquivo)


def inserir_no_banco(regiao):
    arquivo = get_last_planilha(PLANILHAS_FOLDER)
    print(f"Lendo arquivo: {arquivo}")

    df = ler_arquivo(arquivo)
    df["regiao"] = regiao
    df["data_atualizacao"] = datetime.now()

    engine = create_engine(
        f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    try:
        df.to_sql("fato_municipio", engine, if_exists="append", index=False)
        print(f"Carga da região {regiao} concluída com sucesso.")
    except Exception as e:
        print("Erro ao inserir:", e)


# =====================================================================
# FUNÇÃO PARA SELECIONAR REGIÃO, EXPORTAR E CARREGAR
# =====================================================================
def processar_regiao(nome_regiao, seletor_css):
    print(f"\n=== PROCESSANDO {nome_regiao} ===")

    # Abrir filtro
    FILTRO_REGIAO = WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR,
        "#AFrCmZx_content > div > div > div:nth-child(1) > div > div > div > div > div > div.MuiGrid-root.MuiGrid-container.css-q0qbej > h6"))
    )
    FILTRO_REGIAO.click()
    time.sleep(5)

    # Selecionar região
    REGIAO = WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, seletor_css))
    )
    REGIAO.click()
    time.sleep(5)

    # Fechar filtro
    FECHAR_FILTRO = WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR,
        "#actions-toolbar > div.njs-b447-Grid-root.njs-b447-Grid-container.njs-b447-Grid-item.njs-b447-Grid-wrap-xs-nowrap.actions-toolbar-default-actions.css-3cuy5k > div:nth-child(3) > button > i > svg > path"))
    )
    FECHAR_FILTRO.click()
    time.sleep(5)

    # Scroll para botão
    send_multiple_keys(navegador, Keys.PAGE_DOWN, 3)
    time.sleep(5)

    # Clicar exportar
    FATO_MUNICIPIO = WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#exportar-dados-QV22"))
    )
    FATO_MUNICIPIO.click()
    time.sleep(8)

    # Inserir no banco
    inserir_no_banco(nome_regiao)

    # Limpar filtro
    LIMPAR = WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#Região > span.clear-field"))
    )
    LIMPAR.click()
    time.sleep(5)


# =====================================================================
# PROCESSAMENTO DAS TRÊS REGIÕES
# =====================================================================

processar_regiao(
    "Centro-Oeste",
    "body > div.MuiPopover-root.listbox-popover.MuiModal-root.css-1nac088 "
    "> div.MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation8."
    "MuiPopover-paper.css-1dmzujt > div > div > "
    "div.njs-b447-Grid-root.njs-b447-Grid-container.njs-b447-Grid-item."
    "njs-b447-Grid-direction-xs-column.css-ko7loy > "
    "div.njs-b447-Grid-root.njs-b447-Grid-item.njs-b447-Grid-grid-xs-true."
    "ListBoxInline-listboxWrapper.css-1pbssk3 > div > div > div."
    "ListBox-styledScrollbars.css-1nwu5vb > div > div:nth-child(1) span"
)

processar_regiao(
    "Nordeste",
    "body > div.MuiPopover-root.listbox-popover.MuiModal-root.css-1nac088 "
    "> div.MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation8."
    "MuiPopover-paper.css-1dmzujt > div > div > "
    "div.njs-b447-Grid-root.njs-b447-Grid-container.njs-b447-Grid-item."
    "njs-b447-Grid-direction-xs-column.css-ko7loy > "
    "div.njs-b447-Grid-root.njs-b447-Grid-item.njs-b447-Grid-grid-xs-true."
    "ListBoxInline-listboxWrapper.css-1pbssk3 > div > div > div."
    "ListBox-styledScrollbars.css-1nwu5vb > div > div:nth-child(2) span"
)

processar_regiao(
    "Norte",
    "body > div.MuiPopover-root.listbox-popover.MuiModal-root.css-1nac088 "
    "> div.MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation8."
    "MuiPopover-paper.css-1dmzujt > div > div > "
    "div.njs-b447-Grid-root.njs-b447-Grid-container.njs-b447-Grid-item."
    "njs-b447-Grid-direction-xs-column.css-ko7loy > "
    "div.njs-b447-Grid-root.njs-b447-Grid-item.njs-b447-Grid-grid-xs-true."
    "ListBoxInline-listboxWrapper.css-1pbssk3 > div > div > div."
    "ListBox-styledScrollbars.css-1nwu5vb > div > div:nth-child(3) span"
)

processar_regiao(
    "Sudeste",
    "body > div.MuiPopover-root.listbox-popover.MuiModal-root.css-1nac088 "
    "> div.MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation8."
    "MuiPopover-paper.css-1dmzujt > div > div > "
    "div.njs-b447-Grid-root.njs-b447-Grid-container.njs-b447-Grid-item."
    "njs-b447-Grid-direction-xs-column.css-ko7loy > "
    "div.njs-b447-Grid-root.njs-b447-Grid-item.njs-b447-Grid-grid-xs-true."
    "ListBoxInline-listboxWrapper.css-1pbssk3 > div > div > div."
    "ListBox-styledScrollbars.css-1nwu5vb > div > div:nth-child(4) span"
)

processar_regiao(
    "Sul",
    "body > div.MuiPopover-root.listbox-popover.MuiModal-root.css-1nac088 "
    "> div.MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation8."
    "MuiPopover-paper.css-1dmzujt > div > div > "
    "div.njs-b447-Grid-root.njs-b447-Grid-container.njs-b447-Grid-item."
    "njs-b447-Grid-direction-xs-column.css-ko7loy > "
    "div.njs-b447-Grid-root.njs-b447-Grid-item.njs-b447-Grid-grid-xs-true."
    "ListBoxInline-listboxWrapper.css-1pbssk3 > div > div > div."
    "ListBox-styledScrollbars.css-1nwu5vb > div > div:nth-child(5) span"
)


print("\n=== PROCESSO FINALIZADO! ===")
navegador.quit