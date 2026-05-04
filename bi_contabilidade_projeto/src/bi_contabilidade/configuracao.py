from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any


def carregar_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalizar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.replace("_", " ").split())


def slug(valor: Any) -> str:
    texto = normalizar_texto(valor)
    return texto.replace(" ", "_")
