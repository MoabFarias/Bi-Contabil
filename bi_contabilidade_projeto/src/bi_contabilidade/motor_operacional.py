import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "config.json"
LOGS_DIR = ROOT_DIR / "logs"
OUTPUTS_DIR = ROOT_DIR / "outputs"
OPERACIONAL_JSON = LOGS_DIR / "operacional_resumo.json"
OPERACIONAL_XLSX = OUTPUTS_DIR / "operacional_resumo.xlsx"
ABA_BASE_OPERACIONAL = "Base_Operacional"

MESES = {
    "janeiro": "01", "fevereiro": "02", "marco": "03", "março": "03", "abril": "04", "maio": "05", "junho": "06",
    "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12",
}
COLUNAS_BASE_OPERACIONAL = [
    "periodo",
    "preformas_vendidas_mil",
    "garrafas_vendidas_mil",
    "bonificacao_mil",
    "intercompany_preformas_mil",
    "preformas_produzidas_mil",
    "garrafas_produzidas_mil",
    "toneladas_vendidas",
    "toneladas_produzidas",
]
COLUNAS_MOVIMENTO = [
    "preformas_vendidas_mil",
    "garrafas_vendidas_mil",
    "bonificacao_mil",
    "intercompany_preformas_mil",
    "preformas_produzidas_mil",
    "garrafas_produzidas_mil",
    "toneladas_vendidas",
    "toneladas_produzidas",
]


def carregar_configuracao() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def normalizar_coluna(coluna: str) -> str:
    return str(coluna).strip().lower().replace("ç", "c").replace("ã", "a").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


