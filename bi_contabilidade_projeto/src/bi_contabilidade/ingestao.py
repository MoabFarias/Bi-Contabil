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
        "codlanc",
    ],
    "empresa": ["empresa"],
    "filial": ["filial"],
    "data_lancamento": ["data", "data lancamento", "dt lancamento", "data contabil", "ldata"],
    "conta_contabil": ["conta", "conta contabil", "cod conta", "codigo conta", "conta ctb"],
    "versao": ["versao", "cod versao", "codigo versao", "cod_versao"],
    "centro_custo": ["centro custo", "ccusto", "centro de custo", "cost center"],
    "conta_auxiliar": ["cnt aux", "conta auxiliar", "cnt_aux"],
    "item_conta_auxiliar": ["item cntaux", "item conta auxiliar", "item_cntaux"],
    "debito": ["debito", "valor debito", "vl debito", "deb", "valor deb", "valor_deb"],
    "credito": ["credito", "valor credito", "vl credito", "cred", "valor cre", "valor_cre"],
    "valor_liquido": ["valor liquido", "valor liq", "liquido", "valor_liq"],
    "descricao": ["historico", "descricao", "complemento", "detalhe", "texto", "dsc complemento", "dsc_complemento"],
    "documento": ["documento", "doc", "nf", "numero documento", "docno"],
    "codigo_origem": ["codorigem", "codigo origem"],
    "codigo_historico": ["codhist", "codigo historico"],
    "codigo_secundario": ["cod secundario", "codigo secundario", "cod_secundario"],
    "tipo_dc": ["dc", "tipo", "debito credito", "natureza", "dr cr", "ctipo"],
    "classe_conta": ["classe conta", "classe_conta"],
}

TRIAL_BALANCE_SYNONYMS = {
    "codigo_reduzido": ["reduzido", "codigo reduzido", "cod reduzido"],
    "conta_contabil": ["conta", "conta contabil", "codigo conta", "cod conta", "conta ctb"],
    "descricao_conta": ["descricao", "descricao conta", "conta descricao", "nome conta", "denominacao"],
    "saldo_inicial": ["saldo inicial", "sdo inicial", "saldo anterior", "saldo abertura"],
    "debito": ["debito", "mov debito", "total debito"],
    "credito": ["credito", "mov credito", "total credito"],
    "saldo_final": ["saldo final", "sdo final", "saldo atual", "saldo encerramento"],
}

