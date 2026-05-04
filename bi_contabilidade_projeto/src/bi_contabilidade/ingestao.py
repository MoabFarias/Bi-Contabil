from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from .configuracao import normalizar_texto, slug


TRANSACTION_SYNONYMS = {
    "id_lancamento": [
        "lancamento",
        "id lancamento",
        "numero lancamento",
        "num lancamento",
        "partida",
        "lote",
    ],
    "data_lancamento": ["data", "data lancamento", "dt lancamento", "data contabil"],
    "conta_contabil": ["conta", "conta contabil", "cod conta", "codigo conta", "conta ctb"],
    "descricao": ["historico", "descricao", "complemento", "detalhe", "texto"],
    "documento": ["documento", "doc", "nf", "numero documento"],
    "centro_custo": ["centro custo", "ccusto", "centro de custo", "cost center"],
    "debito": ["debito", "valor debito", "vl debito", "deb"],
    "credito": ["credito", "valor credito", "vl credito", "cred"],
    "valor": ["valor", "valor lancamento", "montante", "amount"],
    "tipo_dc": ["dc", "tipo", "debito credito", "natureza", "dr cr"],
}

TRIAL_BALANCE_SYNONYMS = {
    "conta_contabil": ["conta", "conta contabil", "codigo conta", "cod conta", "conta ctb"],
    "descricao_conta": ["descricao", "descricao conta", "conta descricao", "nome conta"],
    "saldo_inicial": ["saldo inicial", "sdo inicial", "saldo anterior", "saldo abertura"],
    "debito": ["debito", "mov debito", "total debito"],
    "credito": ["credito", "mov credito", "total credito"],
    "saldo_final": ["saldo final", "sdo final", "saldo atual", "saldo encerramento"],
}


