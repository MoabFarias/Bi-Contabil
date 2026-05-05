import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "config.json"
LOGS_DIR = ROOT_DIR / "logs"
OUTPUTS_DIR = ROOT_DIR / "outputs"
OPERACIONAL_JSON = LOGS_DIR / "operacional_resumo.json"
OPERACIONAL_XLSX = OUTPUTS_DIR / "operacional_resumo.xlsx"


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
    texto = str(valor).strip().replace(".", "").replace(",", ".").replace("-", "0")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def localizar_arquivo_operacional(base_path: Path) -> Path | None:
    candidatos = []
    for extensao in ("*.xlsx", "*.xls"):
        candidatos.extend(base_path.glob(extensao))
    for arquivo in candidatos:
        nome = arquivo.stem.lower()
        if "volume" in nome and ("producao" in nome or "produção" in nome) and "venda" in nome:
            return arquivo
    return None


def carregar_operacional() -> pd.DataFrame:
    config = carregar_configuracao()
    base_path = Path(config["base_path"])
    arquivo = localizar_arquivo_operacional(base_path)
    if arquivo is None:
        raise FileNotFoundError(f"Arquivo operacional de volume/producao/vendas nao encontrado em: {base_path}")

    bruto = pd.read_excel(arquivo, sheet_name=0, header=None)
    if len(bruto) < 4:
        raise ValueError("Arquivo operacional precisa ter ao menos 4 linhas de cabecalho/dados.")

    grupo = bruto.iloc[0].ffill().fillna("").astype(str).str.strip().tolist()
    metrica = bruto.iloc[1].fillna("").astype(str).str.strip().tolist()
    unidade = bruto.iloc[2].fillna("").astype(str).str.strip().tolist()

    nomes = []
    for i, (g, m, u) in enumerate(zip(grupo, metrica, unidade)):
        if i == 0:
            nomes.append("periodo_texto")
        else:
            partes = [p for p in [g, m, u] if p]
            nomes.append(" | ".join(partes))

    dados = bruto.iloc[3:].copy()
    dados.columns = nomes
    dados = dados.dropna(how="all")
    dados = dados[dados["periodo_texto"].notna()].copy()
    dados["periodo_texto"] = dados["periodo_texto"].astype(str).str.strip()
    dados = dados[~dados["periodo_texto"].isin(["", "nan", "None"])]

    mapa_mes = {
        "janeiro": "01", "fevereiro": "02", "marco": "03", "março": "03", "abril": "04", "maio": "05", "junho": "06",
        "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12",
    }

    def converter_periodo(valor: str) -> str | None:
        texto = valor.strip().lower()
        if "-" not in texto:
            return None
        mes, ano = texto.split("-", 1)
        mes_num = mapa_mes.get(mes)
        if mes_num is None:
            return None
        ano = ano.strip()
        if len(ano) == 2:
            ano = "20" + ano
        return f"{ano}-{mes_num}"

    dados["periodo"] = dados["periodo_texto"].map(converter_periodo)
    dados = dados[dados["periodo"].notna()].copy()
    dados.attrs["arquivo_operacional"] = str(arquivo)
    return dados


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


def montar_operacional() -> tuple[pd.DataFrame, dict]:
    df = carregar_operacional()
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

    saida = saida.groupby("periodo", as_index=False).sum(numeric_only=True)
    periodos = sorted(saida["periodo"].tolist())
    ultimo = saida[saida["periodo"] == periodos[-1]].iloc[0].to_dict() if periodos else {}

    resumo = {
        "status": "sucesso",
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "arquivo_origem": df.attrs.get("arquivo_operacional"),
        "periodo_inicio": periodos[0] if periodos else None,
        "periodo_fim": periodos[-1] if periodos else None,
        "periodos_disponiveis": periodos,
        "ultimo_periodo": ultimo,
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
