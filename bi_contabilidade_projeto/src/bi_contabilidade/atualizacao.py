import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "config.json"
LOGS_DIR = ROOT_DIR / "logs"
LOG_CARGA_PATH = LOGS_DIR / "carga_dados.json"


def carregar_configuracao() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def salvar_log_carga(log: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    with open(LOG_CARGA_PATH, "w", encoding="utf-8") as file:
        json.dump(log, file, ensure_ascii=False, indent=4)


def obter_status_arquivo(caminho_arquivo: Path) -> dict:
    stat = caminho_arquivo.stat()

    return {
        "arquivo": caminho_arquivo.name,
        "caminho": str(caminho_arquivo),
        "arquivo_modificado_em": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "tamanho_mb": round(stat.st_size / (1024 * 1024), 2),
    }


def executar_carga_xlsx() -> dict:
    inicio = datetime.now()
    config = carregar_configuracao()

    base_path = Path(config["base_path"])
    arquivo_principal = config["arquivo_principal"]
    caminho_arquivo = base_path / arquivo_principal

    if not base_path.exists():
        raise FileNotFoundError(f"Pasta base não encontrada: {base_path}")

    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo principal não encontrado: {caminho_arquivo}")

    status_arquivo = obter_status_arquivo(caminho_arquivo)

    xls = pd.ExcelFile(caminho_arquivo)
    abas = xls.sheet_names

    resumo_abas = {}
    menor_data_lancamento = None
    maior_data_lancamento = None

    for aba in abas:
        df = pd.read_excel(caminho_arquivo, sheet_name=aba)

        resumo_abas[aba] = {
            "linhas": int(len(df)),
            "colunas": int(len(df.columns)),
            "colunas_nomes": [str(c) for c in df.columns],
        }

        if aba.strip().lower() == "fatolancamentocontabil" and "LDATA" in df.columns:
            datas = pd.to_datetime(df["LDATA"], errors="coerce").dropna()

            if not datas.empty:
                menor_data_lancamento = datas.min().strftime("%Y-%m-%d")
                maior_data_lancamento = datas.max().strftime("%Y-%m-%d")

    fim = datetime.now()

    log = {
        "ultima_atualizacao": fim.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "sucesso",
        "origem": arquivo_principal,
        "tempo_processamento_segundos": round((fim - inicio).total_seconds(), 2),
        "arquivo": status_arquivo,
        "abas_processadas": abas,
        "resumo_abas": resumo_abas,
        "menor_data_lancamento": menor_data_lancamento,
        "maior_data_lancamento": maior_data_lancamento,
        "mensagem": "Carga XLSX concluída com sucesso."
    }

    salvar_log_carga(log)
    return log


def ler_ultimo_log_carga() -> dict:
    if not LOG_CARGA_PATH.exists():
        return {
            "status": "sem_carga",
            "mensagem": "Nenhuma carga executada ainda."
        }

    with open(LOG_CARGA_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    try:
        resultado = executar_carga_xlsx()
        print(json.dumps(resultado, ensure_ascii=False, indent=4))
    except Exception as erro:
        log = {
            "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "erro",
            "mensagem": str(erro)
        }
        salvar_log_carga(log)
        print(json.dumps(log, ensure_ascii=False, indent=4))
        raise
