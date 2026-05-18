@echo off
setlocal

set "BASE_DIR=%~dp0"

if "%PYTHON_EXE%"=="" set "PYTHON_EXE=python"

echo Executando pipeline contabil via cmd...
echo Python: %PYTHON_EXE%

"%PYTHON_EXE%" "%BASE_DIR%run_pipeline.py" ^
  --balancete "%BASE_DIR%..\balancete 12-2024.txt" ^
  --transacoes "%BASE_DIR%..\Data set - contabilidade-gerencial-html.xlsx" ^
  --config "%BASE_DIR%config\contabilidade_gerencial_real.json" ^
  --saida "%BASE_DIR%saida"

if errorlevel 1 (
  echo.
  echo A execucao terminou com erro.
  exit /b 1
)

echo.
echo Pipeline concluida. Abra os HTMLs em "%BASE_DIR%saida".
exit /b 0