def normalizar_numero(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(".", "").replace(",", ".")
    if texto in ["", "-", "nan", "None"]:
        return 0.0
    try:
        return float(texto)
    except ValueError:
        return 0.0


def converter_periodo(valor) -> str | None:
    if pd.isna(valor):
        return None
    if isinstance(valor, (pd.Timestamp, datetime)):
        return pd.Timestamp(valor).strftime("%Y-%m")
    texto = str(valor).strip().lower()
    texto = texto.replace("/", "-").replace("_", "-").replace(" ", "-")
    if re.fullmatch(r"\d{4}-\d{2}", texto):
        return texto
    match_data = re.search(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if match_data:
        return f"{match_data.group(1)}-{match_data.group(2)}"
    for mes_nome, mes_num in MESES.items():
        if texto.startswith(mes_nome):
            match = re.search(r"(\d{2}|\d{4})", texto)
            if not match:
                return None
            ano = match.group(1)
            if len(ano) == 2:
                ano = "20" + ano
            return f"{ano}-{mes_num}"
    return None


def localizar_arquivo_operacional(base_path: Path) -> Path | None:
    candidatos = []
    for extensao in ("*.xlsx", "*.xls"):
        candidatos.extend(base_path.glob(extensao))
    for arquivo in candidatos:
        nome = normalizar_coluna(arquivo.stem)
        if "volume" in nome and "producao" in nome and "venda" in nome:
            return arquivo
    return None


def ler_base_operacional(arquivo: Path) -> pd.DataFrame | None:
    excel = pd.ExcelFile(arquivo)
    abas = {normalizar_coluna(aba): aba for aba in excel.sheet_names}
    aba_real = abas.get(normalizar_coluna(ABA_BASE_OPERACIONAL))
    if aba_real is None:
        return None
    df = pd.read_excel(arquivo, sheet_name=aba_real)
    mapa_colunas = {normalizar_coluna(c): c for c in df.columns}
    faltantes = [c for c in COLUNAS_BASE_OPERACIONAL if normalizar_coluna(c) not in mapa_colunas]
    if faltantes:
        raise ValueError(f"Aba {ABA_BASE_OPERACIONAL} encontrada, mas faltam colunas: {faltantes}")
    saida = pd.DataFrame()
    for coluna in COLUNAS_BASE_OPERACIONAL:
        origem = mapa_colunas[normalizar_coluna(coluna)]
        if coluna == "periodo":
            saida[coluna] = df[origem].map(converter_periodo)
        else:
            saida[coluna] = df[origem].map(normalizar_numero)
    saida = saida[saida["periodo"].notna()].copy()
    saida.attrs["arquivo_operacional"] = str(arquivo)
    saida.attrs["origem_leitura"] = ABA_BASE_OPERACIONAL
    return saida


def localizar_inicio_tabela(bruto: pd.DataFrame) -> tuple[int, int]:
    melhor_linha = None
    melhor_coluna = None
    melhor_qtd = 0
    for col in bruto.columns:
        periodos = bruto[col].map(converter_periodo)
        qtd = int(periodos.notna().sum())
        if qtd > melhor_qtd:
            melhor_qtd = qtd
            melhor_coluna = int(col)
            indices = periodos[periodos.notna()].index.tolist()
            melhor_linha = int(indices[0]) if indices else None
    if melhor_linha is None or melhor_coluna is None or melhor_qtd == 0:
        raise ValueError("Nao foi possivel localizar coluna de periodo operacional (ex.: janeiro-25).")
    return melhor_linha, melhor_coluna


def montar_nome_colunas(bruto: pd.DataFrame, linha_inicio: int, coluna_inicio: int) -> list[str]:
    linhas_cabecalho = list(range(max(0, linha_inicio - 3), linha_inicio))
    nomes = []
    ultima_parte_por_coluna = {}
    for col in bruto.columns:
        if int(col) == coluna_inicio:
            nomes.append("periodo_texto")
            continue
        partes = []
        for linha in linhas_cabecalho:
            valor = bruto.iat[linha, int(col)] if int(col) < bruto.shape[1] else None
            if pd.isna(valor) or str(valor).strip() == "":
                continue
            partes.append(str(valor).strip())
        if not partes:
            partes = [f"coluna_{col}"]
        nome = " | ".join(partes)
        if nome in ultima_parte_por_coluna:
            ultima_parte_por_coluna[nome] += 1
            nome = f"{nome} | {ultima_parte_por_coluna[nome]}"
        else:
            ultima_parte_por_coluna[nome] = 1
        nomes.append(nome)
    return nomes


def carregar_operacional_legado(arquivo: Path) -> pd.DataFrame:
    bruto = pd.read_excel(arquivo, sheet_name=0, header=None)
    linha_inicio, coluna_periodo = localizar_inicio_tabela(bruto)
    nomes = montar_nome_colunas(bruto, linha_inicio, coluna_periodo)
    dados = bruto.iloc[linha_inicio:].copy()
    dados.columns = nomes[: len(dados.columns)]
    dados = dados.dropna(how="all")
    dados["periodo"] = dados["periodo_texto"].map(converter_periodo)
    dados = dados[dados["periodo"].notna()].copy()
    dados.attrs["arquivo_operacional"] = str(arquivo)
    dados.attrs["origem_leitura"] = "legado"
    dados.attrs["linha_inicio_dados"] = linha_inicio + 1
    dados.attrs["coluna_periodo"] = coluna_periodo + 1
    return dados


def carregar_operacional() -> pd.DataFrame:
    config = carregar_configuracao()
    base_path = Path(config["base_path"])
    arquivo = localizar_arquivo_operacional(base_path)
    if arquivo is None:
        raise FileNotFoundError(f"Arquivo operacional de volume/producao/vendas nao encontrado em: {base_path}")
    base = ler_base_operacional(arquivo)
    if base is not None:
        return base
    return carregar_operacional_legado(arquivo)


def obter_coluna_por_partes(df: pd.DataFrame, partes: list[str]) -> str | None:
    partes_n = [normalizar_coluna(p) for p in partes]
    for coluna in df.columns:
        col_n = normalizar_coluna(coluna)
        if all(p in col_n for p in partes_n):
            return coluna
    return None


def serie_metricas(df: pd.DataFrame, partes: list[str]) -> pd.Series:
    coluna = obter_coluna_por_partes(df, partes)
    if coluna is None:
        return pd.Series([0.0] * len(df), index=df.index)
    return df[coluna].map(normalizar_numero)


def enriquecer_operacional(saida: pd.DataFrame) -> pd.DataFrame:
    saida = saida.groupby("periodo", as_index=False).sum(numeric_only=True)
    saida["pecas_vendidas_mil"] = saida["preformas_vendidas_mil"] + saida["garrafas_vendidas_mil"] + saida["bonificacao_mil"] + saida["intercompany_preformas_mil"]
    saida["pecas_produzidas_mil"] = saida["preformas_produzidas_mil"] + saida["garrafas_produzidas_mil"]
    saida["gap_ton_producao_vs_venda"] = saida["toneladas_produzidas"] - saida["toneladas_vendidas"]
    saida["intercompany_pct_preformas"] = saida.apply(lambda r: 0 if r["preformas_vendidas_mil"] == 0 else (r["intercompany_preformas_mil"] / r["preformas_vendidas_mil"]) * 100, axis=1)
    saida["tem_movimento"] = saida[COLUNAS_MOVIMENTO].abs().sum(axis=1) > 0
    return saida


def montar_operacional() -> tuple[pd.DataFrame, dict]:
    df = carregar_operacional()
    if set(COLUNAS_BASE_OPERACIONAL).issubset(set(df.columns)):
        saida = df[COLUNAS_BASE_OPERACIONAL].copy()
    else:
        saida = pd.DataFrame()
        saida["periodo"] = df["periodo"]
        saida["preformas_vendidas_mil"] = serie_metricas(df, ["preforma", "ventas", "mil"])
        saida["garrafas_vendidas_mil"] = serie_metricas(df, ["botella", "ventas", "mil"])
        saida["bonificacao_mil"] = serie_metricas(df, ["bonificacion", "ventas", "mil"])
        saida["intercompany_preformas_mil"] = serie_metricas(df, ["intercompany", "preforma", "ventas", "mil"])
        saida["preformas_produzidas_mil"] = serie_metricas(df, ["preforma", "produccion", "mil"])
        saida["garrafas_produzidas_mil"] = serie_metricas(df, ["botella", "produccion", "mil"])
        saida["toneladas_vendidas"] = serie_metricas(df, ["tonelada", "ventas", "ton"])
        saida["toneladas_produzidas"] = serie_metricas(df, ["tonelado", "produccion", "ton"])

    saida = enriquecer_operacional(saida)
    periodos = sorted(saida["periodo"].tolist())
    ultimo = saida[saida["periodo"] == periodos[-1]].iloc[0].to_dict() if periodos else {}
    saida_mov = saida[saida["tem_movimento"]].copy()
    periodos_mov = sorted(saida_mov["periodo"].tolist())
    ultimo_mov = saida_mov[saida_mov["periodo"] == periodos_mov[-1]].iloc[0].to_dict() if periodos_mov else {}

    resumo = {
        "status": "sucesso",
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "arquivo_origem": df.attrs.get("arquivo_operacional"),
        "origem_leitura": df.attrs.get("origem_leitura"),
        "linha_inicio_dados": df.attrs.get("linha_inicio_dados"),
        "coluna_periodo": df.attrs.get("coluna_periodo"),
        "periodo_inicio": periodos[0] if periodos else None,
        "periodo_fim": periodos[-1] if periodos else None,
        "periodo_inicio_com_movimento": periodos_mov[0] if periodos_mov else None,
        "periodo_fim_com_movimento": periodos_mov[-1] if periodos_mov else None,
        "periodos_disponiveis": periodos,
        "periodos_com_movimento": periodos_mov,
        "ultimo_periodo": ultimo,
        "ultimo_periodo_com_movimento": ultimo_mov,
        "series": saida.to_dict(orient="records"),
    }
    return saida, resumo


def salvar(saida: pd.DataFrame, resumo: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    saida.to_excel(OPERACIONAL_XLSX, index=False)
    with open(OPERACIONAL_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    saida_df, resumo_execucao = montar_operacional()
    salvar(saida_df, resumo_execucao)
    print(json.dumps({k: v for k, v in resumo_execucao.items() if k != "series"}, ensure_ascii=False, indent=4))
