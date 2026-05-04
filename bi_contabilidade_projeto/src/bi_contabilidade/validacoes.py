from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class SecaoValidacao:
    titulo: str
    resumo: str
    indicadores: list[dict[str, Any]]
    tabela: list[dict[str, Any]]


def _serie_numerica(df: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[coluna], errors="coerce")


def validar_extracao(nome: str, df: pd.DataFrame, obrigatorias: list[str]) -> SecaoValidacao:
    total_linhas = len(df.index)
    total_colunas = len(df.columns)
    colunas_ausentes = [col for col in obrigatorias if col not in df.columns]

    indicadores = [
        {"indicador": "Linhas", "valor": total_linhas},
        {"indicador": "Colunas", "valor": total_colunas},
        {"indicador": "Colunas obrigatórias ausentes", "valor": len(colunas_ausentes)},
    ]

    tabela: list[dict[str, Any]] = []
    for coluna in df.columns:
        serie = df[coluna]
        nulos = int(serie.isna().sum()) + int((serie.astype(str).str.strip() == "").sum())
        tabela.append(
            {
                "coluna": coluna,
                "nulos": nulos,
                "percentual_nulos": round((nulos / total_linhas) * 100, 2) if total_linhas else 0,
                "distintos": int(serie.nunique(dropna=True)),
            }
        )

    resumo = (
        f"{nome}: {total_linhas} linhas e {total_colunas} colunas. "
        f"Ausências obrigatórias detectadas: {', '.join(colunas_ausentes) if colunas_ausentes else 'nenhuma'}."
    )
    return SecaoValidacao(titulo=f"Qualidade de extração - {nome}", resumo=resumo, indicadores=indicadores, tabela=tabela)


def validar_transacoes(df: pd.DataFrame) -> list[SecaoValidacao]:
    secoes: list[SecaoValidacao] = []

    debitos = _serie_numerica(df, "debito").fillna(0.0)
    creditos = _serie_numerica(df, "credito").fillna(0.0)
    total_debito = float(debitos.sum())
    total_credito = float(creditos.sum())
    diferenca = round(total_debito - total_credito, 2)

    indicadores = [
        {"indicador": "Total débito", "valor": round(total_debito, 2)},
        {"indicador": "Total crédito", "valor": round(total_credito, 2)},
        {"indicador": "Diferença débito-crédito", "valor": diferenca},
    ]

    resumo = (
        "Reconciliação geral das transações. "
        f"A diferença consolidada entre débitos e créditos é {diferenca:.2f}."
    )
    secoes.append(
        SecaoValidacao(
            titulo="Fechamento global das transações",
            resumo=resumo,
            indicadores=indicadores,
            tabela=[],
        )
    )

    if "id_lancamento" in df.columns:
        por_lancamento = (
            df.assign(_deb=debitos, _cred=creditos)
            .groupby("id_lancamento", dropna=False)[["_deb", "_cred"]]
            .sum()
            .reset_index()
        )
        por_lancamento["diferenca"] = (por_lancamento["_deb"] - por_lancamento["_cred"]).round(2)
        inconsistentes = por_lancamento[por_lancamento["diferenca"].abs() > 0.01].copy()
        tabela = inconsistentes.head(100).rename(
            columns={"_deb": "debito", "_cred": "credito"}
        ).to_dict(orient="records")
        secoes.append(
            SecaoValidacao(
                titulo="Lançamentos não fechados",
                resumo=(
                    f"Foram encontrados {len(inconsistentes.index)} lançamentos com diferença "
                    "entre débito e crédito acima de 0,01."
                ),
                indicadores=[
                    {"indicador": "Lançamentos avaliados", "valor": int(len(por_lancamento.index))},
                    {"indicador": "Lançamentos com diferença", "valor": int(len(inconsistentes.index))},
                ],
                tabela=tabela,
            )
        )

    if "conta_contabil" in df.columns:
        por_conta = (
            df.assign(_deb=debitos, _cred=creditos)
            .groupby("conta_contabil", dropna=False)[["_deb", "_cred"]]
            .sum()
            .reset_index()
        )
        por_conta["movimento_liquido"] = (por_conta["_deb"] - por_conta["_cred"]).round(2)
        tabela = (
            por_conta.sort_values("movimento_liquido", key=lambda s: s.abs(), ascending=False)
            .head(30)
            .rename(columns={"_deb": "debito", "_cred": "credito"})
            .to_dict(orient="records")
        )
        secoes.append(
            SecaoValidacao(
                titulo="Maiores movimentos por conta",
                resumo="Ranking das contas com maior impacto líquido no período.",
                indicadores=[{"indicador": "Contas analisadas", "valor": int(len(por_conta.index))}],
                tabela=tabela,
            )
        )

    if "data_lancamento" in df.columns:
        datas_invalidas = int(df["data_lancamento"].isna().sum())
        secoes.append(
            SecaoValidacao(
                titulo="Datas das transações",
                resumo=f"Foram identificadas {datas_invalidas} linhas com data inválida ou não reconhecida.",
                indicadores=[
                    {"indicador": "Datas inválidas", "valor": datas_invalidas},
                    {
                        "indicador": "Data mínima",
                        "valor": str(df["data_lancamento"].min()) if not df["data_lancamento"].dropna().empty else "",
                    },
                    {
                        "indicador": "Data máxima",
                        "valor": str(df["data_lancamento"].max()) if not df["data_lancamento"].dropna().empty else "",
                    },
                ],
                tabela=[],
            )
        )

    return secoes


