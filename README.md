# 🕸️ Transactional Network Analysis

An **interactive dashboard** for exploring and visualizing **financial transaction networks** — who transacts with whom, where money flows, and at what value and frequency. Built for *Social/Transactional Network Analysis (SNA)*: mapping relationships between accounts, customers (CIF), and entities/ecosystems, then surfacing the most influential nodes and patterns — including **AI-assisted pattern detection**.

<p align="center">
  <img alt="Python"    src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="PyVis"     src="https://img.shields.io/badge/PyVis-network%20graph-2E74B5">
  <img alt="Plotly"    src="https://img.shields.io/badge/Plotly-sankey-3F4F75?logo=plotly&logoColor=white">
  <img alt="OpenAI"    src="https://img.shields.io/badge/OpenAI-pattern%20analysis-412991?logo=openai&logoColor=white">
</p>

---

## 📌 Overview

The app reads **pre-aggregated monthly transaction snapshots** (per account/CIF/entity pair) and presents them as an interactive **network graph** and **Sankey diagrams** that can be filtered on the fly. Beyond visualization, an **AI Pattern Analysis** automatically summarizes network findings and highlights the most influential nodes.

Data is read from a local cache file (`data_cache/month=YYYYMM.zip`) produced by an upstream data pipeline (a Hive/Spark data warehouse) — that pipeline lives **outside** this repository.

---

## 🌟 Key Features

The dashboard has **5 tabs** for visualization and analysis:

| Tab | What it shows |
|---|---|
| **Network Graph** | Interactive graph (PyVis): nodes = entities/CIFs, edges = transaction relationships, with rich per-node tooltips. |
| **Sankey: Input Transactions** | Inbound money flows **into** the selected node (Plotly Sankey). |
| **Sankey: Output Transactions** | Outbound money flows **out of** the selected node. |
| **Transaction Summary** | Per-relationship summary of amounts and frequencies, as a table. |
| **AI Pattern Analysis** | Automatic pattern detection (OpenAI) + most influential node (PageRank/Betweenness via NetworkX). |

**Two analysis perspectives** (chosen in the sidebar):
- **by Ecosystem** — entity level, drilling down **Ecosystem → Dinas → Sub Dinas**.
- **by CIF** — individual customer level (pick from a dropdown or paste a CIF number).

**Interactive filters:**
- **Period** — pick a **Year** and **Month** (from available partitions), then narrow with a **date range**.
- **Perspective & node** — explore the network starting from a specific entity/CIF.

**AI Pattern Analysis** classifies patterns into: `ONE_TO_MANY`, `MANY_TO_ONE`, `HIGH_VOLUME_PAIR`, `CYCLICAL_FLOW`, `UNUSUAL_OUTLIER`, and flags the key node(s) for each pattern.

---

## 🏗️ Architecture & Data Flow

```
  Upstream pipeline (Hive / Spark data warehouse)     ← outside this repo
        │   ETL & aggregation (per account/CIF/entity pair)
        ▼
  data_cache/month=YYYYMM.zip                         ← monthly transaction snapshot (zipped CSV)
  list_partitions/available_partitions.csv            ← list of available months (year_month)
        │
        ▼
  app.py (Streamlit)                                  ← Network Graph · Sankey · Summary · AI Analysis
```

- Each **monthly cache** is a single ZIP containing the aggregated CSV for one `year_month`.
- The app loads **only the selected month**, then filters by date range and perspective.
- Data paths are resolved **relative to `app.py`** (`BASE_DIR`), so the app is portable across machines/folders with no code changes.

### Columns the app reads

The CSV inside each `month=YYYYMM.zip` is expected to include (among others):

| Column | Description |
|---|---|
| `dt_id` | Transaction date |
| `amount` | Transaction amount |
| `source_cif` / `dest_cif` | Source / destination CIF number |
| `source_account_no` / `dest_account_no` | Source / destination account number |
| `source_customer_name` / `dest_customer_name` | Customer name |
| `source_cif_type_name` / `dest_cif_type_name` | CIF type |
| `source_entity_name` / `dest_entity_name` | Entity / ecosystem |
| `source_kode_dinas_desc` / `dest_kode_dinas_desc` | Department (plus sub & sub-sub variants) |

