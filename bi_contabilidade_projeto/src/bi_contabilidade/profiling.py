import os
from pathlib import Path

import pandas as pd


BASE_PATH = Path(
    r"C:\Users\mfarias\OneDrive - CRISTALPET\POWER BI\Projetos\Contabilidade\Dataset"
)


def listar_arquivos():
    extensoes = [".xlsx", ".xls", ".csv", ".txt"]
    arquivos = []

    for arquivo in BASE_PATH.iterdir():
        if arquivo.suffix.lower() in extensoes:
            arquivos.append(arquivo)

    return arquivos


def analisar_dataframe(df: pd.DataFrame, nome: str):
    print("\n" + "=" * 80)
    print(f"DATASET: {nome}")
    print("=" * 80)

    print(f"\nLinhas: {len(df):,}")
    print(f"Colunas: {len(df.columns):,}")

    print("\nColunas:")
    for col in df.columns:
        print(f"- {col}")

    print("\nTipos de dados:")
    print(df.dtypes)

    print("\nNulos por coluna:")
    print(df.isna().sum())

    print("\nValores distintos por coluna:")
    print(df.nunique(dropna=True))

    print("\nAmostra:")
    print(df.head(10))


def validar_fato_lancamento(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("VALIDAÇÃO ESPECÍFICA: FatoLancamentoContabil")
    print("=" * 80)

    colunas_necessarias = [
        "CODLANC",
        "LDATA",
        "CONTA",
        "CCUS",
        "CNT_AUX",
        "ITEM_CNTAUX",
        "VALOR_DEB",
        "VALOR_CRE",
        "VALOR_LIQ",
        "DSC_COMPLEMENTO",
    ]

    print("\nColunas esperadas:")
    for col in colunas_necessarias:
        status = "OK" if col in df.columns else "FALTANDO"
        print(f"- {col}: {status}")

    if {"VALOR_DEB", "VALOR_CRE", "VALOR_LIQ"}.issubset(df.columns):
        deb = pd.to_numeric(df["VALOR_DEB"], errors="coerce").fillna(0)
        cre = pd.to_numeric(df["VALOR_CRE"], errors="coerce").fillna(0)
        liq = pd.to_numeric(df["VALOR_LIQ"], errors="coerce").fillna(0)

        calc_liq = deb - cre
        divergencia = (calc_liq.round(2) != liq.round(2))

        print(f"\nTotal débitos: {deb.sum():,.2f}")
        print(f"Total créditos: {cre.sum():,.2f}")
        print(f"Total valor líquido: {liq.sum():,.2f}")
        print(f"Divergências em VALOR_LIQ = DEB - CRE: {divergencia.sum():,}")

    if "CONTA" in df.columns:
        print("\nTop 15 contas por quantidade de lançamentos:")
        print(df["CONTA"].astype(str).value_counts().head(15))

    if "CNT_AUX" in df.columns:
        print("\nPreenchimento de CNT_AUX:")
        print(df["CNT_AUX"].isna().value_counts(dropna=False))

    if "ITEM_CNTAUX" in df.columns:
        print("\nPreenchimento de ITEM_CNTAUX:")
        print(df["ITEM_CNTAUX"].isna().value_counts(dropna=False))


def processar_excel(caminho: Path):
    print("\n" + "#" * 100)
    print(f"ARQUIVO EXCEL: {caminho.name}")
    print("#" * 100)

    xls = pd.ExcelFile(caminho)

    print("\nAbas encontradas:")
    for aba in xls.sheet_names:
        print(f"- {aba}")

    for aba in xls.sheet_names:
        df = pd.read_excel(caminho, sheet_name=aba)
        analisar_dataframe(df, f"{caminho.name} | {aba}")

        if aba.strip().lower() == "fatolancamentocontabil":
            validar_fato_lancamento(df)


def main():
    if not BASE_PATH.exists():
        print("Pasta não encontrada.")
        print(f"Caminho configurado: {BASE_PATH}")
        print("Confira se o nome da pasta está exatamente igual no Windows Explorer.")
        raise SystemExit(1)

    arquivos = listar_arquivos()

    print(f"Pasta analisada: {BASE_PATH}")
    print(f"Arquivos encontrados: {len(arquivos)}")

    for arquivo in arquivos:
        print(f"- {arquivo.name}")

    for arquivo in arquivos:
        if arquivo.suffix.lower() in [".xlsx", ".xls"]:
            processar_excel(arquivo)


if __name__ == "__main__":
    main()