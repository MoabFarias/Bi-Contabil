from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .configuracao import carregar_config
from .ingestao import (
    carregar_balancete_txt,
    carregar_transacoes_excel,
    preparar_balancete,
    preparar_transacoes,
)
from .relatorio_html import renderizar_index, renderizar_pagina_secao
from .validacoes import (
    validar_balancete,
    validar_conciliacao_cruzada,
    validar_extracao,
    validar_transacoes,
)


def _garantir_diretorios(saida_dir: Path) -> dict[str, Path]:
    dados_tratados = saida_dir / "dados_tratados"
    saida_dir.mkdir(parents=True, exist_ok=True)
    dados_tratados.mkdir(parents=True, exist_ok=True)
    return {"saida": saida_dir, "dados_tratados": dados_tratados}


def _exportar_csv(df: pd.DataFrame, destino: Path) -> None:
    df.to_csv(destino, index=False, encoding="utf-8-sig")


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

    balancete, mapeamento_balancete, faltantes_balancete = preparar_balancete(
        balancete_raw, config
    )
    transacoes, mapeamento_transacoes, faltantes_transacoes = preparar_transacoes(
        transacoes_raw, config
    )

    _exportar_csv(
        balancete, diretorios["dados_tratados"] / "balancete_normalizado.csv"
    )
    _exportar_csv(
        transacoes, diretorios["dados_tratados"] / "transacoes_normalizadas.csv"
    )
    pd.DataFrame(perfil_abas).to_csv(
        diretorios["saida"] / "perfil_abas_transacoes.csv",
        index=False,
        encoding="utf-8-sig",
    )

    secoes_extracao = [
        validar_extracao(
            "Balancete",
            balancete,
            ["conta_contabil", "debito", "credito"],
        ),
        validar_extracao(
            "Transações",
            transacoes,
            ["data_lancamento", "conta_contabil", "debito", "credito"],
        ),
    ]

    secoes_numericas = (
        validar_balancete(balancete)
        + validar_transacoes(transacoes)
        + validar_conciliacao_cruzada(balancete, transacoes)
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
        "Se alguma coluna-chave não tiver sido reconhecida, ajuste o arquivo config/mapeamento_exemplo.json e rode novamente.",
        "O próximo ciclo pode evoluir para páginas gerenciais por conta, natureza, centro de custo e DRE.",
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
        "faltantes_balancete": faltantes_balancete,
        "faltantes_transacoes": faltantes_transacoes,
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

    (diretorios["saida"] / "resumo_execucao.json").write_text(
        json.dumps(resumo_execucao, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return resumo_execucao
