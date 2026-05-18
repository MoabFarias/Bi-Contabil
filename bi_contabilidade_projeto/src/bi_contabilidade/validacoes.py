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


def _serie_texto(df: pd.DataFrame, coluna: str, zfill: int | None = None) -> pd.Series:
    if coluna not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="string")
    serie = df[coluna].astype("string").str.strip()
    serie = serie.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    if zfill is not None:
        serie = serie.str.zfill(zfill)
    return serie


def _tem_prefixo(valor: str, prefixos: list[str]) -> bool:
    return any(valor.startswith(prefixo) for prefixo in prefixos)


def secao_informativa(titulo: str, resumo: str, indicadores: list[dict[str, Any]] | None = None) -> SecaoValidacao:
    return SecaoValidacao(titulo=titulo, resumo=resumo, indicadores=indicadores or [], tabela=[])


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
    return SecaoValidacao(
        titulo=f"Qualidade de extração - {nome}",
        resumo=resumo,
        indicadores=indicadores,
        tabela=tabela,
    )


def validar_transacoes(df: pd.DataFrame) -> list[SecaoValidacao]:
    secoes: list[SecaoValidacao] = []

    debitos = _serie_numerica(df, "debito").fillna(0.0)
    creditos = _serie_numerica(df, "credito").fillna(0.0)
    total_debito = float(debitos.sum())
    total_credito = float(creditos.sum())
    diferenca = round(total_debito - total_credito, 2)

    secoes.append(
        SecaoValidacao(
            titulo="Fechamento global das transações",
            resumo=(
                "Reconciliação geral das transações. "
                f"A diferença consolidada entre débitos e créditos é {diferenca:.2f}."
            ),
            indicadores=[
                {"indicador": "Total débito", "valor": round(total_debito, 2)},
                {"indicador": "Total crédito", "valor": round(total_credito, 2)},
                {"indicador": "Diferença débito-crédito", "valor": diferenca},
            ],
            tabela=[],
        )
    )

    if "valor_liquido" in df.columns:
        valor_liquido = _serie_numerica(df, "valor_liquido").fillna(0.0)
        diferencas = (debitos - creditos).round(2) != valor_liquido.round(2)
        amostra = df.loc[diferencas, [c for c in ["id_lancamento", "conta_contabil", "debito", "credito", "valor_liquido", "documento"] if c in df.columns]].head(100)
        secoes.append(
            SecaoValidacao(
                titulo="Consistência do valor líquido",
                resumo=(
                    "Verificação da regra `valor_liquido = débito - crédito` "
                    f"nas transações carregadas. Divergências encontradas: {int(diferencas.sum())}."
                ),
                indicadores=[
                    {"indicador": "Valor líquido total", "valor": round(float(valor_liquido.sum()), 2)},
                    {"indicador": "Linhas divergentes", "valor": int(diferencas.sum())},
                ],
                tabela=amostra.to_dict(orient="records"),
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
        tabela = inconsistentes.head(100).rename(columns={"_deb": "debito", "_cred": "credito"}).to_dict(orient="records")
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
        colunas_tabela = [
            col
            for col in [
                "codigo_reduzido",
                "conta_contabil",
                "descricao_conta",
                "saldo_inicial",
                "debito",
                "credito",
                "saldo_final",
                "saldo_calculado",
                "diferenca",
            ]
            if col in divergentes.columns
        ]
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
            df[
                [c for c in ["codigo_reduzido", "conta_contabil", "descricao_conta", "saldo_inicial", "debito", "credito", "saldo_final"] if c in df.columns]
            ]
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


def validar_conciliacao_cruzada(balancete: pd.DataFrame, transacoes: pd.DataFrame) -> list[SecaoValidacao]:
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
        comparativo = mov_bal.merge(
            mov_tx,
            on="conta_contabil",
            how="outer",
            suffixes=("_balancete", "_transacoes"),
        ).fillna(0.0)
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


def validar_modelo_contabil(modelo: dict[str, pd.DataFrame]) -> list[SecaoValidacao]:
    secoes: list[SecaoValidacao] = []

    fato = modelo.get("fato_lancamento_contabil")
    if fato is None or fato.empty:
        return secoes

    tabela_modelo = []
    for nome, df in modelo.items():
        tabela_modelo.append({"tabela": nome, "linhas": int(len(df.index)), "colunas": int(len(df.columns))})
    secoes.append(
        SecaoValidacao(
            titulo="Inventário da base analítica",
            resumo="Contagem das tabelas oficiais carregadas a partir do arquivo de transações contábeis.",
            indicadores=[
                {"indicador": "Tabelas detectadas", "valor": len(modelo)},
                {"indicador": "Linhas fato", "valor": int(len(fato.index))},
            ],
            tabela=tabela_modelo,
        )
    )

    dim_conta = modelo.get("dim_conta")
    dim_cc = modelo.get("dim_centro_custo")
    dim_conta_aux = modelo.get("dim_conta_aux")
    dim_item_aux = modelo.get("dim_item_conta_aux")
    param_bp_dre = modelo.get("param_bp_dre")
    mapa_custo = modelo.get("dim_custo_producao_mapa")

    if dim_conta is not None:
        contas_fato = set(_serie_texto(fato, "conta_contabil").dropna())
        contas_dim = set(_serie_texto(dim_conta, "conta").dropna())
        contas_fora = sorted(contas_fato - contas_dim)
        secoes.append(
            SecaoValidacao(
                titulo="Integridade de contas contábeis",
                resumo="Validação das contas da fato contra a dimensão de contas.",
                indicadores=[
                    {"indicador": "Contas na fato", "valor": len(contas_fato)},
                    {"indicador": "Contas fora da dimensão", "valor": len(contas_fora)},
                ],
                tabela=[{"conta_contabil": conta} for conta in contas_fora[:100]],
            )
        )

        if "usa_conta_aux" in dim_conta.columns:
            fato_dim = fato.copy()
            fato_dim["conta_contabil_n"] = _serie_texto(fato_dim, "conta_contabil")
            dim_aux = dim_conta[["conta", "usa_conta_aux"]].copy()
            dim_aux["conta_n"] = _serie_texto(dim_aux, "conta")
            dim_aux["usa_conta_aux_n"] = _serie_texto(dim_aux, "usa_conta_aux").str.upper()
            fato_dim = fato_dim.merge(dim_aux[["conta_n", "usa_conta_aux_n"]], left_on="conta_contabil_n", right_on="conta_n", how="left")
            exige_aux = fato_dim["usa_conta_aux_n"].eq("S")
            sem_cnt_aux = fato_dim[exige_aux & _serie_texto(fato_dim, "conta_auxiliar").isna()]
            sem_item_aux = fato_dim[exige_aux & _serie_texto(fato_dim, "item_conta_auxiliar").isna()]
            secoes.append(
                SecaoValidacao(
                    titulo="Obrigatoriedade de conta auxiliar",
                    resumo="Verificação das contas marcadas na dimensão como obrigatórias para conta auxiliar.",
                    indicadores=[
                        {"indicador": "Linhas que exigem conta auxiliar", "valor": int(exige_aux.sum())},
                        {"indicador": "Sem CNT_AUX", "valor": int(len(sem_cnt_aux.index))},
                        {"indicador": "Sem ITEM_CNTAUX", "valor": int(len(sem_item_aux.index))},
                    ],
                    tabela=sem_cnt_aux[[c for c in ["id_lancamento", "conta_contabil", "descricao", "documento"] if c in sem_cnt_aux.columns]].head(50).to_dict(orient="records"),
                )
            )

    if dim_conta_aux is not None and {"empresa", "conta", "cnt_aux", "cod_versao"}.issubset(dim_conta_aux.columns):
        fato_aux = fato.copy()
        fato_aux["sk_conta_aux"] = (
            _serie_texto(fato_aux, "empresa", zfill=2).fillna("")
            + "|"
            + _serie_texto(fato_aux, "conta_contabil").fillna("")
            + "|"
            + _serie_texto(fato_aux, "conta_auxiliar", zfill=2).fillna("")
            + "|"
            + _serie_texto(fato_aux, "versao").fillna("")
        )
        dim_conta_aux = dim_conta_aux.copy()
        dim_conta_aux["sk_conta_aux"] = (
            _serie_texto(dim_conta_aux, "empresa", zfill=2).fillna("")
            + "|"
            + _serie_texto(dim_conta_aux, "conta").fillna("")
            + "|"
            + _serie_texto(dim_conta_aux, "cnt_aux", zfill=2).fillna("")
            + "|"
            + _serie_texto(dim_conta_aux, "cod_versao").fillna("")
        )
        fato_com_aux = fato_aux[_serie_texto(fato_aux, "conta_auxiliar").notna()]
        faltantes = sorted(set(fato_com_aux["sk_conta_aux"]) - set(dim_conta_aux["sk_conta_aux"]))
        secoes.append(
            SecaoValidacao(
                titulo="Relacionamento Fato x DimContaAux",
                resumo="Validação da chave empresa + conta + conta auxiliar + versão contra a dimensão de conta auxiliar.",
                indicadores=[
                    {"indicador": "Linhas fato com CNT_AUX", "valor": int(len(fato_com_aux.index))},
                    {"indicador": "Chaves fora da dimensão", "valor": len(faltantes)},
                ],
                tabela=[{"sk_conta_aux": valor} for valor in faltantes[:100]],
            )
        )

    if dim_item_aux is not None and {"empresa", "cnt_aux", "item_cntaux"}.issubset(dim_item_aux.columns):
        fato_item = fato.copy()
        fato_item["sk_item_aux"] = (
            _serie_texto(fato_item, "empresa", zfill=2).fillna("")
            + "|"
            + _serie_texto(fato_item, "conta_auxiliar", zfill=2).fillna("")
            + "|"
            + _serie_texto(fato_item, "item_conta_auxiliar").fillna("")
        )
        dim_item_aux = dim_item_aux.copy()
        dim_item_aux["sk_item_aux"] = (
            _serie_texto(dim_item_aux, "empresa", zfill=2).fillna("")
            + "|"
            + _serie_texto(dim_item_aux, "cnt_aux", zfill=2).fillna("")
            + "|"
            + _serie_texto(dim_item_aux, "item_cntaux").fillna("")
        )
        fato_com_item = fato_item[_serie_texto(fato_item, "item_conta_auxiliar").notna()]
        faltantes = sorted(set(fato_com_item["sk_item_aux"]) - set(dim_item_aux["sk_item_aux"]))
        secoes.append(
            SecaoValidacao(
                titulo="Relacionamento Fato x DimItemContaAux",
                resumo="Validação da chave empresa + conta auxiliar + item auxiliar contra a dimensão de item auxiliar.",
                indicadores=[
                    {"indicador": "Linhas fato com ITEM_CNTAUX", "valor": int(len(fato_com_item.index))},
                    {"indicador": "Chaves fora da dimensão", "valor": len(faltantes)},
                ],
                tabela=[{"sk_item_aux": valor} for valor in faltantes[:100]],
            )
        )

    if dim_cc is not None and "ccusto" in dim_cc.columns:
        fato_34 = fato[_serie_texto(fato, "conta_contabil").fillna("").str.startswith(("3", "4"))].copy()
        cc_validos = set(_serie_texto(dim_cc, "ccusto").dropna())
        cc_fora = sorted(set(_serie_texto(fato_34, "centro_custo").dropna()) - cc_validos)
        cc_vazio = fato_34[_serie_texto(fato_34, "centro_custo").isna()]
        secoes.append(
            SecaoValidacao(
                titulo="Centro de custo nas contas 3 e 4",
                resumo="Validação de centro de custo para contas de resultado e custo.",
                indicadores=[
                    {"indicador": "Linhas com conta 3 ou 4", "valor": int(len(fato_34.index))},
                    {"indicador": "CCusto vazio", "valor": int(len(cc_vazio.index))},
                    {"indicador": "CCusto fora da dimensão", "valor": len(cc_fora)},
                ],
                tabela=cc_vazio[[c for c in ["id_lancamento", "conta_contabil", "descricao", "documento"] if c in cc_vazio.columns]].head(50).to_dict(orient="records"),
            )
        )

    if param_bp_dre is not None and "conta_sintetica" in param_bp_dre.columns:
        prefixos = _serie_texto(param_bp_dre, "conta_sintetica").dropna().drop_duplicates().tolist()
        contas_fato = sorted(set(_serie_texto(fato, "conta_contabil").dropna()))
        contas_relevantes = [conta for conta in contas_fato if conta.startswith(("1", "2", "3", "4"))]
        sem_classificacao = [conta for conta in contas_relevantes if not _tem_prefixo(conta, prefixos)]
        secoes.append(
            SecaoValidacao(
                titulo="Cobertura de classificação BP/DRE",
                resumo="Verificação de cobertura por prefixo das contas operacionais e patrimoniais no mapa BP/DRE.",
                indicadores=[
                    {"indicador": "Prefixos ParamBP_DRE", "valor": len(prefixos)},
                    {"indicador": "Contas 1 a 4 na fato", "valor": len(contas_relevantes)},
                    {"indicador": "Contas sem classificação", "valor": len(sem_classificacao)},
                ],
                tabela=[{"conta_contabil": conta} for conta in sem_classificacao[:100]],
            )
        )

    if mapa_custo is not None and "conta" in mapa_custo.columns:
        contas_mapa = set(_serie_texto(mapa_custo, "conta").dropna())
        movimento = (_serie_numerica(fato, "debito").fillna(0.0).abs() + _serie_numerica(fato, "credito").fillna(0.0).abs()) > 0.01
        fato_custo = fato[movimento & _serie_texto(fato, "conta_contabil").fillna("").str.startswith("4")]
        contas_custo = sorted(set(_serie_texto(fato_custo, "conta_contabil").dropna()))
        sem_mapa = sorted(set(contas_custo) - contas_mapa)
        secoes.append(
            SecaoValidacao(
                titulo="Cobertura do mapa de custo de produção",
                resumo="Validação das contas 4 com movimento contra o mapa de custo de produção.",
                indicadores=[
                    {"indicador": "Contas 4 com movimento", "valor": len(contas_custo)},
                    {"indicador": "Contas 4 sem mapa", "valor": len(sem_mapa)},
                ],
                tabela=[{"conta_contabil": conta} for conta in sem_mapa[:100]],
            )
        )

    return secoes
