from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .configuracao import carregar_config
from .ingestao import (
    carregar_balancete_txt,
    carregar_modelo_contabil_excel,
    carregar_transacoes_excel,
    preparar_balancete,
    preparar_modelo_contabil,
    preparar_transacoes,
)
from .relatorio_html import renderizar_index, renderizar_pagina_secao
from .validacoes import (
    secao_informativa,
    validar_balancete,
    validar_conciliacao_cruzada,
    validar_extracao,
    validar_modelo_contabil,
    validar_transacoes,
)


def _garantir_diretorios(saida_dir: Path) -> dict[str, Path]:
    dados_tratados = saida_dir / "dados_tratados"
    saida_dir.mkdir(parents=True, exist_ok=True)
    dados_tratados.mkdir(parents=True, exist_ok=True)
    return {"saida": saida_dir, "dados_tratados": dados_tratados}


def _exportar_csv(df: pd.DataFrame, destino: Path) -> None:
    df.to_csv(destino, index=False, encoding="utf-8-sig")


def _detectar_periodo_balancete(path: Path) -> dict[str, Any]:
    match = re.search(r"(\d{1,2})[-_](\d{4})", path.name)
    if not match:
        return {"mes": None, "ano": None, "periodo": ""}
    mes = int(match.group(1))
    ano = int(match.group(2))
    return {"mes": mes, "ano": ano, "periodo": f"{ano:04d}-{mes:02d}"}


def _detectar_periodo_transacoes(transacoes: pd.DataFrame) -> dict[str, Any]:
    if "data_lancamento" not in transacoes.columns or transacoes["data_lancamento"].dropna().empty:
        return {"data_min": "", "data_max": "", "periodos": []}
    datas = pd.to_datetime(transacoes["data_lancamento"], errors="coerce").dropna()
    periodos = sorted(datas.dt.to_period("M").astype(str).unique().tolist())
    return {
        "data_min": str(datas.min()),
        "data_max": str(datas.max()),
        "periodos": periodos,
    }


def _comparacao_periodo_habilitada(balancete_path: Path, transacoes: pd.DataFrame) -> tuple[bool, dict[str, Any]]:
    periodo_bal = _detectar_periodo_balancete(balancete_path)
    periodo_tx = _detectar_periodo_transacoes(transacoes)
    periodo_bal_str = periodo_bal.get("periodo", "")
    periodos_tx = periodo_tx.get("periodos", [])
    habilitada = bool(periodo_bal_str and periodos_tx and periodo_bal_str in periodos_tx)
    return habilitada, {"balancete": periodo_bal, "transacoes": periodo_tx}


