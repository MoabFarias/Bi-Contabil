# Resumo de Atividades - Projeto BI Contabil

Data de referencia: 2026-05-04

## 1. Objetivo do projeto

Construir um sistema web de contabilidade gerencial em Python + HTML para automatizar a leitura, validacao, montagem e visualizacao de balancete, BP, DRE e analises gerenciais a partir de dados extraidos do ERP Oracle via Power Query em Excel.

A primeira fase usa o arquivo XLSX como fonte oficial. A conexao direta Oracle ODBC ficara para fase futura, apos estabilizacao do modelo de dados, regras contabeis e validacoes.

---

## 2. Atividades planejadas inicialmente

### 2.1 Fundacao do projeto

- Criar repositorio GitHub para versionamento.
- Organizar estrutura de pastas do projeto.
- Documentar SDD - Software Design Document.
- Documentar fontes de dados e caminho local dos arquivos.
- Documentar modelo dimensional contabil.
- Documentar regras contabeis e gerenciais.

### 2.2 Diagnostico dos dados

- Realizar profiling do Excel principal.
- Identificar abas, colunas, tipos de dados e nulos.
- Validar estrutura da FatoLancamentoContabil.
- Validar dimensoes: DimConta, DimCentroCusto, DimContaAux, DimItemContaAux.
- Validar ParamBP_DRE e mapa de custo de producao.

### 2.3 Validacao relacional

- Validar se todas as contas da fato existem na DimConta.
- Validar se contas que exigem conta auxiliar possuem CNT_AUX e ITEM_CNTAUX.
- Validar relacao CONTA + CNT_AUX com DimContaAux.
- Validar relacao CNT_AUX + ITEM_CNTAUX com DimItemContaAux.
- Validar centros de custo utilizados.
- Validar mapeamento de BP/DRE por prefixo sintetico.
- Validar contas 4 com movimento no mapa de custo.

### 2.4 Motor de balancete

- Criar motor inicial de balancete mensal.
- Gerar Excel de saida com balancete mensal e analitico de lancamentos.
- Gerar JSON resumo do balancete.
- Aplicar regra de visualizacao ate mes corrente + 2 meses.

---

## 3. Atividades realizadas

### 3.1 Repositorio e estrutura

Repositorio utilizado:

```text
MoabFarias/Bi-Contabil
```

Foram criadas e/ou organizadas as seguintes estruturas:

```text
bi_contabilidade_projeto/
├── config/
├── docs/
├── logs/
├── outputs/
└── src/
    └── bi_contabilidade/
```

### 3.2 Documentacao criada

Arquivos documentais criados:

```text
bi_contabilidade_projeto/docs/SDD.md
bi_contabilidade_projeto/docs/DATA_SOURCES.md
bi_contabilidade_projeto/docs/DATA_MODEL.md
bi_contabilidade_projeto/docs/ACCOUNTING_RULES.md
```

Esses documentos registram:

- objetivo do sistema;
- fontes de dados;
- caminho local dos datasets;
- estrutura dimensional;
- regras de BP, DRE e custo de producao;
- tratamento de conta auxiliar;
- tratamento de centro de custo;
- regra da conta 4 fora da DRE;
- regra de CPV na conta 3.

### 3.3 Profiling dos dados

Foi criado e executado o script de profiling:

```text
src/bi_contabilidade/profiling.py
```

Resultado observado:

- Arquivos encontrados na pasta Dataset: 2.
- Abas encontradas no Excel:
  - FatoLancamentoContabil
  - DimConta
  - DimCentroCusto
  - DimItemContaAux
  - DimContaAux
  - ParamBP_DRE
  - Dim_CUSTO_PRODUCAO_MAPA

Resumo dos volumes:

| Tabela | Linhas |
|---|---:|
| FatoLancamentoContabil | 112.825 |
| DimConta | 1.321 |
| DimCentroCusto | 16 |
| DimItemContaAux | 3.221 |
| DimContaAux | 21 |
| ParamBP_DRE | 84 apos ajuste |
| Dim_CUSTO_PRODUCAO_MAPA | 40 |

### 3.4 Validacao do modelo

Foi executada a validacao relacional e contabil.

Resultado apos os ajustes:

