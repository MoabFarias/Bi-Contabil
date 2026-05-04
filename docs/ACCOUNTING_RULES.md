# Regras Contabeis e Gerenciais - BI Contabil

## 1. Regra de classificacao por raiz da conta

| Raiz | Natureza | Uso principal |
|---|---|---|
| 1 | Ativo | Balanco Patrimonial |
| 2 | Passivo / Patrimonio Liquido | Balanco Patrimonial |
| 3 | Resultado | DRE |
| 4 | Custo de producao | Apuracao industrial / estoque |

---

## 2. Regra critica sobre contas 3 e 4

A conta 4 **nao deve ser somada diretamente com a conta 3 para calculo de margem real ou resultado gerencial**.

Motivo:

- As contas 4 representam custos de producao.
- Essas contas sao zeradas mensalmente pela conta 4.2.
- A apuracao do custo de producao e transferida para estoque, em contas do Ativo, raiz 1.
- O impacto no resultado ocorre somente quando o produto e vendido.
- Nesse momento, o custo aparece na conta 3, por meio do CPV / custo de venda.

Portanto:

```text
Margem / DRE = contas de resultado da raiz 3
Custo de producao = analise industrial separada pela raiz 4
```

A conta 4 deve ser usada para analise de formacao de custo, eficiencia industrial e transferencia para estoque, mas nao como componente direto duplicado da DRE.

---

## 3. Tratamento do CPV

O CPV deve ser analisado dentro da conta 3, especialmente nas contas de custo de venda.

Pontos importantes:

- A conta 3 de custo de venda possui conta auxiliar.
- A conta 3 de custo de venda possui centro de custo.
- Conta auxiliar e centro de custo sao essenciais para analisar corretamente CPV, margem e comportamento de custo.

---

## 4. Conta auxiliar na FatoLancamentoContabil

Na aba **FatoLancamentoContabil**, a coluna H representa a conta auxiliar.

No dataset visualizado, as colunas principais da fato incluem:

| Coluna | Uso esperado |
|---|---|
| CODLANC | Codigo do lancamento contabil |
| EMPRESA | Empresa |
| FILIAL | Filial |
| LDATA | Data do lancamento |
| CONTA | Conta contabil |
| COD_VERSAO | Versao do plano/estrutura |
| CCUS | Centro de custo |
| CNT_AUX | Conta auxiliar |
| ITEM_CNTAUX | Item da conta auxiliar |
| VALOR_DEB | Valor de debito |
| VALOR_CRE | Valor de credito |
| VALOR_LIQ | Valor liquido |
| DSC_COMPLEMENTO | Historico / complemento do lancamento |

Regra:

- A coluna `CNT_AUX` deve ser usada para mapear a estrutura da conta auxiliar.
- A coluna `ITEM_CNTAUX` deve ser usada para identificar o item auxiliar especifico, como fornecedor, cliente, colaborador ou outro cadastro.
- O relacionamento deve ser validado com as dimensoes `DimContaAux` e `DimItemContaAux`.

---

## 5. Regra preliminar de valor liquido

A coluna `VALOR_LIQ` aparenta representar o efeito liquido do lancamento.

Regra a validar:

```text
VALOR_LIQ = VALOR_DEB - VALOR_CRE
```

Observacao:

No print analisado, ha exemplo com credito de 450 e valor liquido de -450, o que reforca essa hipotese.

Essa regra precisa ser validada no profiling automatizado.

---

## 6. Regras de demonstrativos

### 6.1 Balanco Patrimonial

Usar contas de raiz:

- 1 - Ativo
- 2 - Passivo / Patrimonio Liquido

### 6.2 DRE

Usar contas de raiz:

- 3 - Resultado

A estrutura de apresentacao deve vir da tabela `paraBR_DRE`.

### 6.3 Custo de producao

Usar contas de raiz:

- 4 - Custo de producao

A analise de custo de producao deve ser separada da DRE, evitando duplicidade de custo.

---

## 7. Validacoes obrigatorias

### 7.1 FatoLancamentoContabil

Validar:

- `CODLANC` preenchido.
- `LDATA` em formato de data.
- `CONTA` preenchida.
- `CONTA` existente em `DimConta`.
- `CCUS` existente em `DimCentroCusto`, quando preenchido.
- `CNT_AUX` existente em `DimContaAux`, quando preenchido.
- `ITEM_CNTAUX` existente em `DimItemContaAux`, quando preenchido.
- `VALOR_LIQ = VALOR_DEB - VALOR_CRE`.

### 7.2 CPV e margem

Validar:

- Contas de CPV dentro da raiz 3.
- Existencia de centro de custo em contas de custo de venda quando aplicavel.
- Existencia de conta auxiliar em contas de CPV quando aplicavel.

### 7.3 Conta 4

Validar:

- Contas da raiz 4 devem zerar mensalmente apos apuracao.
- Transferencia para estoque deve ser conciliada com contas do Ativo.
- Conta 4 nao deve ser somada diretamente na DRE.