def _montar_contrato_base_analitica(
    balancete: pd.DataFrame,
    transacoes: pd.DataFrame,
    modelo: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    tabelas = {
        "BalanceteNormalizado": list(balancete.columns),
        "FatoLancamentoContabil": list(modelo.get("fato_lancamento_contabil", transacoes).columns),
        "DimConta": list(modelo.get("dim_conta", pd.DataFrame()).columns),
        "DimCentroCusto": list(modelo.get("dim_centro_custo", pd.DataFrame()).columns),
        "DimContaAux": list(modelo.get("dim_conta_aux", pd.DataFrame()).columns),
        "DimItemContaAux": list(modelo.get("dim_item_conta_aux", pd.DataFrame()).columns),
        "ParamBP_DRE": list(modelo.get("param_bp_dre", pd.DataFrame()).columns),
        "Dim_CUSTO_PRODUCAO_MAPA": list(modelo.get("dim_custo_producao_mapa", pd.DataFrame()).columns),
    }
    return {
        "tabelas_oficiais": tabelas,
        "arquivos_saida": [
            "dados_tratados/balancete_normalizado.csv",
            "dados_tratados/transacoes_normalizadas.csv",
            "dados_tratados/fato_lancamento_contabil.csv",
            "dados_tratados/dim_conta.csv",
            "dados_tratados/dim_centro_custo.csv",
            "dados_tratados/dim_conta_aux.csv",
            "dados_tratados/dim_item_conta_aux.csv",
            "dados_tratados/param_bp_dre.csv",
            "dados_tratados/dim_custo_producao_mapa.csv",
            "perfil_abas_transacoes.csv",
            "resumo_execucao.json",
            "contrato_base_analitica.json",
            "index.html",
            "validacao_extracoes.html",
            "validacao_numerica.html",
            "validacao_modelo.html",
        ],
    }


def executar_pipeline(
    balancete_path: Path,
    transacoes_path: Path,
    config_path: Path,
    saida_dir: Path,
) -> dict[str, Any]:
    diretorios = _garantir_diretorios(saida_dir)
    config = carregar_config(config_path)

    balancete_raw, meta_balancete = carregar_balancete_txt(balancete_path)
    transacoes_raw, perfil_abas, meta_transacoes = carregar_transacoes_excel(transacoes_path, config)
    planilhas_modelo_raw, meta_modelo_raw = carregar_modelo_contabil_excel(transacoes_path, config)

    balancete, mapeamento_balancete, faltantes_balancete = preparar_balancete(balancete_raw, config)
    transacoes, mapeamento_transacoes, faltantes_transacoes = preparar_transacoes(transacoes_raw, config)
    modelo, meta_modelo = preparar_modelo_contabil(planilhas_modelo_raw, config)

    _exportar_csv(balancete, diretorios["dados_tratados"] / "balancete_normalizado.csv")
    _exportar_csv(transacoes, diretorios["dados_tratados"] / "transacoes_normalizadas.csv")
    if "fato_lancamento_contabil" in modelo:
        _exportar_csv(modelo["fato_lancamento_contabil"], diretorios["dados_tratados"] / "fato_lancamento_contabil.csv")

    export_map = {
        "dim_conta": "dim_conta.csv",
        "dim_centro_custo": "dim_centro_custo.csv",
        "dim_conta_aux": "dim_conta_aux.csv",
        "dim_item_conta_aux": "dim_item_conta_aux.csv",
        "param_bp_dre": "param_bp_dre.csv",
        "dim_custo_producao_mapa": "dim_custo_producao_mapa.csv",
    }
    for nome, arquivo in export_map.items():
        if nome in modelo:
            _exportar_csv(modelo[nome], diretorios["dados_tratados"] / arquivo)

    pd.DataFrame(perfil_abas).to_csv(
        diretorios["saida"] / "perfil_abas_transacoes.csv",
        index=False,
        encoding="utf-8-sig",
    )

    comparacao_habilitada, info_periodo = _comparacao_periodo_habilitada(
        balancete_path,
        modelo.get("fato_lancamento_contabil", transacoes),
    )

    secoes_extracao = [
        validar_extracao(
            "Balancete",
            balancete,
            ["conta_contabil", "debito", "credito", "saldo_final"],
        ),
        validar_extracao(
            "Transações",
            modelo.get("fato_lancamento_contabil", transacoes),
            ["id_lancamento", "data_lancamento", "conta_contabil", "debito", "credito"],
        ),
    ]

    secoes_numericas = validar_balancete(balancete) + validar_transacoes(
        modelo.get("fato_lancamento_contabil", transacoes)
    )
    if comparacao_habilitada:
        secoes_numericas += validar_conciliacao_cruzada(
            balancete,
            modelo.get("fato_lancamento_contabil", transacoes),
        )
    else:
        periodo_bal = info_periodo["balancete"].get("periodo") or "não identificado"
        periodos_tx = ", ".join(info_periodo["transacoes"].get("periodos", [])) or "não identificado"
        secoes_numericas.append(
            secao_informativa(
                "Comparação balancete x transações não aplicada",
                (
                    "A reconciliação direta entre balancete e transações foi pulada por aparente diferença de período. "
                    f"Balancete detectado: {periodo_bal}. Períodos nas transações: {periodos_tx}."
                ),
                indicadores=[
                    {"indicador": "Balancete", "valor": periodo_bal},
                    {"indicador": "Períodos transações", "valor": periodos_tx},
                ],
            )
        )

    secoes_modelo = validar_modelo_contabil(modelo)

    contrato_base = _montar_contrato_base_analitica(
        balancete,
        modelo.get("fato_lancamento_contabil", transacoes),
        modelo,
    )

    observacoes = [
        f"Método de leitura do balancete: {meta_balancete.get('metodo_leitura', '')}.",
        f"Aba selecionada para transações: {meta_transacoes.get('aba_escolhida', '')}.",
        (
            "Campos do balancete não mapeados automaticamente: "
            + (", ".join(faltantes_balancete) if faltantes_balancete else "nenhum.")
        ),
        (
            "Campos das transações não mapeados automaticamente: "
            + (", ".join(faltantes_transacoes) if faltantes_transacoes else "nenhum.")
        ),
        (
            "Planilhas dimensionais identificadas no XLSX: "
            + ", ".join(meta_modelo_raw.get("planilhas_resolvidas", {}).values())
            if meta_modelo_raw.get("planilhas_resolvidas")
            else "Nenhuma planilha dimensional identificada."
        ),
        (
            "Amostra atual sugere transações de 2025 no arquivo Excel e balancete de 12-2024 no TXT; "
            "por isso a comparação direta entre os dois pode exigir alinhamento de período."
        ),
        "Use preferencialmente o arquivo executar_pipeline_real.cmd para rodar a carga pelo cmd.",
    ]

    resumo_execucao = {
        "arquivo_balancete": str(balancete_path),
        "arquivo_transacoes": str(transacoes_path),
        "arquivo_config": str(config_path),
        "linhas_balancete": int(len(balancete.index)),
        "linhas_transacoes": int(len(transacoes.index)),
        "aba_transacoes": meta_transacoes.get("aba_escolhida", ""),
        "metodo_leitura_balancete": meta_balancete.get("metodo_leitura", ""),
        "mapeamento_balancete": mapeamento_balancete,
        "mapeamento_transacoes": mapeamento_transacoes,
        "mapeamento_fato": meta_modelo.get("mapeamento_fato", {}),
        "faltantes_balancete": faltantes_balancete,
        "faltantes_transacoes": faltantes_transacoes,
        "faltantes_fato": meta_modelo.get("faltantes_fato", []),
        "planilhas_modelo": meta_modelo_raw.get("planilhas_resolvidas", {}),
        "planilhas_modelo_faltantes": meta_modelo_raw.get("planilhas_faltantes", []),
        "modelo_detectado": meta_modelo_raw.get("modelo_detectado", False),
        "comparacao_periodo_habilitada": comparacao_habilitada,
        "periodo_detectado": info_periodo,
        "contrato_base_analitica": contrato_base,
    }

    renderizar_index(
        diretorios["saida"] / "index.html",
        resumo_execucao=resumo_execucao,
        perfil_abas=perfil_abas,
        observacoes=observacoes,
    )
    renderizar_pagina_secao(
        "Validação das Extrações",
        "Diagnóstico estrutural dos arquivos carregados.",
        secoes_extracao,
        diretorios["saida"] / "validacao_extracoes.html",
    )
    renderizar_pagina_secao(
        "Validação Numérica",
        "Conferências contábeis e comparações entre balancete e transações.",
        secoes_numericas,
        diretorios["saida"] / "validacao_numerica.html",
    )
    renderizar_pagina_secao(
        "Validação do Modelo Analítico",
        "Conferências de integridade entre fato, dimensões e mapas gerenciais.",
        secoes_modelo,
        diretorios["saida"] / "validacao_modelo.html",
    )

    (diretorios["saida"] / "resumo_execucao.json").write_text(
        json.dumps(resumo_execucao, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (diretorios["saida"] / "contrato_base_analitica.json").write_text(
        json.dumps(contrato_base, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return resumo_execucao