def validar_balancete(df: pd.DataFrame) -> list[SecaoValidacao]:
    secoes: list[SecaoValidacao] = []

    colunas_base = {"saldo_inicial", "debito", "credito", "saldo_final"}
    if colunas_base.issubset(df.columns):
        base = df.copy()
        base["calc_convencao_1"] = (
            base["saldo_inicial"].fillna(0.0)
            + base["debito"].fillna(0.0)
            - base["credito"].fillna(0.0)
        )
        base["calc_convencao_2"] = (
            base["saldo_inicial"].fillna(0.0)
            - base["debito"].fillna(0.0)
            + base["credito"].fillna(0.0)
        )
        erro_1 = (base["calc_convencao_1"] - base["saldo_final"].fillna(0.0)).abs().mean()
        erro_2 = (base["calc_convencao_2"] - base["saldo_final"].fillna(0.0)).abs().mean()

        if erro_1 <= erro_2:
            formula = "saldo_inicial + debito - credito"
            base["saldo_calculado"] = base["calc_convencao_1"]
        else:
            formula = "saldo_inicial - debito + credito"
            base["saldo_calculado"] = base["calc_convencao_2"]

        base["diferenca"] = (base["saldo_calculado"] - base["saldo_final"].fillna(0.0)).round(2)
        divergentes = base[base["diferenca"].abs() > 0.01].copy()
        colunas_tabela = [col for col in ["conta_contabil", "descricao_conta", "saldo_inicial", "debito", "credito", "saldo_final", "saldo_calculado", "diferenca"] if col in divergentes.columns]
        secoes.append(
            SecaoValidacao(
                titulo="Coerência do balancete",
                resumo=(
                    "Validação entre saldo inicial, movimentação e saldo final. "
                    f"A convenção de sinal mais aderente foi: {formula}."
                ),
                indicadores=[
                    {"indicador": "Linhas avaliadas", "valor": int(len(base.index))},
                    {"indicador": "Linhas divergentes", "valor": int(len(divergentes.index))},
                    {"indicador": "Erro médio absoluto", "valor": round(min(erro_1, erro_2), 2)},
                ],
                tabela=divergentes[colunas_tabela].head(100).to_dict(orient="records"),
            )
        )

    if "conta_contabil" in df.columns:
        tabela = (
            df[["conta_contabil"] + [c for c in ["descricao_conta", "saldo_inicial", "debito", "credito", "saldo_final"] if c in df.columns]]
            .head(50)
            .to_dict(orient="records")
        )
        secoes.append(
            SecaoValidacao(
                titulo="Prévia das contas do balancete",
                resumo="Amostra inicial das contas após a padronização do arquivo.",
                indicadores=[{"indicador": "Contas carregadas", "valor": int(len(df.index))}],
                tabela=tabela,
            )
        )

    return secoes


