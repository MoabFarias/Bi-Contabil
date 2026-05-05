import json
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / "logs"
OUTPUTS_DIR = ROOT_DIR / "outputs"
DRE_COMPARATIVO_JSON = LOGS_DIR / "dre_comparativo.json"
OPERACIONAL_JSON = LOGS_DIR / "operacional_resumo.json"
KPIS_JSON = LOGS_DIR / "kpis_resumo.json"


def ler_json(caminho: Path, padrao: dict) -> dict:
    if not caminho.exists():
        return padrao
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def valor_linha_dre(dre: dict, bloco: str, grupo: str, campo: str) -> float:
    bloco_n = bloco.lower().strip()
    grupo_n = grupo.lower().strip()
    for linha in dre.get("linhas", []):
        b = str(linha.get("bloco", "")).lower().strip()
        g = str(linha.get("grupo", "")).lower().strip()
        if b == bloco_n and g == grupo_n:
            return float(linha.get(campo, 0) or 0)
    return 0.0


def somar_bloco(dre: dict, bloco: str, campo: str) -> float:
    bloco_n = bloco.lower().strip()
    return sum(float(l.get(campo, 0) or 0) for l in dre.get("linhas", []) if str(l.get("bloco", "")).lower().strip() == bloco_n)


def buscar_operacional_periodo(operacional: dict, periodo: str) -> dict:
    for linha in operacional.get("series", []):
        if linha.get("periodo") == periodo:
            return linha
    return {}


def dividir(numerador: float, denominador: float) -> float | None:
    if denominador == 0:
        return None
    return numerador / denominador


def montar_visao_gerencial(dre: dict, campo: str) -> dict:
    receita_bruta_raw = valor_linha_dre(dre, "Receita Bruta", "Mercado interno", campo)
    deducoes_raw = somar_bloco(dre, "Deduções da Receita Bruta", campo)
    cpv_raw = valor_linha_dre(dre, "CPV", "CUSTO DOS PRODUTOS VENDIDOS", campo)

    receita_bruta = abs(receita_bruta_raw)
    deducoes = -abs(deducoes_raw)
    receita_liquida = receita_bruta + deducoes
    cpv = -abs(cpv_raw)
    margem_bruta = receita_liquida + cpv

    return {
        "receita_bruta_raw": receita_bruta_raw,
        "deducoes_raw": deducoes_raw,
        "cpv_raw": cpv_raw,
        "receita_bruta": receita_bruta,
        "deducoes": deducoes,
        "receita_liquida": receita_liquida,
        "cpv": cpv,
        "margem_bruta": margem_bruta,
    }


def montar_kpis() -> dict:
    dre = ler_json(DRE_COMPARATIVO_JSON, {"linhas": [], "periodo_base": None, "periodo_comparacao": None})
    operacional = ler_json(OPERACIONAL_JSON, {"series": [], "ultimo_periodo_com_movimento": {}})

    periodo_base = dre.get("periodo_base") or operacional.get("periodo_fim_com_movimento")
    periodo_comparacao = dre.get("periodo_comparacao")

    op_base = buscar_operacional_periodo(operacional, periodo_base) if periodo_base else {}
    op_comp = buscar_operacional_periodo(operacional, periodo_comparacao) if periodo_comparacao else {}

    ger_base = montar_visao_gerencial(dre, "valor_base")
    ger_comp = montar_visao_gerencial(dre, "valor_comparacao")

    ton_base = float(op_base.get("toneladas_vendidas", 0) or 0)
    ton_comp = float(op_comp.get("toneladas_vendidas", 0) or 0)
    pecas_base = float(op_base.get("pecas_vendidas_mil", 0) or 0)
    pecas_comp = float(op_comp.get("pecas_vendidas_mil", 0) or 0)

    resumo = {
        "status": "sucesso",
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "periodo_base": periodo_base,
        "periodo_comparacao": periodo_comparacao,
        "metodologia": "Visao gerencial: receita bruta positiva, deducoes negativas, CPV negativo. Receita liquida = Receita Bruta + Deducoes. Margem bruta = Receita liquida + CPV.",
        "base": {
            **ger_base,
            "toneladas_vendidas": ton_base,
            "pecas_vendidas_mil": pecas_base,
            "receita_liquida_por_ton": dividir(ger_base["receita_liquida"], ton_base),
            "cpv_por_ton": dividir(ger_base["cpv"], ton_base),
            "margem_bruta_por_ton": dividir(ger_base["margem_bruta"], ton_base),
            "receita_liquida_por_mil_pecas": dividir(ger_base["receita_liquida"], pecas_base),
            "intercompany_pct_preformas": op_base.get("intercompany_pct_preformas"),
            "gap_ton_producao_vs_venda": op_base.get("gap_ton_producao_vs_venda"),
        },
        "comparacao": {
            **ger_comp,
            "toneladas_vendidas": ton_comp,
            "pecas_vendidas_mil": pecas_comp,
            "receita_liquida_por_ton": dividir(ger_comp["receita_liquida"], ton_comp),
            "cpv_por_ton": dividir(ger_comp["cpv"], ton_comp),
            "margem_bruta_por_ton": dividir(ger_comp["margem_bruta"], ton_comp),
            "receita_liquida_por_mil_pecas": dividir(ger_comp["receita_liquida"], pecas_comp),
            "intercompany_pct_preformas": op_comp.get("intercompany_pct_preformas"),
            "gap_ton_producao_vs_venda": op_comp.get("gap_ton_producao_vs_venda"),
        },
    }

    for chave in ["receita_liquida_por_ton", "cpv_por_ton", "margem_bruta_por_ton", "receita_liquida_por_mil_pecas"]:
        b = resumo["base"].get(chave)
        c = resumo["comparacao"].get(chave)
        resumo[f"variacao_{chave}"] = None if b is None or c is None else b - c

    return resumo


def salvar(resumo: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(KPIS_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    resumo_execucao = montar_kpis()
    salvar(resumo_execucao)
    print(json.dumps(resumo_execucao, ensure_ascii=False, indent=4))