def detectar_encoding(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            path.read_text(encoding=encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def limpar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    novo = df.copy()
    novo.columns = [slug(col) if str(col).strip() else f"coluna_{idx+1}" for idx, col in enumerate(df.columns)]
    novo = novo.dropna(axis=1, how="all")
    novo = novo.dropna(axis=0, how="all")
    return novo.reset_index(drop=True)


def _pontuar_tabela(df: pd.DataFrame) -> tuple[int, int]:
    linhas = len(df.index)
    colunas = len(df.columns)
    return colunas, linhas


def carregar_balancete_txt(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    encoding = detectar_encoding(path)
    metadata: dict[str, Any] = {"arquivo": str(path), "encoding": encoding, "metodo_leitura": ""}

    candidates: list[tuple[tuple[int, int], pd.DataFrame, str]] = []
    for sep, nome in [(";", "csv_ponto_virgula"), ("|", "csv_pipe"), ("\t", "csv_tab")]:
        try:
            df = pd.read_csv(path, sep=sep, encoding=encoding, dtype=str)
            df = limpar_dataframe(df)
            if len(df.columns) > 1 and len(df.index) > 0:
                candidates.append((_pontuar_tabela(df), df, nome))
        except Exception:
            continue

    if candidates:
        _, melhor_df, metodo = sorted(candidates, key=lambda item: item[0], reverse=True)[0]
        metadata["metodo_leitura"] = metodo
        return melhor_df, metadata

    raw_lines = path.read_text(encoding=encoding).splitlines()
    lines = [line.rstrip() for line in raw_lines if line.strip()]
    parsed = [re.split(r"\s{2,}", line.strip()) for line in lines]
    max_len = max((len(parts) for parts in parsed), default=0)

    if max_len >= 4:
        header_like = parsed[0]
        header_is_text = sum(any(ch.isalpha() for ch in part) for part in header_like) >= max_len - 1
        if header_is_text:
            header = [slug(part) if part else f"coluna_{idx+1}" for idx, part in enumerate(header_like)]
            rows = [parts + [""] * (max_len - len(parts)) for parts in parsed[1:]]
        else:
            header = [f"coluna_{idx+1}" for idx in range(max_len)]
            rows = [parts + [""] * (max_len - len(parts)) for parts in parsed]
        df = pd.DataFrame(rows, columns=header)
        df = limpar_dataframe(df)
        metadata["metodo_leitura"] = "layout_multiplo_espaco"
        return df, metadata

    regex = re.compile(
        r"^\s*(?P<conta>[\d\.\-]+)\s+(?P<descricao>.+?)\s+(?P<valor_1>-?[\d\.,]+)(?:\s+(?P<valor_2>-?[\d\.,]+))?(?:\s+(?P<valor_3>-?[\d\.,]+))?(?:\s+(?P<valor_4>-?[\d\.,]+))?\s*$"
    )
    rows = []
    for line in lines:
        match = regex.match(line)
        if match:
            rows.append(match.groupdict())

    if rows:
        df = limpar_dataframe(pd.DataFrame(rows))
        metadata["metodo_leitura"] = "regex_posicional"
        return df, metadata

    metadata["metodo_leitura"] = "linha_bruta"
    return pd.DataFrame({"linha_original": lines}), metadata


def perfilar_abas_excel(path: Path) -> tuple[list[dict[str, Any]], pd.ExcelFile]:
    excel = pd.ExcelFile(path)
    perfil: list[dict[str, Any]] = []
    for aba in excel.sheet_names:
        preview = pd.read_excel(excel, sheet_name=aba, dtype=str, nrows=10)
        preview = limpar_dataframe(preview)
        perfil.append(
            {
                "aba": aba,
                "linhas_preview": len(preview.index),
                "colunas_preview": len(preview.columns),
                "colunas_detectadas": ", ".join(str(col) for col in preview.columns[:12]),
            }
        )
    return perfil, excel


def escolher_aba_transacoes(
    perfil_abas: list[dict[str, Any]], config: dict[str, Any]
) -> str:
    aba_configurada = str(config.get("planilha_transacoes", "")).strip()
    if aba_configurada:
        return aba_configurada

    melhores: list[tuple[int, str]] = []
    palavras = {"lanc", "trans", "mov", "razao", "diario", "contab"}
    for item in perfil_abas:
        base = normalizar_texto(item["aba"])
        score = sum(1 for palavra in palavras if palavra in base)
        if "debito" in item["colunas_detectadas"] or "credito" in item["colunas_detectadas"]:
            score += 3
        if "data" in item["colunas_detectadas"]:
            score += 2
        melhores.append((score, item["aba"]))

    melhores.sort(reverse=True)
    return melhores[0][1] if melhores else ""


def carregar_transacoes_excel(
    path: Path, config: dict[str, Any]
) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    perfil_abas, excel = perfilar_abas_excel(path)
    aba_escolhida = escolher_aba_transacoes(perfil_abas, config)
    df = pd.read_excel(excel, sheet_name=aba_escolhida or 0, dtype=str)
    df = limpar_dataframe(df)
    metadata = {"arquivo": str(path), "aba_escolhida": aba_escolhida or excel.sheet_names[0]}
    return df, perfil_abas, metadata


def mapear_colunas(
    df: pd.DataFrame, synonyms: dict[str, list[str]], manual_mapping: dict[str, str]
) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    colunas_normalizadas = {normalizar_texto(col): col for col in df.columns}
    rename_map: dict[str, str] = {}
    faltantes: list[str] = []

    for canonica, original in manual_mapping.items():
        original_limpa = str(original).strip()
        if original_limpa and original_limpa in df.columns:
            rename_map[original_limpa] = canonica

    for canonica, apelidos in synonyms.items():
        if canonica in rename_map.values():
            continue
        encontrado = None
        for apelido in apelidos:
            chave = normalizar_texto(apelido)
            if chave in colunas_normalizadas:
                encontrado = colunas_normalizadas[chave]
                break
        if encontrado:
            rename_map[encontrado] = canonica
        else:
            faltantes.append(canonica)

    mapeado = df.rename(columns=rename_map).copy()
    return mapeado, rename_map, faltantes


def converter_numero_serie(valor: Any) -> float | None:
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    texto = re.sub(r"[R$\s]", "", texto)
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def normalizar_tipos_transacoes(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    if "data_lancamento" in base.columns:
        base["data_lancamento"] = pd.to_datetime(
            base["data_lancamento"], errors="coerce", dayfirst=True
        )

    for coluna in ("debito", "credito", "valor"):
        if coluna in base.columns:
            base[coluna] = base[coluna].apply(converter_numero_serie)

    if "debito" not in base.columns and "valor" in base.columns and "tipo_dc" in base.columns:
        dc = base["tipo_dc"].astype(str).str.upper().str.strip()
        base["debito"] = base["valor"].where(dc.isin(["D", "DB", "DEBITO", "DEBIT"]), 0.0)
        base["credito"] = base["valor"].where(dc.isin(["C", "CR", "CREDITO", "CREDIT"]), 0.0)

    if "debito" in base.columns:
        base["debito"] = base["debito"].fillna(0.0)
    if "credito" in base.columns:
        base["credito"] = base["credito"].fillna(0.0)

    return base


def normalizar_tipos_balancete(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    for coluna in ("saldo_inicial", "debito", "credito", "saldo_final", "valor_1", "valor_2", "valor_3", "valor_4"):
        if coluna in base.columns:
            base[coluna] = base[coluna].apply(converter_numero_serie)
    return base


def preparar_balancete(
    df: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    manual = config.get("colunas_balancete", {})
    mapeado, rename_map, faltantes = mapear_colunas(df, TRIAL_BALANCE_SYNONYMS, manual)
    return normalizar_tipos_balancete(mapeado), rename_map, faltantes


def preparar_transacoes(
    df: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    manual = config.get("colunas_transacoes", {})
    mapeado, rename_map, faltantes = mapear_colunas(df, TRANSACTION_SYNONYMS, manual)
    return normalizar_tipos_transacoes(mapeado), rename_map, faltantes
