# Fontes de Dados - BI Contabil

## 1. Diretorio local padrao

Os arquivos fonte do projeto devem ser buscados, no ambiente local do usuario, no seguinte diretorio:

```text
C:\Users\mfarias\OneDrive - CRISTALPET\POWER BI\Projetos\Contabilidade\Data driven - Gestão
```

Esse caminho sera usado como parametro padrao dos scripts Python.

---

## 2. Arquivos iniciais identificados

### 2.1 Balancete inicial dezembro/2024

Arquivo enviado:

```text
balancete 12-2024.txt
```

Colunas identificadas:

| Coluna | Descricao preliminar |
|---|---|
| Reduzido | Codigo reduzido da conta ou auxiliar |
| Conta | Codigo estruturado da conta contabil ou codigo auxiliar |
| Denominacao | Nome da conta contabil ou da conta auxiliar |
| Saldo Inicial | Saldo inicial do periodo |
| Debito | Total de debitos no periodo |
| Credito | Total de creditos no periodo |
| Saldo Final | Saldo final do periodo |

Observacoes importantes:

- O arquivo possui linhas de contas contabeis estruturadas, como `1`, `1.1`, `1.1.01`, `1.1.01.01.0001`.
- O arquivo tambem possui linhas auxiliares vinculadas a uma conta contabil superior.
- Linhas auxiliares aparecem com a primeira coluna vazia e codigo auxiliar na coluna `Conta`.
- Os valores estao no padrao brasileiro, com ponto para milhar e virgula decimal.
- O campo `Saldo Final` deve ser conciliado com `Saldo Inicial + Debito - Credito`, sujeito a regra de natureza/sinal da conta.

---

### 2.2 Dataset contabilidade gerencial HTML

Arquivo enviado:

```text
Data set - contabilidade-gerencial-html.xlsx
```

Status:

- Pendente de profiling automatizado.
- Pendente de mapeamento de abas.
- Pendente de identificacao de colunas.
- Pendente de validacao com usuario.

---

## 3. Premissas de carga

Na fase inicial, os scripts devem procurar arquivos Excel, CSV e TXT no diretorio padrao.

Extensoes inicialmente suportadas:

```text
.xlsx
.xls
.csv
.txt
```

---

## 4. Regras preliminares de leitura

### 4.1 TXT do balancete

- Separador esperado: tabulacao.
- Encoding a testar: utf-8-sig, latin1 ou cp1252.
- Numeros em formato brasileiro devem ser convertidos para decimal.

### 4.2 Excel

- Todas as abas devem ser inventariadas.
- Cada aba deve ter profiling separado.
- Nomes de colunas devem ser normalizados para uso interno.

---

## 5. Proximas validacoes com usuario

- Confirmar quais arquivos devem entrar no MVP.
- Confirmar se o balancete 12/2024 deve ser saldo inicial oficial de 2025.
- Confirmar se linhas auxiliares devem aparecer no balancete ou apenas em drill-down.
- Confirmar se o saldo deve ser apresentado no sinal contabil original ou em sinal gerencial.
- Confirmar frequencia de atualizacao do Oracle ODBC.
