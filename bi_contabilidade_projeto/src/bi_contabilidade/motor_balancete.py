import json
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "config.json"
OUTPUT_DIR = ROOT_DIR / "outputs"
LOGS_DIR = ROOT_DIR / "logs"
BALANCETE_XLSX = OUTPUT_DIR / "balancete_mensal.xlsx"
BALANCETE_JSON = LOGS_DIR / "balancete_resumo.json"


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
        raise FileNotFoundError(f"Arquivo principal não encontrado: {caminho}")

    return pd.read_excel(caminho, sheet_name=None)


def classificar_relatorio(conta: str) -> str:
    if conta.startswith("1") or conta.startswith("2"):
        return "BP"

    if conta.startswith("3"):
        return "DRE"

    if conta.startswith("4"):
        return "CUSTO_PRODUCAO"

    return "NAO_CLASSIFICADO"


def nivel_conta(conta: str) -> int:
    return len(str(conta).split("."))


def tratar_ccusto(row):
    ccusto = row.get("CCUSTO_N")
    conta = row.get("CONTA_N")

    if ccusto is not None and str(ccusto) != "<NA>":
        return ccusto

    if isinstance(conta, str) and conta.startswith("3"):
        return "ADMINISTRACAO"

    if isinstance(conta, str) and conta.startswith("4"):
        return "PRODUCAO"

    return None


def origem_ccusto(row) -> str:
    ccusto = row.get("CCUSTO_N")
    conta = row.get("CONTA_N")

    if ccusto is not None and str(ccusto) != "<NA>":
        return "ERP"

    if isinstance(conta, str) and conta.startswith(("3", "4")):
        return "REGRA_AUTOMATICA"

    return "NAO_APLICAVEL"


def montar_fato_tratada(fato: pd.DataFrame) -> pd.DataFrame:
    fato = fato.copy()

    fato["CONTA_N"] = serie_normalizada(fato["CONTA"])
    fato["CCUSTO_N"] = serie_normalizada(fato["CCUSTO"])
    fato["PERIODO"] = pd.to_datetime(fato["LDATA"], errors="coerce").dt.to_period("M").astype(str)

    fato["VALOR_DEB_N"] = pd.to_numeric(fato["VALOR_DEB"], errors="coerce").fillna(0)
    fato["VALOR_CRE_N"] = pd.to_numeric(fato["VALOR_CRE"], errors="coerce").fillna(0)
    fato["VALOR_LIQ_N"] = pd.to_numeric(fato["VALOR_LIQ"], errors="coerce").fillna(0)

    fato["CCUSTO_TRATADO"] = fato.apply(tratar_ccusto, axis=1)
    fato["ORIGEM_CCUSTO"] = fato.apply(origem_ccusto, axis=1)
    fato["RELATORIO_BASE"] = fato["CONTA_N"].map(classificar_relatorio)

    return fato


def obter_limite_visualizacao(config: dict) -> str | None:
    limite_config = config.get("limite_visualizacao", {})

    if not limite_config.get("usar_limite_automatico", False):
        return None

    meses_futuros = int(limite_config.get("meses_futuros_permitidos", 2))
    hoje = pd.Timestamp.today().normalize()
    limite = hoje + pd.DateOffset(months=meses_futuros)
    return limite.strftime("%Y-%m")


def aplicar_limite_visualizacao(fato: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, dict]:
    periodos_total = sorted(fato["PERIODO"].dropna().unique().tolist())
    limite_periodo = obter_limite_visualizacao(config)

    if limite_periodo is None:
        fato_filtrada = fato.copy()
        modo_limite = "SEM_LIMITE"
    else:
        fato_filtrada = fato[fato["PERIODO"] <= limite_periodo].copy()
        modo_limite = "AUTOMATICO_MES_ATUAL_MAIS_FUTUROS"

    periodos_visualizacao = sorted(fato_filtrada["PERIODO"].dropna().unique().tolist())

    metadados = {
        "modo_limite_visualizacao": modo_limite,
        "limite_periodo_visualizacao": limite_periodo,
        "periodo_total_carregado_inicio": periodos_total[0] if periodos_total else None,
        "periodo_total_carregado_fim": periodos_total[-1] if periodos_total else None,
        "periodo_visualizacao_inicio": periodos_visualizacao[0] if periodos_visualizacao else None,
        "periodo_visualizacao_fim": periodos_visualizacao[-1] if periodos_visualizacao else None,
        "periodos_total_carregados": periodos_total,
        "periodos_visualizados": periodos_visualizacao,
        "linhas_fato_total_carregadas": int(len(fato)),
        "linhas_fato_visualizadas": int(len(fato_filtrada)),
        "linhas_fato_ocultadas_por_periodo": int(len(fato) - len(fato_filtrada)),
    }

    return fato_filtrada, metadados


