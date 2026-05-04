# Projeto BI Contabilidade

Este projeto monta uma base inicial de BI contábil a partir de:

- `balancete 12-2024.txt`
- `Data set - contabilidade-gerencial-html.xlsx`

O fluxo foi pensado para trabalhar em etapas:

1. Validar a extração dos arquivos
2. Padronizar e mapear colunas
3. Validar coerência numérica contábil
4. Gerar páginas HTML com os achados
5. Produzir bases tratadas para a próxima etapa visual

## Estrutura

- `run_pipeline.py`: ponto de entrada do processo
- `config/mapeamento_exemplo.json`: configuração opcional para aba e nomes de colunas
- `src/bi_contabilidade/`: módulos Python de ingestão, validação e geração HTML
- `saida/`: pasta sugerida para relatórios e arquivos tratados

## Como executar

Crie um ambiente com as dependências e execute:

```bash
python run_pipeline.py ^
  --balancete "..\balancete 12-2024.txt" ^
  --transacoes "..\Data set - contabilidade-gerencial-html.xlsx" ^
  --config "config\mapeamento_exemplo.json" ^
  --saida "saida"
```

No PowerShell, uma versão equivalente:

```powershell
python .\run_pipeline.py `
  --balancete "..\balancete 12-2024.txt" `
  --transacoes "..\Data set - contabilidade-gerencial-html.xlsx" `
  --config ".\config\mapeamento_exemplo.json" `
  --saida ".\saida"
```

## Entregas geradas

Após a execução, o projeto gera:

- `saida/index.html`: página inicial com resumo executivo
- `saida/validacao_extracoes.html`: diagnóstico da qualidade das extrações
- `saida/validacao_numerica.html`: reconciliações e consistência contábil
- `saida/dados_tratados/balancete_normalizado.csv`
- `saida/dados_tratados/transacoes_normalizadas.csv`
- `saida/perfil_abas_transacoes.csv`
- `saida/resumo_execucao.json`

## Mapeamento de colunas

Como o formato real pode variar, o pipeline tenta mapear automaticamente nomes como:

- Transações: `data`, `conta`, `historico`, `debito`, `credito`, `valor`, `lancamento`, `documento`
- Balancete: `conta`, `descricao`, `saldo inicial`, `debito`, `credito`, `saldo final`

Se os nomes estiverem diferentes no seu arquivo, ajuste o arquivo `config/mapeamento_exemplo.json`.

## Próximos passos sugeridos

1. Rodar o pipeline e revisar o perfil das colunas detectadas
2. Ajustar o mapeamento caso alguma aba ou coluna não seja reconhecida corretamente
3. Validar as diferenças apontadas no HTML
4. Evoluir para páginas gerenciais por tema:
   - visão executiva
   - DRE gerencial
   - balanço patrimonial
   - centro de custo
   - contas contábeis com maior variação

## Observações

- O pipeline preserva os arquivos de origem e trabalha em cópias tratadas.
- A lógica de reconciliação do balancete tenta identificar automaticamente a convenção de sinal mais compatível com os dados.
- Caso o `TXT` venha em layout posicional, o parser aplica uma leitura heurística baseada em separação por múltiplos espaços.