def validar_conciliacao_cruzada(
    balancete: pd.DataFrame, transacoes: pd.DataFrame
) -> list[SecaoValidacao]:
    secoes: list[SecaoValidacao] = []

    if {"debito", "credito"}.issubset(transacoes.columns) and {"debito", "credito"}.issubset(balancete.columns):
        total_tx_debito = float(_serie_numerica(transacoes, "debito").fillna(0.0).sum())
        total_tx_credito = float(_serie_numerica(transacoes, "credito").fillna(0.0).sum())
        total_bal_debito = float(_serie_numerica(balancete, "debito").fillna(0.0).sum())
        total_bal_credito = float(_serie_numerica(balancete, "credito").fillna(0.0).sum())

        secoes.append(
            SecaoValidacao(
                titulo="Conciliação entre transações e balancete",
                resumo="Comparação consolidada do movimento encontrado nas transações versus o movimento acumulado no balancete.",
                indicadores=[
                    {"indicador": "Débito transações", "valor": round(total_tx_debito, 2)},
                    {"indicador": "Débito balancete", "valor": round(total_bal_debito, 2)},
                    {"indicador": "Diferença débito", "valor": round(total_tx_debito - total_bal_debito, 2)},
                    {"indicador": "Crédito transações", "valor": round(total_tx_credito, 2)},
                    {"indicador": "Crédito balancete", "valor": round(total_bal_credito, 2)},
                    {"indicador": "Diferença crédito", "valor": round(total_tx_credito - total_bal_credito, 2)},
                ],
                tabela=[],
            )
        )

    if "conta_contabil" in transacoes.columns and "conta_contabil" in balancete.columns:
        mov_tx = (
            transacoes.assign(
                deb=_serie_numerica(transacoes, "debito").fillna(0.0),
                cred=_serie_numerica(transacoes, "credito").fillna(0.0),
            )
            .groupby("conta_contabil", dropna=False)[["deb", "cred"]]
            .sum()
            .reset_index()
        )
        mov_bal = (
            balancete.assign(
                deb=_serie_numerica(balancete, "debito").fillna(0.0),
                cred=_serie_numerica(balancete, "credito").fillna(0.0),
            )
            .groupby("conta_contabil", dropna=False)[["deb", "cred"]]
            .sum()
            .reset_index()
        )
        comparativo = mov_bal.merge(mov_tx, on="conta_contabil", how="outer", suffixes=("_balancete", "_transacoes")).fillna(0.0)
        comparativo["dif_debito"] = (comparativo["deb_transacoes"] - comparativo["deb_balancete"]).round(2)
        comparativo["dif_credito"] = (comparativo["cred_transacoes"] - comparativo["cred_balancete"]).round(2)
        divergentes = comparativo[
            (comparativo["dif_debito"].abs() > 0.01) | (comparativo["dif_credito"].abs() > 0.01)
        ]
        secoes.append(
            SecaoValidacao(
                titulo="Diferenças por conta contábil",
                resumo=(
                    f"Foram encontradas {len(divergentes.index)} contas com diferença entre "
                    "o movimento das transações e o movimento do balancete."
                ),
                indicadores=[
                    {"indicador": "Contas comparadas", "valor": int(len(comparativo.index))},
                    {"indicador": "Contas divergentes", "valor": int(len(divergentes.index))},
                ],
                tabela=divergentes.head(100).to_dict(orient="records"),
            )
        )

    return secoes
