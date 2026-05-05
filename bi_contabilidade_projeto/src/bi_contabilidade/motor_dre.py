import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "config.json"
OUTPUT_DIR = ROOT_DIR / "outputs"
LOGS_DIR = ROOT_DIR / "logs"
DRE_XLSX = OUTPUT_DIR / "dre_gerencial.xlsx"
DRE_JSON = LOGS_DIR / "dre_resumo.json"
DRE_DETALHE_JSON = LOGS_DIR / "dre_detalhe.json"
TIPOS_LANCAMENTO_EXCLUIR_DRE = {"EF"}


def carregar_configuracao() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def normalizar_texto(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    if texto in ["", "nan", "NaN", "None", "<NA>"]:
        return None
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def serie_normalizada(serie: pd.Series) -> pd.Series:
    return serie.map(normalizar_texto).astype("string")


def carregar_excel() -> dict[str, pd.DataFrame]:
    config = carregar_configuracao()
    caminho = Path(config["base_path"]) / config["arquivo_principal"]
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo principal nao encontrado: {caminho}")
    return pd.read_excel(caminho, sheet_name=None)


def obter_limite_visualizacao(config: dict) -> str | None:
    limite_config = config.get("limite_visualizacao", {})
    if not limite_config.get("usar_limite_automatico", False):
        return None
    meses_futuros = int(limite_config.get("meses_futuros_permitidos", 2))
    limite = pd.Timestamp.today().normalize() + pd.DateOffset(months=meses_futuros)
    return limite.strftime("%Y-%m")


def possui_prefixo(conta: str, prefixo: str) -> bool:
    return str(conta).startswith(str(prefixo))


def aplicar_param_dre(fato: pd.DataFrame, param: pd.DataFrame) -> pd.DataFrame:
    param = param.copy()
    param["CONTA_SINTETICA_N"] = serie_normalizada(param["conta_sintetica"])
    param = param[param["ativa"].astype(str).str.upper().eq("S")].copy()
    param = param[param["relatorio"].astype(str).str.upper().eq("DRE")].copy()
    param = param.sort_values("CONTA_SINTETICA_N", key=lambda s: s.str.len(), ascending=False)
    parametros = param.to_dict(orient="records")

    def buscar(conta):
        for p in parametros:
            if possui_prefixo(conta, p["CONTA_SINTETICA_N"]):
                return p
        return {}

    registros = [buscar(conta) for conta in fato["CONTA_N"]]
    param_df = pd.DataFrame(registros).add_prefix("PARAM_")
    return pd.concat([fato.reset_index(drop=True), param_df.reset_index(drop=True)], axis=1)


def preparar_fato_dre(abas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    config = carregar_configuracao()
    fato = abas["FatoLancamentoContabil"].copy()
    dim_conta = abas["DimConta"].copy()
    param = abas["ParamBP_DRE"].copy()

    fato["CONTA_N"] = serie_normalizada(fato["CONTA"])
    fato["PERIODO"] = pd.to_datetime(fato["LDATA"], errors="coerce").dt.to_period("M").astype(str)
    fato["VALOR_DEB_N"] = pd.to_numeric(fato["VALOR_DEB"], errors="coerce").fillna(0)
    fato["VALOR_CRE_N"] = pd.to_numeric(fato["VALOR_CRE"], errors="coerce").fillna(0)
    fato["VALOR_LIQ_N"] = pd.to_numeric(fato["VALOR_LIQ"], errors="coerce").fillna(0)

    qtd_antes_tipo = len(fato)
    tipos_excluidos_encontrados = {}
    if "CTIPO" in fato.columns:
        fato["CTIPO_N"] = serie_normalizada(fato["CTIPO"]).str.upper()
        mascara_excluir = fato["CTIPO_N"].isin(TIPOS_LANCAMENTO_EXCLUIR_DRE)
        tipos_excluidos_encontrados = fato.loc[mascara_excluir, "CTIPO_N"].value_counts(dropna=False).to_dict()
        fato = fato.loc[~mascara_excluir].copy()
    fato.attrs["qtd_lancamentos_excluidos_tipo_dre"] = qtd_antes_tipo - len(fato)
    fato.attrs["tipos_lancamento_excluidos_dre"] = tipos_excluidos_encontrados

    limite = obter_limite_visualizacao(config)
    if limite:
        fato = fato[fato["PERIODO"] <= limite].copy()

    # DRE usa contas 3. Conta 4 fica fora da DRE direta; impacto aparece via CPV na conta 3.
    fato = fato[fato["CONTA_N"].str.startswith("3", na=False)].copy()

    dim_conta["CONTA_N"] = serie_normalizada(dim_conta["CONTA"])
    colunas_dim = ["CONTA_N", "DESCRICAO", "NATUREZA", "TIPO", "CLASSE_CONTA"]
    colunas_dim = [c for c in colunas_dim if c in dim_conta.columns]
    fato = fato.merge(dim_conta[colunas_dim], on="CONTA_N", how="left")
    fato = aplicar_param_dre(fato, param)

    sinal = fato.get("PARAM_sinal")
    if sinal is not None:
        sinal_norm = sinal.astype("string").str.upper()
        fato["VALOR_GERENCIAL"] = fato["VALOR_LIQ_N"]
        fato.loc[sinal_norm.eq("C"), "VALOR_GERENCIAL"] = -fato.loc[sinal_norm.eq("C"), "VALOR_LIQ_N"]
    else:
        fato["VALOR_GERENCIAL"] = fato["VALOR_LIQ_N"]

    return fato


def montar_dre() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    abas = carregar_excel()
    fato = preparar_fato_dre(abas)

    grupo_cols = ["PARAM_bloco", "PARAM_grupo", "PARAM_ordem_bloco", "PARAM_ordem_grupo", "PARAM_natureza", "PARAM_sinal"]
    grupo_cols = [c for c in grupo_cols if c in fato.columns]

    dre = fato.groupby(["PERIODO"] + grupo_cols, dropna=False).agg(valor=("VALOR_GERENCIAL", "sum"), debito=("VALOR_DEB_N", "sum"), credito=("VALOR_CRE_N", "sum"), qtd_lancamentos=("CODLANC", "count")).reset_index()
    conta = fato.groupby(["PERIODO"] + grupo_cols + ["CONTA_N", "DESCRICAO"], dropna=False).agg(valor=("VALOR_GERENCIAL", "sum"), debito=("VALOR_DEB_N", "sum"), credito=("VALOR_CRE_N", "sum"), qtd_lancamentos=("CODLANC", "count")).reset_index()

    detalhe_cols = ["CODLANC", "PERIODO", "LDATA", "CONTA_N", "DESCRICAO", "DOCNO", "DSC_COMPLEMENTO", "CTIPO", "VALOR_DEB_N", "VALOR_CRE_N", "VALOR_LIQ_N", "VALOR_GERENCIAL"] + grupo_cols
    detalhe_cols = [c for c in detalhe_cols if c in fato.columns]
    detalhe = fato[detalhe_cols].copy()

    periodos = sorted(fato["PERIODO"].dropna().unique().tolist())
    resumo = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "periodo_inicio": periodos[0] if periodos else None,
        "periodo_fim": periodos[-1] if periodos else None,
        "periodos": periodos,
        "qtd_linhas_dre": int(len(dre)),
        "qtd_contas_analiticas": int(conta["CONTA_N"].nunique()) if not conta.empty else 0,
        "qtd_lancamentos_dre": int(len(detalhe)),
        "qtd_lancamentos_excluidos_tipo_dre": int(fato.attrs.get("qtd_lancamentos_excluidos_tipo_dre", 0)),
        "tipos_lancamento_excluidos_dre": fato.attrs.get("tipos_lancamento_excluidos_dre", {}),
        "valor_total_dre": float(dre["valor"].sum()) if not dre.empty else 0.0,
    }

    detalhe_json = {"grupos": []}
    for _, row in dre.sort_values(["PARAM_ordem_bloco", "PARAM_ordem_grupo", "PARAM_bloco", "PARAM_grupo"], na_position="last").iterrows():
        filtro = conta["PERIODO"] == row["PERIODO"]
        if "PARAM_grupo" in conta.columns:
            filtro &= conta["PARAM_grupo"].astype("string").fillna("").eq(str(row.get("PARAM_grupo", "")))
        contas = conta[filtro].sort_values("valor", key=lambda s: s.abs(), ascending=False).head(80)
        detalhe_json["grupos"].append({"periodo": row.get("PERIODO"), "bloco": row.get("PARAM_bloco"), "grupo": row.get("PARAM_grupo"), "valor": float(row.get("valor", 0) or 0), "contas": [{"conta": c.get("CONTA_N"), "descricao": c.get("DESCRICAO"), "valor": float(c.get("valor", 0) or 0), "debito": float(c.get("debito", 0) or 0), "credito": float(c.get("credito", 0) or 0), "qtd_lancamentos": int(c.get("qtd_lancamentos", 0) or 0)} for _, c in contas.iterrows()]})

    return dre, detalhe, resumo, detalhe_json


def salvar(dre: pd.DataFrame, detalhe: pd.DataFrame, resumo: dict, detalhe_json: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(DRE_XLSX, engine="openpyxl") as writer:
        dre.to_excel(writer, sheet_name="DRE_Grupos", index=False)
        detalhe.to_excel(writer, sheet_name="DRE_Analitico", index=False)
    with open(DRE_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=4)
    with open(DRE_DETALHE_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(detalhe_json, arquivo, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    dre_df, detalhe_df, resumo_execucao, detalhe_execucao = montar_dre()
    salvar(dre_df, detalhe_df, resumo_execucao, detalhe_execucao)
    print(json.dumps(resumo_execucao, ensure_ascii=False, indent=4))
