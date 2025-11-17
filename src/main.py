import os
import time
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
from dotenv import load_dotenv
import csv

# ================================
# CARREGAR VARIÁVEIS DO .ENV
# ================================
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
PLANILHAS_FOLDER = os.getenv("PLANILHAS_FOLDER")

DOWNLOAD = PLANILHAS_FOLDER

# ================================
# FUNÇÃO: PEGAR ÚLTIMO ARQUIVO BAIXADO
# ================================
def get_last_download(path, prefix):
    arquivos = [f for f in os.listdir(path) if f.startswith(prefix)]
    if not arquivos:
        raise Exception(f"Nenhum arquivo encontrado começando com '{prefix}'")

    arquivos = sorted(
        arquivos,
        key=lambda x: os.path.getmtime(os.path.join(path, x)),
        reverse=True
    )

    return os.path.join(path, arquivos[0])

# ================================
# DETECTAR ENCODING AUTOMÁTICO
# ================================
def detectar_encoding(filepath):
    encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
    for enc in encodings:
        try:
            with open(filepath, encoding=enc) as f:
                f.readline()
            return enc
        except:
            pass
    return "latin-1"

# ================================
# DETECTAR SEPARADOR AUTOMÁTICO
# ================================
def detectar_separador(filepath, encoding):
    with open(filepath, "r", encoding=encoding) as f:
        linha = f.readline()
        if ";" in linha:
            return ";"
        if "," in linha:
            return ","
    return ";"  # fallback

# ================================
# NORMALIZAR NOMES DE COLUNAS
# ================================
def normalizar_colunas(df):
    colunas_novas = {}
    for i, col in enumerate(df.columns):
        nome = f"col_{i+1}"
        colunas_novas[col] = nome
    df.rename(columns=colunas_novas, inplace=True)
    return df

# ================================
# PROCESSAR ARQUIVO CSV
# ================================
def processar(filepath):
    print(f"Lendo arquivo: {filepath}")

    # Detectar encoding
    encoding = detectar_encoding(filepath)
    print("Encoding detectado:", encoding)

    # Detectar separador
    sep = detectar_separador(filepath, encoding)
    print("Separador detectado:", sep)

    # Ler CSV
    df = pd.read_csv(filepath, encoding=encoding, sep=sep)

    # Normalizar nomes das colunas
    df = normalizar_colunas(df)

    # Adicionar timestamp
    df["data_atualizacao"] = pd.Timestamp.now()

    # Nome da tabela baseado no arquivo
    nome_tabela = os.path.basename(filepath).split(".")[0]
    nome_tabela = nome_tabela.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")

    print("Tabela alvo:", nome_tabela)

    # Conectar MySQL via SQLAlchemy
    engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    # Inserir no MySQL
    try:
        df.to_sql(nome_tabela, engine, if_exists="replace", index=False)
        print("Carga concluída com sucesso!")
    except Exception as e:
        print("Erro ao inserir:", e)

# ================================
# PROGRAMA PRINCIPAL
# ================================
if __name__ == "__main__":
    arquivo = get_last_download(DOWNLOAD, prefix="municipios")
    processar(arquivo)
