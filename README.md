# Economic Indicators Pipeline

A Python pipeline that extracts the **USD/BRL exchange rate**, the **Selic target rate** and **IPCA inflation** from the Central Bank of Brazil's public APIs, joins the series and loads everything into **Snowflake**, ready to answer questions like:

> *"What was the average dollar rate each month, and what was inflation in that same month?"*

> **Status:** under active development. See the [roadmap](#roadmap).

---

## Tech stack

| Layer | Tools |
|---|---|
| Language | Python |
| Extraction | `requests` |
| Transformation | `pandas` |
| Storage | Snowflake (`snowflake-connector-python`) |

## Key engineering problems

- **API windowing:** splitting long date ranges to respect per-request limits.
- **Resilience:** retries with exponential backoff, and controlled failure on network loss.
- **Joining mixed frequencies:** daily exchange rates, event-driven Selic changes and monthly IPCA.
- **Idempotent writes:** rerunning the pipeline never duplicates rows.
- **Incremental loads:** fetching only the dates not yet stored.

---

## Data sources

The series come from two public APIs of the Central Bank of Brazil (BCB):

| Series | API | Identifier | Frequency | Unit |
|---|---|---|---|---|
| USD/BRL (selling rate) | PTAX | `CotacaoDolarPeriodo` | Daily (business days) | BRL |
| Selic target rate (set by Copom) | SGS | code `432` | Changes at Copom meetings | % per year |
| IPCA (monthly change) | SGS | code `433` | Monthly | % per month |

*Selic is Brazil's benchmark interest rate, set by the Monetary Policy Committee (Copom). IPCA is Brazil's official consumer price index.*

**PTAX** (official exchange rates, OData standard):

```
https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='mm-dd-yyyy'&@dataFinalCotacao='mm-dd-yyyy'&$format=json
```

**SGS** (Time Series Management System):

```
https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json&dataInicial=dd/mm/yyyy&dataFinal=dd/mm/yyyy
```

### API behavior observed in practice

Neither API has formal documentation. The behavior below was mapped through direct testing against the endpoints.

**PTAX**

- **The response is an object, not a list.** Records live in `response["value"]`, with fields such as `cotacaoVenda` (a number) and `dataHoraCotacao` (a date-time string).
- **Dates use the `mm-dd-yyyy` format wrapped in single quotes** in the request, because that is how OData represents a string literal.

**SGS**

- **Values come back as strings.** The response looks like `[{"data": "01/10/2026", "valor": "0.14"}]`, and both `data` and `valor` need to be converted.
- **Dates use the `dd/mm/yyyy` format**, in both the request and the response.
- **A `404` is not always an error.** A period with no data returns `404` with `Value(s) not found` in the body. It should be treated as an empty list and not retried.
- **IPCA is published with a lag.** IBGE (the national statistics office) releases each month's index around the 10th of the following month, so the current month never has an IPCA value.
- **Daily series have a maximum period per request**, so long ranges must be split into request windows.

Because the two APIs return different formats, the transformation step converts both into a common shape (`date`, `value`) before joining the series.

---

## Architecture

```
 ┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
 │   BCB APIs   │ ──▶ │    Extraction    │ ──▶ │   Transformation    │
 │ (PTAX + SGS) │     │ windows + retry  │     │  types, dedup,      │
 └──────────────┘     └──────────────────┘     │  current Selic,     │
                                               │  monthly averages   │
                                               └──────────┬──────────┘
                                                          ▼
                                               ┌─────────────────────┐
                                               │  Load (Snowflake)   │
                                               │  idempotent and     │
                                               │  incremental        │
                                               └─────────────────────┘
```

### Tables

| Table | Contents | Grain |
|---|---|---|
| `raw_series` | Raw data: `codigo`, `data`, `valor` | 1 row per series per date |
| `diario` (daily) | `data`, `dolar`, `selic_vigente` (Selic in effect) | 1 row per day with an exchange rate |
| `mensal` (monthly) | `mes`, `dolar_medio`, `ipca` | 1 row per month |

---

## Getting started

**Requirements:** Python 3.10+ and a Snowflake account (the free trial works).

```bash
git clone <repository-url>
cd Pipeline_indicadores_economicos
pip install requests pandas snowflake-connector-python
```

**Credentials:** the pipeline reads its connection settings from environment variables. Credentials never go in the code or the repository.

| Variable | Example |
|---|---|
| `SNOWFLAKE_ACCOUNT` | `abc12345.sa-east-1` |
| `SNOWFLAKE_USER` | `my_user` |
| `SNOWFLAKE_PASSWORD` | *(your password)* |
| `SNOWFLAKE_WAREHOUSE` | `COMPUTE_WH` |
| `SNOWFLAKE_DATABASE` | `INDICADORES` |
| `SNOWFLAKE_SCHEMA` | `PUBLIC` |

**Current entry point** (extraction):

```bash
python Extract.py
```

**Target CLI** (Stage 5):

```bash
python pipeline.py --desde 2015-01-01
```

---

<!--
## Technical decisions

Uncomment and fill in each item as its stage is completed:

- **Selic in effect for each day:** approach and Big-O complexity.
- **Deduplication and idempotency:** how a rerun never duplicates rows.
- **Incremental load:** how the pipeline finds what is already loaded.
- **Network failures:** retry strategy and protection against partial writes.

---
-->

## Roadmap

- [ ] **Stage 1: Extraction**
  - [x] USD/BRL fetched from the PTAX API
  - [x] Selic and IPCA fetched from the SGS API
  - [ ] Fetch functions for each API with a common `(start, end)` interface
  - [ ] Retry with exponential backoff (1s, 2s, 4s)
  - [ ] Automatic splitting of long periods into windows
- [ ] **Stage 2: Transformation**
  - [ ] Type conversion, with invalid rows discarded and logged
  - [ ] Duplicate removal
  - [ ] Selic in effect for each day with an exchange rate
  - [ ] Monthly average dollar rate + that month's IPCA
- [ ] **Stage 3: Load**: `raw_series`, `diario` and `mensal` tables, with no duplicates
- [ ] **Stage 4: Incremental load**: fetch only the dates not yet in the database
- [ ] **Stage 5: Finishing touches**: CLI, file logging and a run summary

### Extras

- [ ] `pytest` tests for the transformation functions
- [ ] Parallel extraction with `ThreadPoolExecutor`
- [ ] Docker container
