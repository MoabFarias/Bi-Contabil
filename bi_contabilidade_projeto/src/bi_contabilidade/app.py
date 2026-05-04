from pathlib import Path
import subprocess
import sys

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.bi_contabilidade.atualizacao import ler_ultimo_log_carga

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / "logs"
OUTPUTS_DIR = ROOT_DIR / "outputs"
TEMPLATES_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"

app = FastAPI(title="Envases FP&A Cinematic Lab")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def ler_json(caminho: Path, padrao: dict) -> dict:
    if not caminho.exists():
        return padrao

    import json

    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def executar_script(nome_script: str) -> None:
    caminho_script = Path(__file__).resolve().parent / nome_script
    subprocess.run([sys.executable, str(caminho_script)], check=True)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    carga = ler_ultimo_log_carga()
    validacao = ler_json(
        LOGS_DIR / "validacao_modelo.json",
        {"status": "sem_validacao", "mensagem": "Nenhuma validacao executada."},
    )
    balancete = ler_json(
        LOGS_DIR / "balancete_resumo.json",
        {"status": "sem_balancete", "mensagem": "Nenhum balancete gerado."},
    )
    dre_resumo = ler_json(
        LOGS_DIR / "dre_resumo.json",
        {"status": "sem_dre", "mensagem": "Nenhuma DRE gerada."},
    )
    dre_detalhe = ler_json(
        LOGS_DIR / "dre_detalhe.json",
        {"grupos": []},
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "carga": carga,
            "validacao": validacao,
            "balancete": balancete,
            "dre_resumo": dre_resumo,
            "dre_detalhe": dre_detalhe,
        },
    )


@app.post("/atualizar-dados")
def atualizar_dados():
    executar_script("atualizacao.py")
    return RedirectResponse(url="/", status_code=303)


@app.post("/validar-modelo")
def validar_modelo():
    executar_script("validacoes.py")
    return RedirectResponse(url="/", status_code=303)


@app.post("/gerar-balancete")
def gerar_balancete():
    executar_script("motor_balancete.py")
    return RedirectResponse(url="/", status_code=303)


@app.post("/gerar-dre")
def gerar_dre():
    executar_script("motor_dre.py")
    return RedirectResponse(url="/", status_code=303)


@app.get("/download-balancete")
def download_balancete():
    arquivo = OUTPUTS_DIR / "balancete_mensal.xlsx"
    if not arquivo.exists():
        return HTMLResponse("Balancete ainda nao foi gerado.", status_code=404)
    return FileResponse(
        path=arquivo,
        filename="balancete_mensal.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/download-dre")
def download_dre():
    arquivo = OUTPUTS_DIR / "dre_gerencial.xlsx"
    if not arquivo.exists():
        return HTMLResponse("DRE ainda nao foi gerada.", status_code=404)
    return FileResponse(
        path=arquivo,
        filename="dre_gerencial.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
