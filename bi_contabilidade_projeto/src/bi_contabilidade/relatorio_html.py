from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


BASE_CSS = """
body {
  margin: 0;
  font-family: "Segoe UI", Tahoma, sans-serif;
  background: linear-gradient(180deg, #f4efe6 0%, #fbfaf8 100%);
  color: #18222d;
}
.shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px 64px;
}
.hero {
  background: linear-gradient(135deg, #0b3c49, #225b62);
  color: #f8f3eb;
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 18px 45px rgba(11, 60, 73, 0.18);
}
.hero h1 {
  margin: 0 0 8px;
  font-size: 2rem;
}
.hero p {
  margin: 0;
  max-width: 840px;
  line-height: 1.5;
}
.nav {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin: 20px 0 28px;
}
.nav a {
  text-decoration: none;
  color: #0b3c49;
  background: #d8e5dd;
  padding: 10px 14px;
  border-radius: 999px;
  font-weight: 600;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin: 24px 0;
}
.card {
  background: #ffffff;
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 10px 30px rgba(24, 34, 45, 0.08);
}
.metric {
  font-size: 1.8rem;
  font-weight: 700;
  margin-top: 8px;
  color: #8c4b2f;
}
.section {
  margin-top: 28px;
}
.section h2 {
  margin-bottom: 8px;
}
.section p {
  line-height: 1.5;
}
table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(24, 34, 45, 0.08);
}
th, td {
  padding: 10px 12px;
  border-bottom: 1px solid #ebedf0;
  text-align: left;
  font-size: 0.95rem;
}
th {
  background: #f3f6f8;
}
.note {
  background: #fff6df;
  border-left: 4px solid #d7962a;
  padding: 14px 16px;
  border-radius: 12px;
  margin-top: 16px;
}
pre {
  white-space: pre-wrap;
  background: #fff;
  padding: 16px;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(24, 34, 45, 0.08);
}
@media (max-width: 768px) {
  .shell {
    padding: 18px 14px 48px;
  }
  .hero h1 {
    font-size: 1.6rem;
  }
}
"""


def _render_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<div class='note'>Nenhuma linha para exibir nesta seção.</div>"

    headers = list(rows[0].keys())
    head_html = "".join(f"<th>{html.escape(str(col))}</th>" for col in headers)
    body_rows = []
    for row in rows:
        cols = "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in headers)
        body_rows.append(f"<tr>{cols}</tr>")
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _render_indicadores(indicadores: list[dict[str, Any]]) -> str:
    cards = []
    for item in indicadores:
        cards.append(
            "<div class='card'>"
            f"<div>{html.escape(str(item.get('indicador', 'Indicador')))}</div>"
            f"<div class='metric'>{html.escape(str(item.get('valor', '')))}</div>"
            "</div>"
        )
    return f"<div class='grid'>{''.join(cards)}</div>" if cards else ""


def _base_html(titulo: str, subtitulo: str, conteudo: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(titulo)}</title>
  <style>{BASE_CSS}</style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>{html.escape(titulo)}</h1>
      <p>{html.escape(subtitulo)}</p>
    </section>
    <nav class="nav">
      <a href="index.html">Resumo</a>
      <a href="validacao_extracoes.html">Validação das extrações</a>
      <a href="validacao_numerica.html">Validação numérica</a>
      <a href="validacao_modelo.html">Validação do modelo</a>
    </nav>
    {conteudo}
  </div>
</body>
</html>"""


def renderizar_pagina_secao(
    titulo: str, subtitulo: str, secoes: list[Any], destino: Path
) -> None:
    blocos = []
    for secao in secoes:
        blocos.append(
            "<section class='section'>"
            f"<h2>{html.escape(secao.titulo)}</h2>"
            f"<p>{html.escape(secao.resumo)}</p>"
            f"{_render_indicadores(secao.indicadores)}"
            f"{_render_table(secao.tabela)}"
            "</section>"
        )
    destino.write_text(_base_html(titulo, subtitulo, "".join(blocos)), encoding="utf-8")


def renderizar_index(
    destino: Path,
    resumo_execucao: dict[str, Any],
    perfil_abas: list[dict[str, Any]],
    observacoes: list[str],
) -> None:
    cards = [
        {"indicador": "Arquivo balancete", "valor": resumo_execucao.get("arquivo_balancete", "")},
        {"indicador": "Arquivo transações", "valor": resumo_execucao.get("arquivo_transacoes", "")},
        {"indicador": "Aba selecionada", "valor": resumo_execucao.get("aba_transacoes", "")},
        {"indicador": "Linhas balancete", "valor": resumo_execucao.get("linhas_balancete", 0)},
        {"indicador": "Linhas transações", "valor": resumo_execucao.get("linhas_transacoes", 0)},
    ]

    conteudo = [
        "<section class='section'>",
        "<h2>Visão geral</h2>",
        "<p>Este relatório organiza a primeira camada do projeto de BI contábil: extração, validação e base pronta para evolução das páginas gerenciais.</p>",
        _render_indicadores(cards),
        "</section>",
        "<section class='section'>",
        "<h2>Perfil das abas do arquivo de transações</h2>",
        "<p>Antes de consolidar as movimentações, o pipeline registra as abas encontradas e a estrutura preliminar de cada uma.</p>",
        _render_table(perfil_abas),
        "</section>",
        "<section class='section'>",
        "<h2>Observações para o próximo ciclo</h2>",
        "<div class='note'>" + "<br>".join(html.escape(obs) for obs in observacoes) + "</div>",
        "</section>",
        "<section class='section'>",
        "<h2>Resumo técnico da execução</h2>",
        f"<pre>{html.escape(json.dumps(resumo_execucao, ensure_ascii=False, indent=2, default=str))}</pre>",
        "</section>",
    ]
    destino.write_text(
        _base_html(
            "Projeto BI Contabilidade",
            "Resumo executivo da carga inicial, com foco em qualidade da extração e coerência contábil.",
            "".join(conteudo),
        ),
        encoding="utf-8",
    )