| Validacao | Resultado |
|---|---:|
| Contas da fato fora da DimConta | 0 |
| Contas que exigem auxiliar sem CNT_AUX | 0 |
| Contas que exigem auxiliar sem ITEM_CNTAUX | 0 |
| CONTA + CNT_AUX fora da DimContaAux | 0 |
| CNT_AUX + ITEM_CNTAUX fora da DimItemContaAux | 0 |
| CCUSTO preenchido fora da DimCentroCusto | 0 |
| Contas 1/2/3 fora do ParamBP_DRE | 0 |
| Contas 4 com movimento fora do mapa de custo | 0 |
| Divergencias em VALOR_LIQ = VALOR_DEB - VALOR_CRE | 0 |

Ponto tratado por regra:

- Foram identificadas 16.120 linhas em contas 3 e 4 sem centro de custo.
- Regra aprovada:
  - Conta 3 sem CCUSTO: classificar como ADMINISTRACAO.
  - Conta 4 sem CCUSTO: classificar como PRODUCAO.

### 3.5 Ajuste do ParamBP_DRE

Foram identificadas inicialmente 2 contas fora do ParamBP_DRE:

```text
1.1.02.07.0003
1.1.05.01.0017
```

Essas contas foram corrigidas no dataset pelo usuario, e a validacao posterior passou a retornar 0 contas fora do ParamBP_DRE.

### 3.6 Controle de carga

Foi criada configuracao do projeto:

```text
config/config.json
```

Configuracoes atuais:

- caminho da pasta Dataset;
- nome do arquivo principal;
- uso de Excel XLSX como fonte;
- flag futura para Power Query;
- limite automatico de visualizacao.

### 3.7 Motor de balancete

Foi criado o motor inicial:

```text
src/bi_contabilidade/motor_balancete.py
```

Saidas geradas:

```text
outputs/balancete_mensal.xlsx
logs/balancete_resumo.json
```

Resultado validado:

| Indicador | Resultado |
|---|---:|
| Periodo total carregado | 2025-01 a 2027-12 |
| Periodo visualizado | 2025-01 a 2026-07 |
| Linhas totais carregadas | 112.825 |
| Linhas visualizadas | 112.767 |
| Linhas ocultadas por periodo | 58 |
| Linhas do balancete | 3.498 |
| Total debitos exibidos | 7.348.245.728,57 |
| Total creditos exibidos | 7.348.245.728,57 |
| Movimento total | 0,00 |
| Linhas com CCUSTO por regra automatica | 16.120 |

### 3.8 Limite de periodos futuros

Foi implementada regra de visualizacao:

```text
Visualizar ate mes corrente + 2 meses.
```

O sistema carrega todo o periodo disponivel, mas so apresenta no balancete padrao os periodos permitidos pela configuracao.

---

## 4. Regras de negocio aprovadas

### 4.1 Classificacao por raiz da conta

| Raiz | Tratamento |
|---|---|
| 1 | BP - Ativo |
| 2 | BP - Passivo / PL |
| 3 | DRE - Resultado |
| 4 | Custo de producao |

### 4.2 Conta 4

- A conta 4 nao deve ser somada diretamente na DRE.
- A conta 4 representa apuracao de custo de producao.
- A conta 4 e zerada mensalmente e transferida para estoque.
- O impacto na DRE ocorre via CPV na conta 3.

### 4.3 Conta auxiliar

- Conta auxiliar so e obrigatoria quando DimConta.USA_CONTA_AUX = S.
- Quando houver CNT_AUX e ITEM_CNTAUX, ambos devem estar mapeados nas dimensoes auxiliares.

### 4.4 Centro de custo

- Centro de custo preenchido deve existir na DimCentroCusto.
- Contas 3 sem centro de custo devem ser classificadas automaticamente como ADMINISTRACAO.
- Contas 4 sem centro de custo devem ser classificadas automaticamente como PRODUCAO.

### 4.5 ParamBP_DRE

- O mapeamento de BP/DRE deve ocorrer por prefixo hierarquico.
- Contas analiticas herdam o agrupamento de contas sinteticas.

### 4.6 Periodos futuros

- O sistema pode carregar lancamentos futuros.
- A visualizacao padrao deve limitar ate mes corrente + 2 meses.
- Periodos futuros acima desse limite ficam ocultos da visualizacao padrao.

---

## 5. O que precisa ser feito agora

### 5.1 Melhorar organizacao dos scripts

- Corrigir confusao entre `validacoes.py` e `validacao_modelo.py`.
- Transformar `validacao_modelo.py` em executor oficial ou remover o placeholder.
- Padronizar nomes de arquivos e comandos no README.

