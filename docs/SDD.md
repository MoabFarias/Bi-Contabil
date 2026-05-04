# SDD - Software Design Document

Projeto: **BI Contabil**

## 1. Objetivo do sistema

Construir uma aplicacao web em Python + HTML para automatizar a montagem, validacao, visualizacao e analise de balancete, DRE e relatorios gerenciais a partir de dados contabeis extraidos do ERP Oracle via ODBC.

O sistema devera permitir rastreabilidade desde os saldos apresentados ate os lancamentos contabeis originais.

---

## 2. Premissas do projeto

- Existe um balancete inicial de dezembro de 2024.
- Existem transacoes contabeis a partir de janeiro de 2025.
- Os dados sao extraidos do banco Oracle via ODBC.
- A base pode ser atualizada em tempo real ou em ciclos de atualizacao definidos.
- Existem contas contabeis, contas auxiliares, centros de custo, clientes e fornecedores.
- Existem estruturas de de/para para montagem de relatorios internos e da controladora.
- Antes da construcao dos dashboards, sera realizada analise exploratoria e validacao contabil dos datasets.

---

## 3. Escopo inicial do MVP

### 3.1 Incluido

- Inventario dos datasets.
- Mapeamento de colunas.
- Analise exploratoria dos dados.
- Validacao de tipos de dados.
- Validacao de saldos, debitos e creditos.
- Conciliacao entre balancete inicial e movimentacoes.
- Montagem do balancete mensal.
- Amostragem de calculos com validacao manual.
- Registro das regras contabeis aprovadas.
- Visualizacao HTML do balancete.

### 3.2 Fora do escopo inicial

- DRE automatica completa.
- Orcamento x realizado.
- IA explicativa.
- Integracao definitiva com relatorios da controladora.
- Controle de permissoes por usuario.

Esses itens ficarao para fases posteriores.

---

## 4. Fontes de dados

| Dataset | Origem | Formato | Atualizacao | Responsavel | Status |
|---|---|---|---|---|---|
| Balancete inicial 12/2024 | ERP / Excel | Excel | Fixo | Contabilidade | Pendente mapear |
| Lancamentos contabeis 2025+ | Oracle ODBC | Query / Excel | Recorrente ou tempo real | Contabilidade / TI | Pendente mapear |
| Plano de contas | ERP Oracle | Query / Excel | Sob demanda | Contabilidade | Pendente mapear |
| Contas auxiliares | ERP Oracle | Query / Excel | Sob demanda | Contabilidade | Pendente mapear |
| Centros de custo | ERP Oracle | Query / Excel | Sob demanda | Controladoria | Pendente mapear |
| De/para DRE | Planilha configuracao | Excel/CSV | Manual | Controladoria | Pendente mapear |
| De/para controladora | Planilha configuracao | Excel/CSV | Manual | Controladoria | Pendente mapear |

---

## 5. Dicionario de dados

Cada dataset devera possuir um dicionario de dados com a seguinte estrutura:

| Campo | Descricao | Tipo esperado | Exemplo | Obrigatorio | Regra de validacao |
|---|---|---|---|---|---|
| conta_contabil | Codigo da conta contabil | Texto | 3.1.01.001 | Sim | Nao pode ser vazio |
| descricao_conta | Nome da conta contabil | Texto | Receita de vendas | Sim | Deve existir no plano de contas |
| data_lancamento | Data contabil | Data | 2025-01-31 | Sim | Deve pertencer ao periodo analisado |
| debito | Valor de debito | Decimal | 1500.00 | Nao | Valor >= 0 |
| credito | Valor de credito | Decimal | 1500.00 | Nao | Valor >= 0 |
| centro_custo | Centro de custo | Texto | ADM | Depende da conta | Validar conforme regra da conta |
| conta_auxiliar | Cliente, fornecedor ou auxiliar | Texto | FORN001 | Nao | Validar existencia na base auxiliar |
| historico | Historico do lancamento | Texto | NF 12345 | Nao | Livre |

---

## 6. Etapa de analise exploratoria dos dados

Antes da construcao dos calculos oficiais, deverao ser executadas as seguintes analises:

### 6.1 Perfil das colunas

Para cada dataset:

- Nome da coluna.
- Tipo identificado automaticamente.
- Tipo esperado.
- Quantidade de linhas preenchidas.
- Quantidade de nulos.
- Percentual de nulos.
- Quantidade de valores distintos.
- Exemplos de valores.
- Valores minimos e maximos, quando aplicavel.

### 6.2 Qualidade dos dados

Validacoes iniciais:

- Contas vazias.
- Datas invalidas.
- Lancamentos sem valor.
- Debito e credito simultaneamente zerados.
- Debito e credito preenchidos na mesma linha, se isso nao for permitido pelo ERP.
- Contas inexistentes no plano de contas.
- Centros de custo inexistentes.
- Contas auxiliares inexistentes.
- Lancamentos fora do periodo.
- Duplicidades potenciais.

### 6.3 Analise contabil preliminar

- Total de debitos por periodo.
- Total de creditos por periodo.
- Diferenca entre debitos e creditos.
- Quantidade de lancamentos por mes.
- Top contas por valor movimentado.
- Top centros de custo por valor movimentado.
- Top fornecedores/clientes por valor movimentado.
- Contas com saldo contrario ao esperado.