MODEL_SHEET_ALIASES = {
    "fato_lancamento_contabil": ["FatoLancamentoContabil"],
    "dim_conta": ["DimConta"],
    "dim_centro_custo": ["DimCentroCusto"],
    "dim_item_conta_aux": ["DimItemContaAux"],
    "dim_conta_aux": ["DimContaAux"],
    "param_bp_dre": ["ParamBP_DRE"],
    "dim_custo_producao_mapa": ["Dim_CUSTO_PRODUCAO_MAPA"],
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
    return len(df.columns), len(df.index)


def _padronizar_brancos(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    for coluna in base.columns:
        if base[coluna].dtype == "object" or str(base[coluna].dtype).startswith("string"):
            base[coluna] = (
                base[coluna]
                .astype("string")
                .str.strip()
                .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
            )
    return base


def _resolver_planilha(config: dict[str, Any], canonical: str, sheet_names: list[str]) -> str:
    configuradas = config.get("planilhas_modelo", {})
    alvo = str(configuradas.get(canonical, "")).strip()
    if alvo and alvo in sheet_names:
        return alvo

    aliases = MODEL_SHEET_ALIASES.get(canonical, [])
    for alias in aliases:
        if alias in sheet_names:
            return alias

    names_normalized = {normalizar_texto(name): name for name in sheet_names}
    for alias in aliases:
        chave = normalizar_texto(alias)
        if chave in names_normalized:
            return names_normalized[chave]

    return ""


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
        metadata["metodo_leitura"] = "layout_multiplo_espaco"
        return limpar_dataframe(df), metadata

    regex = re.compile(
        r"^\s*(?P<conta>[\d\.\-]+)\s+(?P<descricao>.+?)\s+(?P<valor_1>-?[\d\.,]+)(?:\s+(?P<valor_2>-?[\d\.,]+))?(?:\s+(?P<valor_3>-?[\d\.,]+))?(?:\s+(?P<valor_4>-?[\d\.,]+))?\s*$"
    )
    rows = []
    for line in lines:
        match = regex.match(line)
        if match:
            rows.append(match.groupdict())

    if rows:
        metadata["metodo_leitura"] = "regex_posicional"
        return limpar_dataframe(pd.DataFrame(rows)), metadata

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


def escolher_aba_transacoes(perfil_abas: list[dict[str, Any]], config: dict[str, Any]) -> str:
    aba_configurada = str(config.get("planilha_transacoes", "")).strip()
    if aba_configurada:
        return aba_configurada

    for item in perfil_abas:
        if normalizar_texto(item["aba"]) == normalizar_texto("FatoLancamentoContabil"):
            return item["aba"]

    melhores: list[tuple[int, str]] = []
    palavras = {"lanc", "trans", "mov", "razao", "diario", "contab"}
    for item in perfil_abas:
        base = normalizar_texto(item["aba"])
        colunas = normalizar_texto(item["colunas_detectadas"])
        score = sum(1 for palavra in palavras if palavra in base)
        if "debito" in colunas or "credito" in colunas or "valor deb" in colunas or "valor cre" in colunas:
            score += 3
        if "data" in colunas or "ldata" in colunas:
            score += 2
        melhores.append((score, item["aba"]))

    melhores.sort(reverse=True)
    return melhores[0][1] if melhores else ""


def carregar_transacoes_excel(path: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    perfil_abas, excel = perfilar_abas_excel(path)
    aba_escolhida = escolher_aba_transacoes(perfil_abas, config)
    df = pd.read_excel(excel, sheet_name=aba_escolhida or 0, dtype=str)
    metadata = {"arquivo": str(path), "aba_escolhida": aba_escolhida or excel.sheet_names[0]}
    return limpar_dataframe(df), perfil_abas, metadata


def carregar_modelo_contabil_excel(path: Path, config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    excel = pd.ExcelFile(path)
    planilhas: dict[str, pd.DataFrame] = {}
    resolvidas: dict[str, str] = {}
    faltantes: list[str] = []

    for canonical in MODEL_SHEET_ALIASES:
        nome_planilha = _resolver_planilha(config, canonical, excel.sheet_names)
        if not nome_planilha:
            faltantes.append(canonical)
            continue
        df = pd.read_excel(excel, sheet_name=nome_planilha, dtype=str)
        planilhas[canonical] = limpar_dataframe(df)
        resolvidas[canonical] = nome_planilha

    metadata = {
        "arquivo": str(path),
        "planilhas_resolvidas": resolvidas,
        "planilhas_faltantes": faltantes,
        "modelo_detectado": "fato_lancamento_contabil" in planilhas and "dim_conta" in planilhas,
    }
    return planilhas, metadata


def mapear_colunas(df: pd.DataFrame, synonyms: dict[str, list[str]], manual_mapping: dict[str, str]) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
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

    return df.rename(columns=rename_map).copy(), rename_map, faltantes


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


def _parse_data_serie(serie: pd.Series) -> pd.Series:
    texto = serie.astype("string").str.strip()
    parsed_default = pd.to_datetime(texto, errors="coerce")
    parsed_dayfirst = pd.to_datetime(texto, errors="coerce", dayfirst=True)
    if parsed_dayfirst.notna().sum() > parsed_default.notna().sum():
        return parsed_dayfirst
    return parsed_default


def normalizar_tipos_transacoes(df: pd.DataFrame) -> pd.DataFrame:
    base = _padronizar_brancos(df)
    if "data_lancamento" in base.columns:
        base["data_lancamento"] = _parse_data_serie(base["data_lancamento"])

    for coluna in ("debito", "credito", "valor_liquido"):
        if coluna in base.columns:
            base[coluna] = base[coluna].apply(converter_numero_serie)

    if "debito" not in base.columns and "valor_liquido" in base.columns and "tipo_dc" in base.columns:
        dc = base["tipo_dc"].astype("string").str.upper().str.strip()
        base["debito"] = base["valor_liquido"].where(dc.isin(["D", "DB", "DEBITO", "DEBIT"]), 0.0)
        base["credito"] = base["valor_liquido"].where(dc.isin(["C", "CR", "CREDITO", "CREDIT"]), 0.0)

    if "debito" in base.columns:
        base["debito"] = base["debito"].fillna(0.0)
    if "credito" in base.columns:
        base["credito"] = base["credito"].fillna(0.0)

    return base


def normalizar_tipos_balancete(df: pd.DataFrame) -> pd.DataFrame:
    base = _padronizar_brancos(df)
    for coluna in ("saldo_inicial", "debito", "credito", "saldo_final", "valor_1", "valor_2", "valor_3", "valor_4"):
        if coluna in base.columns:
            base[coluna] = base[coluna].apply(converter_numero_serie)
    return base


def preparar_balancete(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    manual = config.get("colunas_balancete", {})
    mapeado, rename_map, faltantes = mapear_colunas(df, TRIAL_BALANCE_SYNONYMS, manual)
    return normalizar_tipos_balancete(mapeado), rename_map, faltantes


def preparar_transacoes(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    manual = config.get("colunas_transacoes", {})
    mapeado, rename_map, faltantes = mapear_colunas(df, TRANSACTION_SYNONYMS, manual)
    return normalizar_tipos_transacoes(mapeado), rename_map, faltantes


def preparar_modelo_contabil(
    planilhas: dict[str, pd.DataFrame], config: dict[str, Any]
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    preparado: dict[str, pd.DataFrame] = {}
    metadata: dict[str, Any] = {
        "mapeamento_fato": {},
        "faltantes_fato": [],
        "tabelas": {},
    }

    fato = planilhas.get("fato_lancamento_contabil")
    if fato is not None:
        fato_prep, mapeamento, faltantes = preparar_transacoes(fato, config)
        preparado["fato_lancamento_contabil"] = fato_prep
        preparado["transacoes_normalizadas"] = fato_prep.copy()
        metadata["mapeamento_fato"] = mapeamento
        metadata["faltantes_fato"] = faltantes

    for nome, df in planilhas.items():
        if nome == "fato_lancamento_contabil":
            continue
        preparado[nome] = _padronizar_brancos(df)
        metadata["tabelas"][nome] = list(preparado[nome].columns)

    return preparado, metadata