### 5.2 Versionamento dos arquivos locais

- Garantir que `motor_balancete.py` esteja versionado no GitHub.
- Garantir que alteracoes locais estejam com `git status` limpo.
- Confirmar `.gitignore` para nao subir arquivos sensiveis.

Arquivos que nao devem subir:

```text
Dataset/
*.xlsx
*.xls
*.csv
logs/*.json
outputs/*.xlsx
.venv/
__pycache__/
```

### 5.3 Dashboard HTML inicial

Criar primeira tela HTML com:

- status da ultima carga;
- status da validacao;
- periodo total carregado;
- periodo visualizado;
- linhas carregadas e visualizadas;
- debitos, creditos e movimento;
- quantidade de linhas ocultadas por periodo;
- quantidade de linhas com CCUSTO por regra automatica;
- botoes:
  - Atualizar dados;
  - Validar modelo;
  - Gerar balancete;
  - Abrir/baixar balancete Excel.

### 5.4 Integração com FastAPI

Criar rotas iniciais:

```text
GET  /                  Dashboard inicial
POST /atualizar-dados   Executa atualizacao.py
POST /validar-modelo    Executa validacoes.py
POST /gerar-balancete   Executa motor_balancete.py
GET  /download-balancete Baixa outputs/balancete_mensal.xlsx
```

### 5.5 Balancete com saldo inicial

O motor atual monta movimento mensal a partir da FatoLancamentoContabil.

Proxima evolucao:

- Incorporar balancete inicial 12/2024.
- Calcular saldo inicial mensal.
- Calcular saldo final mensal.
- Conciliar saldo final com o balancete oficial do ERP quando disponivel.

---

## 6. Atividades que ficam para outro momento

### 6.1 Power Query automatico

Fase futura:

- Botao para atualizar Power Query dentro do Excel.
- Uso de pywin32 para abrir Excel, executar RefreshAll, salvar e fechar.

Motivo para deixar depois:

- Depende de Excel instalado localmente.
- Pode exigir login, permissao e tratamento de travamentos.

### 6.2 Oracle ODBC direto

Fase futura:

- Substituir ou complementar XLSX por conexao direta ao Oracle via ODBC.
- Migrar queries do Power Query para SQL controlado pelo Python.

Motivo para deixar depois:

- Primeiro e necessario estabilizar modelo, regras e validacoes.

### 6.3 DRE completa em HTML

Fase futura:

- Criar DRE estruturada pelo ParamBP_DRE.
- Aplicar regras de sinal gerencial.
- Exibir linhas e subtotais.
- Permitir drill-down para lancamentos.

### 6.4 BP completo em HTML

Fase futura:

- Criar Balanco Patrimonial estruturado.
- Apresentar Ativo, Passivo e PL.
- Conciliar totais.

### 6.5 Analise de custo de producao

Fase futura:

- Criar visao especifica para conta 4.
- Analisar custo direto e indireto.
- Separar grupos do mapa de custo.
- Conectar apuracao de custo com estoque.

### 6.6 IA explicativa

Fase futura:

- Gerar comentarios automaticos de variacao.
- Explicar resultado mensal.
- Apontar contas com comportamento anormal.
- Gerar resumo executivo para controladora.

### 6.7 Controle de usuarios e seguranca

Fase futura:

- Autenticacao.
- Perfis de acesso.
- Controle de permissoes.

---

## 7. Proxima etapa recomendada

A proxima etapa recomendada e criar o dashboard HTML inicial com FastAPI, usando os arquivos JSON e XLSX ja gerados.

Prioridade imediata:

1. Organizar scripts oficiais.
2. Criar dashboard inicial.
3. Criar botoes de execucao.
4. Exibir status de carga, validacao e balancete.
5. Incorporar saldo inicial de 12/2024 no motor de balancete.

---

## 8. Comandos principais atuais

Executar atualizacao/carga:

```bash
python .\src\bi_contabilidade\atualizacao.py
```

Executar validacao:

```bash
python .\src\bi_contabilidade\validacoes.py
```

Gerar balancete:

```bash
python .\src\bi_contabilidade\motor_balancete.py
```

Verificar versionamento:

```bash
git status
```

Atualizar local com GitHub:

```bash
git pull origin main
```

Enviar alteracoes locais:

```bash
git add .
git commit -m "Atualiza projeto BI Contabil"
git push origin main
```
