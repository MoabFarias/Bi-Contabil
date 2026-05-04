# Bi-Contabil

Sistema web em Python + HTML para montagem, visualizacao e analise de balancete, DRE e contabilidade gerencial.

## Objetivo inicial

Criar um MVP para importar bases em Excel/CSV, montar um balancete completo e visualizar os saldos por conta contabil com rastreabilidade.

## Como executar localmente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Depois acesse:

```text
http://127.0.0.1:8000
```

## Estrutura inicial

```text
app/              Backend FastAPI e motor contabil
templates/        Telas HTML
static/           CSS e JavaScript
data/raw/         Arquivos originais exportados do ERP ou Excel
data/processed/   Bases tratadas
data/config/      De/para, mapas contabeis e parametros
```

## Estrutura versionada nesta etapa

```text
bi_contabilidade_projeto/  Pipeline inicial para ingestão, validação e geração de HTML
```

Esse diretório contém a primeira versão do projeto para:

- ler `balancete 12-2024.txt`
- perfilar o arquivo `Data set - contabilidade-gerencial-html.xlsx`
- mapear colunas automaticamente
- validar coerência numérica contábil
- gerar páginas HTML com diagnóstico das extrações e reconciliações