---

## 7. Regras de montagem do balancete

### 7.1 Formula base

Saldo final = Saldo inicial + Debitos - Creditos

Essa regra podera variar conforme a natureza da conta, caso a empresa decida apresentar saldos com sinal gerencial.

### 7.2 Regras a validar com a contabilidade

| Regra | Pergunta de validacao | Status |
|---|---|---|
| Natureza da conta | Ativo, passivo, receita, custo ou despesa vem do plano de contas? | Pendente |
| Sinal do saldo | O saldo deve aparecer com sinal contabil ou gerencial? | Pendente |
| Conta auxiliar | Quais contas exigem cliente, fornecedor ou auxiliar? | Pendente |
| Centro de custo | Quais contas exigem centro de custo? | Pendente |
| Encerramento | Existe lancamento de encerramento mensal? | Pendente |
| Periodo aberto | Como tratar mes ainda nao fechado? | Pendente |
| Duplicidade | Qual chave identifica lancamento unico no ERP? | Pendente |

---

## 8. Conciliacoes obrigatorias

### 8.1 Conciliacao do balancete inicial

- Conferir total do balancete de dezembro de 2024.
- Validar se saldos devedores e credores fecham.
- Validar se todas as contas existem no plano de contas.

### 8.2 Conciliacao mensal

Para cada mes:

- Saldo inicial do mes = saldo final do mes anterior.
- Soma dos debitos = soma dos creditos, quando aplicavel ao lote contabil.
- Saldo final calculado = saldo final esperado no balancete do ERP.
- Diferencas devem ser registradas e justificadas.

### 8.3 Amostragem manual

Selecionar amostras para validacao manual:

- 5 contas de ativo.
- 5 contas de passivo.
- 5 contas de receita.
- 5 contas de custo.
- 5 contas de despesa.
- Contas com maior movimentacao.
- Contas com maior variacao percentual.
- Contas com saldo contrario ao esperado.

---

## 9. Processo de atualizacao dos dados

### 9.1 Atualizacao manual inicial

Na fase MVP, os dados poderao ser carregados por Excel/CSV exportado do ERP.

### 9.2 Atualizacao via ODBC

Na fase seguinte, o sistema devera conectar ao Oracle via ODBC e executar queries padronizadas.

### 9.3 Frequencia de atualizacao

Opcoes a definir:

- Manual sob demanda.
- Diario.
- A cada hora.
- Tempo real ou quase tempo real.

### 9.4 Controle de fechamento

O sistema devera diferenciar:

- Periodo aberto.
- Periodo em conferencia.
- Periodo fechado.
- Periodo reprocessado.

---

## 10. Arquitetura proposta

```text
Oracle ODBC / Excel inicial
        ↓
Camada de extracao
        ↓
Analise exploratoria e validacao
        ↓
Base tratada
        ↓
Motor contabil
        ↓
Balancete / DRE / relatorios
        ↓
HTML + CSS + JavaScript
```

---

## 11. Estrutura de pastas

```text
Bi-Contabil/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── etl.py
│   ├── profiling.py
│   ├── validation.py
│   ├── accounting_engine.py
│   └── reports.py
│
├── docs/
│   ├── SDD.md
│   ├── DATA_DICTIONARY.md
│   ├── VALIDATION_RULES.md
│   └── ACCOUNTING_RULES.md
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── config/
│   └── samples/
│
├── templates/
│   ├── balancete.html
│   └── profiling.html
│
├── static/
│   ├── css/
│   └── js/
│
├── tests/
│   ├── test_balancete.py
│   └── test_validations.py
│
├── requirements.txt
└── README.md
```

---

## 12. Entregaveis da fase 1

| Entregavel | Descricao | Status |
|---|---|---|
| SDD inicial | Documento de arquitetura e regras | Criado |
| Dicionario de dados | Mapeamento dos campos dos datasets | Pendente |
| Script de profiling | Analise exploratoria automatica | Pendente |
| Relatorio de qualidade | Nulos, duplicidades, tipos e inconsistencias | Pendente |
| Motor de balancete | Calculo saldo inicial + movimento + saldo final | Pendente |
| Validacao amostral | Conferencia manual com a contabilidade | Pendente |
| Tela HTML inicial | Visualizacao do balancete | Pendente |

---

## 13. Criterios de aceite

O MVP do balancete so sera considerado valido quando:

- O sistema carregar os datasets definidos.
- O dicionario de dados estiver documentado.
- As colunas obrigatorias estiverem mapeadas.
- As validacoes principais forem executadas.
- O balancete mensal calculado fechar com uma amostra validada manualmente.
- As divergencias forem documentadas.
- O usuario aprovar a regra de sinal e apresentacao.

---

## 14. Pendencias para decisao

- Confirmar nomes reais das colunas dos arquivos.
- Confirmar chave unica do lancamento contabil.
- Confirmar regra de sinal por natureza de conta.
- Confirmar se o balancete inicial esta em sinal contabil ou gerencial.
- Confirmar se a movimentacao Oracle ja vem consolidada ou por partida/lancamento.
- Confirmar granularidade desejada: conta, centro de custo, auxiliar, cliente, fornecedor.
- Confirmar frequencia de atualizacao dos dados.