---

## 📂 Repository Structure

```
.
├── app.py                              # Streamlit app (visualization + AI analysis)
├── deploy_app.py                       # Runtime entrypoint (Cloudera Data Science Workbench)
├── requirements.txt                    # Python dependencies
├── .streamlit/
│   └── config.toml                     # Theme config (light theme enforced)
├── data_cache/
│   └── month=YYYYMM.zip                # Monthly transaction snapshot (the cache the app reads)
├── list_partitions/
│   └── available_partitions.csv        # List of available months (column: year_month)
├── lib/                                # PyVis front-end assets (vis-network, tom-select)
├── filtered_network.html               # Graph artifact generated by PyVis at runtime
└── README.md
```

---

## 🛠️ Tech Stack

- **Python 3.9+** · **Streamlit** (dashboard UI)
- **PyVis** (Network Graph) · **Plotly** (Sankey) · **NetworkX** (PageRank/Betweenness)
- **Pandas** · **Matplotlib** / **Seaborn** · **SciPy**
- **OpenAI** (AI-assisted pattern summaries)
- Deployed on **Cloudera Data Science Workbench (CDSW)**

---

## 🚀 Running Locally

```bash
# 1. (optional) create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2. install dependencies
pip install -r requirements.txt

# 3. run
streamlit run app.py
```

The app reads:
- `list_partitions/available_partitions.csv` — the list of available months, and
- `data_cache/month=YYYYMM.zip` — the data for the selected month.

> Run `streamlit run app.py` from the **project root** so that `.streamlit/config.toml` and the relative data paths resolve correctly.

### 🔑 OpenAI configuration (for the AI Pattern Analysis tab)

The **AI Pattern Analysis** tab uses OpenAI via `st.secrets`. Create a **`.streamlit/secrets.toml`** file (already in `.gitignore`, so it won't be committed):

```toml
OPENAI_API_KEY = "sk-..."
```

> The other tabs work without an API key; only AI Pattern Analysis requires it.

### 🎨 Theme

A **light** theme is enforced via `.streamlit/config.toml`:

```toml
[theme]
base = "light"
```

This overrides the user's OS theme preference, keeping the look consistent across any machine/folder.

---

## 🧭 How to Use

1. **Pick a period** in the sidebar — **Year** then **Month**, and click **🔄 Load Data**.
2. (Optional) narrow down with a **date range**.
3. **Choose a perspective** — *by Ecosystem* or *by CIF* — and the node to explore.
4. Browse the tabs: **Network Graph**, **Sankey (Input/Output)**, **Transaction Summary**.
5. Open **AI Pattern Analysis** for an automatic pattern summary (requires an OpenAI key).

---

## ☁️ Deployment (CDSW)

`deploy_app.py` runs the app on the port provided by the workbench:

```bash
streamlit run app.py --server.port $CDSW_APP_PORT --server.address 127.0.0.1
```

---

## 🩹 Troubleshooting

| Symptom | Cause & fix |
|---|---|
| **`TypeError: unsupported format string passed to NoneType.__format__`** | The partition list is empty (no data found), so the month dropdown is `None`. Make sure `list_partitions/available_partitions.csv` (column `year_month`) and `data_cache/month=YYYYMM.zip` exist in the project folder. The app now shows a warning and stops gracefully instead of crashing. |
| **"File partition list not found"** | `available_partitions.csv` is missing from `list_partitions/`. |
| **"Zip file not found: ...month=YYYYMM.zip"** | The cache for the selected month is not present in `data_cache/`. |
| **AI Pattern Analysis errors / empty** | `OPENAI_API_KEY` is not set in `.streamlit/secrets.toml`. |
| **Theme is not light** | Make sure `.streamlit/config.toml` exists and `streamlit run` is launched from the project root. |

---

## 📝 Notes

- The pipeline that produces `data_cache/month=YYYYMM.zip` runs upstream (Hive/Spark) and is **not** part of this repository; this repo focuses on the **dashboard application**.
- `filtered_network.html` is an artifact generated by PyVis at runtime.
