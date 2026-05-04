# Modelo de Dados - BI Contabil

## 1. Visao geral

O projeto sera estruturado como um modelo dimensional contabile-gerencial, baseado em uma tabela fato principal de lancamentos contabeis e tabelas dimensao provenientes do ERP Oracle.

A tabela principal sera a **FatoLancamentoContabil**, que devera permitir rastreabilidade ate o lancamento contabil original, incluindo conta contabil, centro de custo, conta auxiliar, historico e valores.

---

## 2. Abas / datasets identificados no arquivo Excel

Arquivo de origem:

```text
Data set - contabilidade-gerencial-html.xlsx
```

### 2.1 FatoLancamentoContabil

Tabela fato com as transacoes contabeis do ERP.

Uso esperado:

- Base principal para montagem do balancete.
- Base para DRE.
- Base para BP.
- Base para analise analitica conta a conta.
- Base para rastreabilidade ate o lancamento original.

Campos esperados a mapear:

- Codigo do lancamento.
- Data do lancamento.
- Conta contabil.
- Conta auxiliar.
- Centro de custo.
- Historico ou descricao do lancamento.
- Valor de debito.
- Valor de credito.
- Documento ou origem do lancamento, se existir.

Ponto critico:

A FatoLancamentoContabil precisa possuir chaves ou campos correlacionaveis com:

- DimConta.
- DimCentroCusto.
- DimContaAux.
- DimItemContaAux.

Especialmente a conta auxiliar deve ser melhorada/tratada para permitir chave estrangeira consistente.

---

### 2.2 DimConta

Tabela do plano de contas contabil, sem abertura de contas auxiliares.

Uso esperado:

- Descricao oficial das contas.
- Hierarquia contabil.
- Identificacao da natureza pela raiz da conta.
- Agrupamento para BP, DRE e custo.

Regra inicial por raiz:

| Raiz da conta | Classificacao inicial | Demonstrativo |
|---|---|---|
| 1 | Ativo | Balanco Patrimonial |
| 2 | Passivo / Patrimonio Liquido | Balanco Patrimonial |
| 3 | Resultado | DRE |
| 4 | Custo de producao | Custo / Gerencial |

---

### 2.3 DimCentroCusto

Tabela de centros de custo cadastrados no ERP.

Uso esperado:

- Validar centros de custo informados nos lancamentos.
- Permitir analise por area, setor ou natureza operacional.
- Apoiar relatorios gerenciais.

---

### 2.4 DimItemContaAux

Tabela de itens de contas auxiliares, como fornecedores, clientes, custos e colaboradores.

Uso esperado:

- Identificar clientes, fornecedores, colaboradores e outros auxiliares.
- Permitir drill-down do balancete por item auxiliar.
- Apoiar analise de contas a receber, fornecedores, adiantamentos e contas correlatas.

Ponto critico:

A FatoLancamentoContabil deve ser enriquecida para possuir uma chave estrangeira confiavel para essa dimensao.

---

### 2.5 DimContaAux

Tabela com a estrutura de contas auxiliares.

Uso esperado:

- Relacionar tipos de contas auxiliares com o plano de contas.
- Identificar quais contas contabeis exigem abertura auxiliar.
- Validar consistencia entre conta contabil e conta auxiliar.

---

### 2.6 paraBR_DRE

Tabela de parametros para estrutura de DRE e Balanco Patrimonial.

Uso esperado:

- Mapear contas contabeis para linhas gerenciais.
- Montar estrutura de DRE.
- Montar estrutura de BP.
- Definir ordem, grupo, subgrupo e exibicao dos reports.

---

### 2.7 Estrutura de conta de custo

Existe uma estrutura complementar para montagem de conta de custo, associada especialmente as contas com raiz 4.

Uso esperado:

- Classificar custos de producao.
- Apoiar analise de custo industrial.
- Relacionar custos com centros de custo, itens auxiliares ou parametros gerenciais.

Observacao:

A aba mencionada pelo usuario foi novamente `DimItemContaAux`, mas deve ser validado se ha outra aba especifica para estrutura de custos.

---

## 3. Desenho dimensional proposto

```text
DimConta
   ↑
   |
FatoLancamentoContabil  → DimCentroCusto
   |
   ├→ DimContaAux
   |
   └→ DimItemContaAux

FatoLancamentoContabil + DimConta + paraBR_DRE
   → Balancete
   → BP
   → DRE
   → Custo de producao
```

---

## 4. Regras iniciais de classificacao

### 4.1 Classificacao por raiz da conta

A classificacao inicial sera feita pelo primeiro caractere do codigo da conta contabil:

| Prefixo | Tratamento inicial |
|---|---|
| 1 | Conta patrimonial - Ativo |
| 2 | Conta patrimonial - Passivo / PL |
| 3 | Conta de resultado - DRE |
| 4 | Conta de custo de producao |

### 4.2 Uso por demonstrativo

| Demonstrativo | Contas utilizadas |
|---|---|
| Balanco Patrimonial | 1 e 2 |
| DRE | 3 |
| Custo de producao | 4 |
| Analise gerencial ampliada | 3 e 4, conforme regra definida |

---

## 5. Validacoes obrigatorias entre fato e dimensoes

### 5.1 Conta contabil

- Toda conta contabil da FatoLancamentoContabil deve existir na DimConta.
- Contas inexistentes devem ser listadas como erro critico.

### 5.2 Centro de custo

- Todo centro de custo informado na FatoLancamentoContabil deve existir na DimCentroCusto.
- Lancamentos sem centro de custo devem ser avaliados conforme exigencia da conta.

### 5.3 Conta auxiliar

- Toda conta auxiliar informada na FatoLancamentoContabil deve conseguir se relacionar com DimContaAux e/ou DimItemContaAux.
- Contas que exigem auxiliar e nao possuem auxiliar devem ser listadas.
- Auxiliares informados em contas que nao deveriam ter auxiliar devem ser analisados.

### 5.4 Parametros DRE/BP

- Toda conta relevante para BP ou DRE deve possuir mapeamento em paraBR_DRE.
- Contas sem mapeamento devem ser apresentadas em relatorio de pendencias.

---

## 6. Saidas esperadas do modelo

### 6.1 Balancete

- Conta contabil.
- Descricao.
- Saldo inicial.
- Debito.
- Credito.
- Saldo final.
- Nivel hierarquico.
- Tipo: sintetica, analitica ou auxiliar.

### 6.2 Balancete analitico

- Conta contabil.
- Conta auxiliar.
- Item auxiliar.
- Centro de custo.
- Historico.
- Documento.
- Data.
- Debito.
- Credito.

### 6.3 BP

- Estrutura conforme paraBR_DRE.
- Ativo.
- Passivo.
- Patrimonio liquido.

### 6.4 DRE

- Estrutura conforme paraBR_DRE.
- Receitas.
- Deducoes.
- Custos.
- Despesas.
- Resultado.

### 6.5 Custo de producao

- Custos por conta.
- Custos por centro de custo.
- Custos por item/estrutura definida.

---

## 7. Pendencias para profiling

O proximo passo tecnico e executar profiling no arquivo Excel para descobrir:

- Nomes reais das abas.
- Nomes reais das colunas.
- Tipos de dados.
- Chaves candidatas.
- Quantidade de linhas por aba.
- Percentual de nulos.
- Relacionamentos possiveis entre fato e dimensoes.
- Contas da fato sem correspondencia na DimConta.
- Centros de custo da fato sem correspondencia na DimCentroCusto.
- Auxiliares da fato sem correspondencia nas dimensoes auxiliares.
