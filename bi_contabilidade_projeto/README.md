# Projeto BI Contabilidade

Este projeto consolida a Fase 2 do BI contábil com foco em:

- leitura do balancete em `TXT`
- leitura do arquivo contábil em `XLSX`
- padronização da fato e das dimensões
- validação estrutural, numérica e relacional
- geração de páginas `HTML` para conferência

## Arquivos de origem atuais

- `..\balancete 12-2024.txt`
- `..\Data set - contabilidade-gerencial-html.xlsx`

O `TXT` atual é tabulado e o `XLSX` traz as planilhas:

- `FatoLancamentoContabil`
- `DimConta`
- `DimCentroCusto`
- `DimItemContaAux`
- `DimContaAux`
- `ParamBP_DRE`
- `Dim_CUSTO_PRODUCAO_MAPA`

## Ponto importante de período

Pela amostra do arquivo Excel, há lançamentos com datas de `2025`, enquanto o balancete informado no nome do arquivo está em `12-2024`.

Por isso, a pipeline:

- continua validando cada base individualmente
- só faz reconciliação direta entre balancete e transações quando detecta período compatível

## Estrutura

- `run_pipeline.py`: ponto de entrada do processo
- `executar_pipeline_real.cmd`: atalho para execução via `cmd`
- `config/contabilidade_gerencial_real.json`: mapeamento real do dataset atual
- `config/mapeamento_exemplo.json`: modelo genérico para adaptações futuras
- `src/bi_contabilidade/`: ingestão, validações e relatórios
- `saida/`: relatórios e bases tratadas

## Como executar no cmd

Use `cmd`, não PowerShell.

### Opção 1

```cmd
cd /d C:\Users\mfarias\OneDrive - CRISTALPET\POWER BI\Projetos\Contabilidade\Data driven - Gestão\bi_contabilidade_projeto
executar_pipeline_real.cmd
```

### Opção 2

```cmd
cd /d C:\Users\mfarias\OneDrive - CRISTALPET\POWER BI\Projetos\Contabilidade\Data driven - Gestão\bi_contabilidade_projeto
python run_pipeline.py --balancete "..\balancete 12-2024.txt" --transacoes "..\Data set - contabilidade-gerencial-html.xlsx" --config "config\contabilidade_gerencial_real.json" --saida "saida"
```

## Saídas oficiais da Fase 2

### Relatórios

- `saida/index.html`
- `saida/validacao_extracoes.html`
- `saida/validacao_numerica.html`
- `saida/validacao_modelo.html`

### Arquivos de controle

- `saida/perfil_abas_transacoes.csv`
- `saida/resumo_execucao.json`
- `saida/contrato_base_analitica.json`

### Bases tratadas

- `saida/dados_tratados/balancete_normalizado.csv`
- `saida/dados_tratados/transacoes_normalizadas.csv`
- `saida/dados_tratados/fato_lancamento_contabil.csv`
- `saida/dados_tratados/dim_conta.csv`
- `saida/dados_tratados/dim_centro_custo.csv`
- `saida/dados_tratados/dim_conta_aux.csv`
- `saida/dados_tratados/dim_item_conta_aux.csv`
- `saida/dados_tratados/param_bp_dre.csv`
- `saida/dados_tratados/dim_custo_producao_mapa.csv`

## Validações implementadas

### Balancete

- coerência entre saldo inicial, débito, crédito e saldo final
- amostra das contas após a padronização

### Fato contábil

- fechamento global débito x crédito
- conferência de `valor_liquido = debito - credito`
- fechamento por lançamento
- maiores movimentos por conta
- qualidade e faixa de datas

### Modelo analítico

- fato versus `DimConta`
- obrigatoriedade de conta auxiliar
- fato versus `DimContaAux`
- fato versus `DimItemContaAux`
- centro de custo nas contas 3 e 4
- cobertura de `ParamBP_DRE`
- cobertura de `Dim_CUSTO_PRODUCAO_MAPA`

## Próxima fase sugerida

Com a camada analítica estabilizada, a próxima evolução natural é criar a interface web consumindo os CSVs tratados, começando por:

- resumo executivo
- validação das extrações
- validação numérica
- DRE gerencial
- balanço patrimonial
- centro de custo