def enriquecer_com_dim_conta(balancete: pd.DataFrame, dim_conta: pd.DataFrame) -> pd.DataFrame:
    dim = dim_conta.copy()
    dim["CONTA_N"] = serie_normalizada(dim["CONTA"])

    colunas_dim = [
        "CONTA_N",
        "DESCRICAO",
        "NATUREZA",
        "TIPO",
        "CLASSE_CONTA",
        "IND_ATIVA",
        "USA_CONTA_AUX",
    ]

    colunas_dim = [col for col in colunas_dim if col in dim.columns]

    return balancete.merge(dim[colunas_dim], on="CONTA_N", how="left")


def aplicar_param_bp_dre(balancete: pd.DataFrame, param: pd.DataFrame) -> pd.DataFrame:
    param = param.copy()

    param["CONTA_SINTETICA_N"] = serie_normalizada(param["conta_sintetica"])
    param = param[param["ativa"].astype(str).str.upper().eq("S")].copy()

    param = param.sort_values(
        "CONTA_SINTETICA_N",
        key=lambda s: s.str.len(),
        ascending=False,
    )

    parametros = param.to_dict(orient="records")

    def buscar_param(conta: str):
        for p in parametros:
            prefixo = p["CONTA_SINTETICA_N"]

            if conta.startswith(prefixo):
                return p

        return {}

    registros = []

    for conta in balancete["CONTA_N"]:
        registros.append(buscar_param(conta))

    param_df = pd.DataFrame(registros)
    param_df = param_df.add_prefix("PARAM_")

    return pd.concat(
        [balancete.reset_index(drop=True), param_df.reset_index(drop=True)],
        axis=1,
    )


def montar_balancete_mensal():
    config = carregar_configuracao()
    abas = carregar_excel()

    fato_total = montar_fato_tratada(abas["FatoLancamentoContabil"])
    fato, metadados_periodo = aplicar_limite_visualizacao(fato_total, config)
    dim_conta = abas["DimConta"]
    param = abas["ParamBP_DRE"]

    balancete = (
        fato.groupby(["PERIODO", "CONTA_N"], dropna=False)
        .agg(
            debito=("VALOR_DEB_N", "sum"),
            credito=("VALOR_CRE_N", "sum"),
            movimento=("VALOR_LIQ_N", "sum"),
            qtd_lancamentos=("CODLANC", "count"),
        )
        .reset_index()
    )

    balancete["nivel_conta"] = balancete["CONTA_N"].map(nivel_conta)
    balancete["relatorio_base"] = balancete["CONTA_N"].map(classificar_relatorio)

    balancete = enriquecer_com_dim_conta(balancete, dim_conta)
    balancete = aplicar_param_bp_dre(balancete, param)

    analitico_colunas = [
        "CODLANC",
        "PERIODO",
        "LDATA",
        "CONTA_N",
        "CCUSTO",
        "CCUSTO_TRATADO",
        "ORIGEM_CCUSTO",
        "CNT_AUX",
        "ITEM_CNTAUX",
        "VALOR_DEB_N",
        "VALOR_CRE_N",
        "VALOR_LIQ_N",
        "DOCNO",
        "DSC_COMPLEMENTO",
        "RELATORIO_BASE",
    ]

    analitico_colunas = [col for col in analitico_colunas if col in fato.columns]

    analitico = fato[analitico_colunas].copy()

    resumo = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **metadados_periodo,
        "periodos": sorted(balancete["PERIODO"].dropna().unique().tolist()),
        "qtd_linhas_balancete": int(len(balancete)),
        "qtd_linhas_analitico": int(len(analitico)),
        "total_debitos": float(balancete["debito"].sum()),
        "total_creditos": float(balancete["credito"].sum()),
        "total_movimento": float(balancete["movimento"].sum()),
        "linhas_ccusto_regra_automatica": int(
            (analitico["ORIGEM_CCUSTO"] == "REGRA_AUTOMATICA").sum()
        ),
    }

    return balancete, analitico, resumo


def salvar_outputs(balancete: pd.DataFrame, analitico: pd.DataFrame, resumo: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(BALANCETE_XLSX, engine="openpyxl") as writer:
        balancete.to_excel(writer, sheet_name="BalanceteMensal", index=False)
        analitico.to_excel(writer, sheet_name="AnaliticoLancamentos", index=False)

    with open(BALANCETE_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    balancete_df, analitico_df, resumo_execucao = montar_balancete_mensal()
    salvar_outputs(balancete_df, analitico_df, resumo_execucao)
    print(json.dumps(resumo_execucao, ensure_ascii=False, indent=4))