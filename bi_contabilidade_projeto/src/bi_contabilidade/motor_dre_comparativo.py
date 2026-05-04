import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.bi_contabilidade.motor_dre import carregar_excel, preparar_fato_dre

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "outputs"
LOGS_DIR = ROOT_DIR / "logs"
DRE_COMP_JSON = LOGS_DIR / "dre_comparativo.json"
DRE_COMP_XLSX = OUTPUT_DIR / "dre_comparativo.xlsx"


def variacao_percentual(base: float, comparacao: float) -> float | None:
    if comparacao == 0:
        return None
    return ((base - comparacao) / abs(comparacao)) * 100


def montar_comparativo(periodo_base: str | None = None, periodo_comparacao: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    abas = carregar_excel()
    fato = preparar_fato_dre(abas)

    periodos = sorted(fato["PERIODO"].dropna().unique().tolist())
    if len(periodos) < 2:
        raise ValueError("Nao ha periodos suficientes para montar comparativo de DRE.")

    if periodo_base is None:
        periodo_base = periodos[-1]
    if periodo_base not in periodos:
        raise ValueError(f"Periodo base {periodo_base} nao encontrado. Periodos disponiveis: {periodos}")

    if periodo_comparacao is None:
        idx_base = periodos.index(periodo_base)
        periodo_comparacao = periodos[idx_base - 1] if idx_base > 0 else periodos[0]
    if periodo_comparacao not in periodos:
        raise ValueError(f"Periodo comparacao {periodo_comparacao} nao encontrado. Periodos disponiveis: {periodos}")

    fato_base = fato[fato["PERIODO"] == periodo_base].copy()
    fato_comp = fato[fato["PERIODO"] == periodo_comparacao].copy()

    grupo_cols = [
        "PARAM_bloco",
        "PARAM_grupo",
        "PARAM_ordem_bloco",
        "PARAM_ordem_grupo",
        "PARAM_natureza",
        "PARAM_sinal",
    ]
    grupo_cols = [c for c in grupo_cols if c in fato.columns]

    base_grupo = (
        fato_base.groupby(grupo_cols, dropna=False)
        .agg(valor_base=("VALOR_GERENCIAL", "sum"), debito_base=("VALOR_DEB_N", "sum"), credito_base=("VALOR_CRE_N", "sum"), lancamentos_base=("CODLANC", "count"))
        .reset_index()
    )
    comp_grupo = (
        fato_comp.groupby(grupo_cols, dropna=False)
        .agg(valor_comparacao=("VALOR_GERENCIAL", "sum"), debito_comparacao=("VALOR_DEB_N", "sum"), credito_comparacao=("VALOR_CRE_N", "sum"), lancamentos_comparacao=("CODLANC", "count"))
        .reset_index()
    )

    comparativo_grupo = base_grupo.merge(comp_grupo, on=grupo_cols, how="outer").fillna(0)
    comparativo_grupo["periodo_base"] = periodo_base
    comparativo_grupo["periodo_comparacao"] = periodo_comparacao
    comparativo_grupo["variacao_valor"] = comparativo_grupo["valor_base"] - comparativo_grupo["valor_comparacao"]
    comparativo_grupo["variacao_percentual"] = comparativo_grupo.apply(lambda r: variacao_percentual(float(r["valor_base"]), float(r["valor_comparacao"])), axis=1)

    conta_cols = grupo_cols + ["CONTA_N", "DESCRICAO"]
    base_conta = (
        fato_base.groupby(conta_cols, dropna=False)
        .agg(valor_base=("VALOR_GERENCIAL", "sum"), debito_base=("VALOR_DEB_N", "sum"), credito_base=("VALOR_CRE_N", "sum"), lancamentos_base=("CODLANC", "count"))
        .reset_index()
    )
    comp_conta = (
        fato_comp.groupby(conta_cols, dropna=False)
        .agg(valor_comparacao=("VALOR_GERENCIAL", "sum"), debito_comparacao=("VALOR_DEB_N", "sum"), credito_comparacao=("VALOR_CRE_N", "sum"), lancamentos_comparacao=("CODLANC", "count"))
        .reset_index()
    )

    comparativo_conta = base_conta.merge(comp_conta, on=conta_cols, how="outer").fillna(0)
    comparativo_conta["periodo_base"] = periodo_base
    comparativo_conta["periodo_comparacao"] = periodo_comparacao
    comparativo_conta["variacao_valor"] = comparativo_conta["valor_base"] - comparativo_conta["valor_comparacao"]
    comparativo_conta["variacao_percentual"] = comparativo_conta.apply(lambda r: variacao_percentual(float(r["valor_base"]), float(r["valor_comparacao"])), axis=1)

    linhas_json = []
    ordenado = comparativo_grupo.sort_values(["PARAM_ordem_bloco", "PARAM_ordem_grupo", "PARAM_bloco", "PARAM_grupo"], na_position="last")
    for _, row in ordenado.iterrows():
        filtro = pd.Series([True] * len(comparativo_conta))
        for col in grupo_cols:
            filtro &= comparativo_conta[col].astype("string").fillna("").eq(str(row.get(col, "")))
        contas = comparativo_conta[filtro].sort_values("variacao_valor", key=lambda s: s.abs(), ascending=False).head(80)
        linhas_json.append({
            "bloco": row.get("PARAM_bloco"),
            "grupo": row.get("PARAM_grupo"),
            "valor_base": float(row.get("valor_base", 0) or 0),
            "valor_comparacao": float(row.get("valor_comparacao", 0) or 0),
            "variacao_valor": float(row.get("variacao_valor", 0) or 0),
            "variacao_percentual": None if pd.isna(row.get("variacao_percentual")) else float(row.get("variacao_percentual")),
            "lancamentos_base": int(row.get("lancamentos_base", 0) or 0),
            "lancamentos_comparacao": int(row.get("lancamentos_comparacao", 0) or 0),
            "contas": [
                {
                    "conta": c.get("CONTA_N"),
                    "descricao": c.get("DESCRICAO"),
                    "valor_base": float(c.get("valor_base", 0) or 0),
                    "valor_comparacao": float(c.get("valor_comparacao", 0) or 0),
                    "variacao_valor": float(c.get("variacao_valor", 0) or 0),
                    "variacao_percentual": None if pd.isna(c.get("variacao_percentual")) else float(c.get("variacao_percentual")),
                    "lancamentos_base": int(c.get("lancamentos_base", 0) or 0),
                    "lancamentos_comparacao": int(c.get("lancamentos_comparacao", 0) or 0),
                }
                for _, c in contas.iterrows()
            ],
        })

    resumo = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modo": "mensal",
        "periodo_base": periodo_base,
        "periodo_comparacao": periodo_comparacao,
        "periodos_disponiveis": periodos,
        "qtd_linhas_grupo": int(len(comparativo_grupo)),
        "qtd_linhas_conta": int(len(comparativo_conta)),
        "valor_total_base": float(comparativo_grupo["valor_base"].sum()),
        "valor_total_comparacao": float(comparativo_grupo["valor_comparacao"].sum()),
        "variacao_total": float(comparativo_grupo["variacao_valor"].sum()),
        "linhas": linhas_json,
    }

    return comparativo_grupo, comparativo_conta, resumo


def salvar(grupo: pd.DataFrame, conta: pd.DataFrame, resumo: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(DRE_COMP_XLSX, engine="openpyxl") as writer:
        grupo.to_excel(writer, sheet_name="Comparativo_Grupos", index=False)
        conta.to_excel(writer, sheet_name="Comparativo_Contas", index=False)
    with open(DRE_COMP_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera comparativo mensal da DRE.")
    parser.add_argument("--base", dest="periodo_base", default=None, help="Periodo base no formato YYYY-MM. Exemplo: 2026-01")
    parser.add_argument("--comparacao", dest="periodo_comparacao", default=None, help="Periodo de comparacao no formato YYYY-MM. Exemplo: 2025-01")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    grupo_df, conta_df, resumo_execucao = montar_comparativo(args.periodo_base, args.periodo_comparacao)
    salvar(grupo_df, conta_df, resumo_execucao)
    print(json.dumps({k: v for k, v in resumo_execucao.items() if k != "linhas"}, ensure_ascii=False, indent=4))
