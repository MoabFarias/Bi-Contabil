import json
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "config.json"
LOGS_DIR = ROOT_DIR / "logs"
OUTPUT_PATH = LOGS_DIR / "validacao_modelo.json"


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


def serie_codigo_2(serie: pd.Series) -> pd.Series:
    return serie_normalizada(serie).str.zfill(2)


def carregar_excel() -> dict[str, pd.DataFrame]:
    config = carregar_configuracao()
    caminho = Path(config["base_path"]) / config["arquivo_principal"]

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    return pd.read_excel(caminho, sheet_name=None)


def possui_prefixo(conta: str, prefixos: list[str]) -> bool:
    return any(conta.startswith(prefixo) for prefixo in prefixos)


def validar_modelo() -> dict:
    abas = carregar_excel()

    fato = abas["FatoLancamentoContabil"].copy()
    dim_conta = abas["DimConta"].copy()
    dim_cc = abas["DimCentroCusto"].copy()
    dim_item_aux = abas["DimItemContaAux"].copy()
    dim_conta_aux = abas["DimContaAux"].copy()
    param_bp_dre = abas["ParamBP_DRE"].copy()
    mapa_custo = abas["Dim_CUSTO_PRODUCAO_MAPA"].copy()

    fato["CONTA_N"] = serie_normalizada(fato["CONTA"])
    fato["CCUSTO_N"] = serie_normalizada(fato["CCUSTO"])
    fato["CNT_AUX_N"] = serie_codigo_2(fato["CNT_AUX"])
    fato["ITEM_CNTAUX_N"] = serie_normalizada(fato["ITEM_CNTAUX"])
    fato["EMPRESA_N"] = serie_codigo_2(fato["EMPRESA"])
    fato["COD_VERSAO_N"] = serie_normalizada(fato["COD_VERSAO"])

    dim_conta["CONTA_N"] = serie_normalizada(dim_conta["CONTA"])
    dim_conta["USA_CONTA_AUX_N"] = serie_normalizada(dim_conta["USA_CONTA_AUX"]).str.upper()

    dim_cc["CCUSTO_N"] = serie_normalizada(dim_cc["CCUSTO"])

    dim_conta_aux["EMPRESA_N"] = serie_codigo_2(dim_conta_aux["EMPRESA"])
    dim_conta_aux["CONTA_N"] = serie_normalizada(dim_conta_aux["CONTA"])
    dim_conta_aux["CNT_AUX_N"] = serie_codigo_2(dim_conta_aux["CNT_AUX"])
    dim_conta_aux["COD_VERSAO_N"] = serie_normalizada(dim_conta_aux["COD_VERSAO"])

    dim_item_aux["EMPRESA_N"] = serie_codigo_2(dim_item_aux["EMPRESA"])
    dim_item_aux["CNT_AUX_N"] = serie_codigo_2(dim_item_aux["CNT_AUX"])
    dim_item_aux["ITEM_CNTAUX_N"] = serie_normalizada(dim_item_aux["ITEM_CNTAUX"])

    param_bp_dre["CONTA_SINTETICA_N"] = serie_normalizada(param_bp_dre["conta_sintetica"])
    mapa_custo["CONTA_N"] = serie_normalizada(mapa_custo["CONTA"])

    # 1. Conta da fato contra DimConta
    contas_fato = set(fato["CONTA_N"].dropna())
    contas_dim = set(dim_conta["CONTA_N"].dropna())
    contas_fora_dim = sorted(contas_fato - contas_dim)

    # 2. Conta auxiliar obrigatória apenas quando DimConta.USA_CONTA_AUX = S
    fato_dim = fato.merge(
        dim_conta[["CONTA_N", "USA_CONTA_AUX_N"]],
        on="CONTA_N",
        how="left",
    )

    exige_aux = fato_dim["USA_CONTA_AUX_N"].eq("S")
    sem_cnt_aux = fato_dim[exige_aux & fato_dim["CNT_AUX_N"].isna()]
    sem_item_aux = fato_dim[exige_aux & fato_dim["ITEM_CNTAUX_N"].isna()]

    # 3. Validação CONTA + CNT_AUX contra DimContaAux
    fato_com_aux = fato_dim[fato_dim["CNT_AUX_N"].notna()].copy()

    fato_com_aux["SK_CONTA_AUX_CHECK"] = (
        fato_com_aux["EMPRESA_N"]
        + "|"
        + fato_com_aux["CONTA_N"]
        + "|"
        + fato_com_aux["CNT_AUX_N"]
        + "|"
        + fato_com_aux["COD_VERSAO_N"]
    )

    dim_conta_aux["SK_CONTA_AUX_CHECK"] = (
        dim_conta_aux["EMPRESA_N"]
        + "|"
        + dim_conta_aux["CONTA_N"]
        + "|"
        + dim_conta_aux["CNT_AUX_N"]
        + "|"
        + dim_conta_aux["COD_VERSAO_N"]
    )

    sk_conta_aux_fora = sorted(
        set(fato_com_aux["SK_CONTA_AUX_CHECK"].dropna())
        - set(dim_conta_aux["SK_CONTA_AUX_CHECK"].dropna())
    )

    # 4. Validação CNT_AUX + ITEM_CNTAUX contra DimItemContaAux
    fato_com_aux["SK_ITEM_CNTAUX_CHECK"] = (
        fato_com_aux["EMPRESA_N"]
        + "|"
        + fato_com_aux["CNT_AUX_N"]
        + "|"
        + fato_com_aux["ITEM_CNTAUX_N"]
    )

    dim_item_aux["SK_ITEM_CNTAUX_CHECK"] = (
        dim_item_aux["EMPRESA_N"]
        + "|"
        + dim_item_aux["CNT_AUX_N"]
        + "|"
        + dim_item_aux["ITEM_CNTAUX_N"]
    )

    sk_item_aux_fora = sorted(
        set(fato_com_aux["SK_ITEM_CNTAUX_CHECK"].dropna())
        - set(dim_item_aux["SK_ITEM_CNTAUX_CHECK"].dropna())
    )

    # 5. Centro de custo apenas para contas 3 e 4
    fato_3_4 = fato[fato["CONTA_N"].str.startswith(("3", "4"), na=False)].copy()
    cc_validos = set(dim_cc["CCUSTO_N"].dropna())

    cc_fora_dim = sorted(set(fato_3_4["CCUSTO_N"].dropna()) - cc_validos)
    cc_vazio_3_4 = fato_3_4[fato_3_4["CCUSTO_N"].isna()]

    # 6. ParamBP_DRE por prefixo
    prefixos_bp_dre = param_bp_dre["CONTA_SINTETICA_N"].dropna().drop_duplicates().tolist()

    contas_123 = sorted([c for c in contas_fato if c.startswith(("1", "2", "3"))])
    contas_123_sem_param = sorted(
        [c for c in contas_123 if not possui_prefixo(c, prefixos_bp_dre)]
    )

    # 7. Mapa de custo: contas 4 com movimento e sem mapa
    contas_4_fato = sorted([c for c in contas_fato if c.startswith("4")])
    contas_4_mapa = set(mapa_custo["CONTA_N"].dropna())
    contas_4_sem_mapa = sorted(set(contas_4_fato) - contas_4_mapa)

    # 8. Valor líquido
    deb = pd.to_numeric(fato["VALOR_DEB"], errors="coerce").fillna(0)
    cre = pd.to_numeric(fato["VALOR_CRE"], errors="coerce").fillna(0)
    liq = pd.to_numeric(fato["VALOR_LIQ"], errors="coerce").fillna(0)

    divergencia_valor = (deb - cre).round(2) != liq.round(2)

    resultado = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resumo_linhas": {
            "FatoLancamentoContabil": int(len(fato)),
            "DimConta": int(len(dim_conta)),
            "DimCentroCusto": int(len(dim_cc)),
            "DimItemContaAux": int(len(dim_item_aux)),
            "DimContaAux": int(len(dim_conta_aux)),
            "ParamBP_DRE": int(len(param_bp_dre)),
            "Dim_CUSTO_PRODUCAO_MAPA": int(len(mapa_custo)),
        },
        "validacao_valores": {
            "total_debitos": float(deb.sum()),
            "total_creditos": float(cre.sum()),
            "total_valor_liquido": float(liq.sum()),
            "qtd_divergencias_valor_liq": int(divergencia_valor.sum()),
        },
        "validacao_estrutura": {
            "codlanc_vazio": int(fato["CODLANC"].isna().sum()),
            "conta_vazia": int(fato["CONTA"].isna().sum()),
            "datas_invalidas": int(pd.to_datetime(fato["LDATA"], errors="coerce").isna().sum()),
            "docno_vazio": int(fato["DOCNO"].isna().sum()) if "DOCNO" in fato.columns else None,
            "cod_secundario_desconsiderado": True,
        },
        "relacionamentos": {
            "contas_fato_fora_dimconta": {
                "qtd": len(contas_fora_dim),
                "amostra": contas_fora_dim[:100],
            },
            "contas_que_exigem_aux_sem_cnt_aux": {
                "qtd_linhas": int(len(sem_cnt_aux)),
                "amostra_codlanc": sem_cnt_aux["CODLANC"].head(50).astype(str).tolist(),
            },
            "contas_que_exigem_aux_sem_item_aux": {
                "qtd_linhas": int(len(sem_item_aux)),
                "amostra_codlanc": sem_item_aux["CODLANC"].head(50).astype(str).tolist(),
            },
            "sk_conta_aux_fora_dimcontaaux": {
                "qtd": len(sk_conta_aux_fora),
                "amostra": sk_conta_aux_fora[:100],
            },
            "sk_item_aux_fora_dimitemcontaaux": {
                "qtd": len(sk_item_aux_fora),
                "amostra": sk_item_aux_fora[:100],
            },
            "ccusto_3_4_fora_dimcentrocusto": {
                "qtd": len(cc_fora_dim),
                "amostra": cc_fora_dim[:100],
            },
            "ccusto_vazio_em_contas_3_4": {
                "qtd_linhas": int(len(cc_vazio_3_4)),
                "amostra_codlanc": cc_vazio_3_4["CODLANC"].head(50).astype(str).tolist(),
            },
            "contas_1_2_3_sem_param_bp_dre_por_prefixo": {
                "qtd": len(contas_123_sem_param),
                "amostra": contas_123_sem_param[:100],
            },
            "contas_4_com_movimento_sem_mapa_custo": {
                "qtd": len(contas_4_sem_mapa),
                "amostra": contas_4_sem_mapa[:100],
            },
        },
    }

    return resultado


if __name__ == "__main__":
    resultado = validar_modelo()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(resultado, arquivo, ensure_ascii=False, indent=4)

    print(json.dumps(resultado, ensure_ascii=False, indent=4))