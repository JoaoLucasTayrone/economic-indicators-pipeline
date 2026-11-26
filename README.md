# Pipeline de Indicadores Econômicos

Pipeline em Python que extrai **cotação do dólar**, **Meta Selic** e **IPCA** da API pública do Banco Central, cruza as séries e armazena tudo no **Snowflake**, pronto para responder perguntas como:

> *"Qual foi o dólar médio de cada mês e quanto foi a inflação naquele mês?"*

> 🚧 **Projeto em desenvolvimento.** Veja o [roadmap](#roadmap) para o que já está pronto.

---

## Por que este projeto existe

É um projeto de estudo em engenharia de dados, construído à mão, com regras restritivas de propósito:

- **Sem pandas.** Toda transformação é feita com listas, dicionários e sets, o que obriga a pensar em estrutura de dados e complexidade.
- **Só `requests` + biblioteca padrão** (`datetime`, `logging`, `json`, `argparse`...), além do conector oficial do banco.
- **Snowflake** como destino dos dados, para praticar a carga num data warehouse em nuvem.

O objetivo é praticar os fundamentos que uma ferramenta pronta esconderia: paginação de API, retry, deduplicação, junção de séries com frequências diferentes, idempotência e carga incremental.

---

## Fontes de dados

As séries vêm de duas APIs públicas do Banco Central:

| Série | API | Identificador | Frequência | Unidade |
|---|---|---|---|---|
| Dólar (venda) | PTAX | `CotacaoDolarPeriodo` | Diária (dias úteis) | R$ |
| Meta Selic (Copom) | SGS | código `432` | Muda nas reuniões do Copom | % a.a. |
| IPCA (variação mensal) | SGS | código `433` | Mensal | % no mês |

**PTAX** (cotações oficiais de câmbio, padrão OData):

```
https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='mm-dd-aaaa'&@dataFinalCotacao='mm-dd-aaaa'&$format=json
```

**SGS** (Sistema Gerenciador de Séries Temporais):

```
https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=dd/mm/aaaa&dataFinal=dd/mm/aaaa
```

### Comportamentos das APIs observados na prática

As APIs não têm documentação formal, então estes pontos foram descobertos testando.

**PTAX**

- **A resposta é um objeto, não uma lista.** Os registros ficam em `resposta["value"]`, com campos como `cotacaoVenda` (número) e `dataHoraCotacao` (texto com data e hora).
- **As datas usam o formato `mm-dd-aaaa` entre aspas simples** na requisição, porque é assim que o OData representa um texto literal.

**SGS**

- **Os valores vêm como string.** A resposta é `[{"data": "01/10/2026", "valor": "0.14"}]`, e tanto `data` quanto `valor` precisam ser convertidos.
- **As datas usam o formato `dd/mm/aaaa`**, tanto na requisição quanto na resposta.
- **Um `404` nem sempre é erro.** Um período sem dados devolve `404` com `Value(s) not found` no corpo, e isso deve ser tratado como lista vazia, sem retry.
- **O IPCA tem defasagem.** O IBGE divulga o índice de um mês por volta do dia 10 do mês seguinte, então o mês corrente nunca tem IPCA.
- **Há um limite de período por consulta** nas séries diárias, o que exige quebrar intervalos longos em janelas. *(Limite exato: a documentar.)*

Como as duas APIs têm formatos diferentes, a transformação converte as duas para uma estrutura comum (`data`, `valor`) antes de cruzar as séries.

---

## Arquitetura

```
 ┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
 │  API do BCB  │ ──▶ │    Extração      │ ──▶ │   Transformação     │
 │ (PTAX + SGS) │     │  janelas + retry │     │  tipos, dedup,      │
 └──────────────┘     └──────────────────┘     │  Selic vigente,     │
                                               │  médias mensais     │
                                               └──────────┬──────────┘
                                                          ▼
                                               ┌─────────────────────┐
                                               │  Carga (Snowflake)  │
                                               │  idempotente e      │
                                               │  incremental        │
                                               └─────────────────────┘
```

### Tabelas

| Tabela | Conteúdo | Granularidade |
|---|---|---|
| `raw_series` | Dados brutos: `codigo`, `data`, `valor` | 1 linha por série por data |
| `diario` | `data`, `dolar`, `selic_vigente` | 1 linha por dia com cotação |
| `mensal` | `mes`, `dolar_medio`, `ipca` | 1 linha por mês |

---

## Como rodar

**Pré-requisitos:** Python 3.10+ e uma conta Snowflake (o trial gratuito serve).

```bash
git clone <url-do-repositorio>
cd Pipeline_indicadores_economicos
pip install requests snowflake-connector-python
```

**Credenciais:** o pipeline lê a conexão de variáveis de ambiente. As credenciais nunca ficam no código nem no repositório.

| Variável | Exemplo |
|---|---|
| `SNOWFLAKE_ACCOUNT` | `abc12345.sa-east-1` |
| `SNOWFLAKE_USER` | `meu_usuario` |
| `SNOWFLAKE_PASSWORD` | *(sua senha)* |
| `SNOWFLAKE_WAREHOUSE` | `COMPUTE_WH` |
| `SNOWFLAKE_DATABASE` | `INDICADORES` |
| `SNOWFLAKE_SCHEMA` | `PUBLIC` |

**Hoje** (extração exploratória):

```bash
python Extract.py
```

**Quando o pipeline estiver completo:**

```bash
python pipeline.py --desde 2015-01-01
```

---

## Decisões técnicas

> Seção preenchida conforme cada etapa é concluída.

- **Selic vigente por dia (Desafio 1):** *a documentar: abordagem escolhida e complexidade Big-O.*
- **Deduplicação e idempotência:** *a documentar: como rodar duas vezes não duplica linhas.*
- **Carga incremental:** *a documentar: como o pipeline descobre o que já está no banco.*
- **Falhas de rede:** *a documentar: estratégia de retry e como o banco é protegido de escrita parcial.*

---

## Roadmap

- [ ] **Etapa 1: Extração**
  - [x] Dólar consumido da API PTAX
  - [x] Selic e IPCA consumidos da API SGS
  - [ ] Funções de busca para cada API, com interface comum `(inicio, fim)`
  - [ ] Retry com backoff exponencial (1s, 2s, 4s)
  - [ ] Quebra automática de períodos longos em janelas
- [ ] **Etapa 2: Transformação**
  - [ ] Conversão de tipos com descarte e log de linhas inválidas
  - [ ] Remoção de duplicados
  - [ ] Selic vigente para cada dia com cotação
  - [ ] Dólar médio mensal + IPCA do mês
- [ ] **Etapa 3: Carga**: tabelas `raw_series`, `diario` e `mensal`, sem duplicação
- [ ] **Etapa 4: Carga incremental**: buscar só as datas que ainda não estão no banco
- [ ] **Etapa 5: Acabamento**: CLI, log em arquivo e resumo da execução

### Extras

- [ ] Testes com `pytest` para as funções de transformação
- [ ] Extração paralela com `ThreadPoolExecutor`
- [ ] Container Docker
