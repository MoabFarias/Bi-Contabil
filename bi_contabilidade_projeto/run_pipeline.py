import argparse
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bi_contabilidade.pipeline import executar_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline inicial de BI contábil com validação e geração de HTML."
    )
    parser.add_argument("--balancete", required=True, help="Caminho do balancete em TXT.")
    parser.add_argument(
        "--transacoes", required=True, help="Caminho do arquivo de transações em XLSX."
    )
    parser.add_argument(
        "--config",
        default=str(BASE_DIR / "config" / "contabilidade_gerencial_real.json"),
        help="Arquivo JSON opcional com aba e mapeamento de colunas.",
    )
    parser.add_argument(
        "--saida",
        default=str(BASE_DIR / "saida"),
        help="Diretório onde os relatórios e CSVs serão gerados.",
    )

    args = parser.parse_args()

    executar_pipeline(
        balancete_path=Path(args.balancete),
        transacoes_path=Path(args.transacoes),
        config_path=Path(args.config),
        saida_dir=Path(args.saida),
    )


if __name__ == "__main__":
    main()
