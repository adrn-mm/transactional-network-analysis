# 🕸️ Transactional Network Analysis

Dashboard **interaktif** untuk mengeksplorasi dan memvisualisasikan **jaringan transaksi keuangan** — siapa bertransaksi dengan siapa, ke mana dana mengalir, dengan nilai dan frekuensi berapa. Dirancang untuk *Social/Transactional Network Analysis (SNA)*: memetakan relasi antar rekening, antar nasabah (CIF), dan antar entitas/ekosistem, lalu menyorot simpul serta pola yang paling berpengaruh — termasuk **deteksi pola berbantuan AI**.

<p align="center">
  <img alt="Python"    src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="PyVis"     src="https://img.shields.io/badge/PyVis-network%20graph-2E74B5">
  <img alt="Plotly"    src="https://img.shields.io/badge/Plotly-sankey-3F4F75?logo=plotly&logoColor=white">
  <img alt="OpenAI"    src="https://img.shields.io/badge/OpenAI-pattern%20analysis-412991?logo=openai&logoColor=white">
</p>

---

## 📌 Ringkasan

Aplikasi membaca **snapshot transaksi bulanan** yang sudah teragregasi (per pasangan rekening/CIF/entitas), lalu menyajikannya sebagai **graph jaringan** dan **diagram Sankey** yang dapat difilter secara interaktif. Selain visualisasi, tersedia **AI Pattern Analysis** untuk merangkum temuan jaringan dan menyorot simpul paling berpengaruh secara otomatis.

Data dibaca dari berkas cache lokal (`data_cache/month=YYYYMM.zip`) yang dihasilkan oleh pipeline data di hulu (data warehouse Hive/Spark) — pipeline itu berada **di luar** repositori ini.

---

## 🌟 Fitur Utama

Dashboard memiliki **5 tab** visualisasi/analisis:

| Tab | Isi |
|---|---|
| **Network Graph** | Graph interaktif (PyVis): simpul = entitas/CIF, sisi (edge) = relasi transaksi, dengan *tooltip* kaya info per simpul. |
| **Sankey: Input Transactions** | Aliran dana **masuk** menuju simpul terpilih (Plotly Sankey). |
| **Sankey: Output Transactions** | Aliran dana **keluar** dari simpul terpilih. |
| **Transaction Summary** | Ringkasan nominal & frekuensi per relasi, dalam bentuk tabel. |
| **AI Pattern Analysis** | Deteksi pola otomatis (OpenAI) + simpul paling berpengaruh (PageRank/Betweenness via NetworkX). |

**Dua perspektif analisis** (dipilih di sidebar):
- **by Ecosystem** — level entitas, dengan kedalaman **Ecosystem → Dinas → Sub Dinas**.
- **by CIF** — level nasabah individual (pilih dari dropdown atau tempel nomor CIF).

**Filter interaktif:**
- **Periode** — pilih **Tahun** & **Bulan** (dari partisi yang tersedia), lalu persempit dengan **rentang tanggal**.
- **Perspektif & simpul** — telusuri jaringan dari entitas/CIF tertentu.

**AI Pattern Analysis** mengklasifikasikan pola menjadi: `ONE_TO_MANY`, `MANY_TO_ONE`, `HIGH_VOLUME_PAIR`, `CYCLICAL_FLOW`, `UNUSUAL_OUTLIER`, lalu menandai simpul kunci tiap pola.

---

## 🏗️ Arsitektur & Alur Data

```
  Pipeline hulu (data warehouse Hive / Spark)         ← di luar repo ini
        │   ETL & agregasi (per pasangan rekening/CIF/entitas)
        ▼
  data_cache/month=YYYYMM.zip                         ← snapshot transaksi bulanan (CSV ter-zip)
  list_partitions/available_partitions.csv            ← daftar bulan (year_month) yang tersedia
        │
        ▼
  app.py (Streamlit)                                  ← Network Graph · Sankey · Summary · AI Analysis
```

- **Cache bulanan** adalah satu file ZIP berisi CSV hasil agregasi untuk satu `year_month`.
- Aplikasi memuat **hanya bulan terpilih**, lalu memfilter berdasarkan rentang tanggal & perspektif.
- Path data dibuat **relatif terhadap lokasi `app.py`** (`BASE_DIR`), jadi portabel antar mesin/folder tanpa mengubah kode.

### Kolom yang dibaca aplikasi

CSV di dalam tiap `month=YYYYMM.zip` diharapkan memuat (antara lain):

| Kolom | Keterangan |
|---|---|
| `dt_id` | Tanggal transaksi |
| `amount` | Nominal transaksi |
| `source_cif` / `dest_cif` | Nomor CIF sisi sumber / tujuan |
| `source_account_no` / `dest_account_no` | Nomor rekening sumber / tujuan |
| `source_customer_name` / `dest_customer_name` | Nama nasabah |
| `source_cif_type_name` / `dest_cif_type_name` | Tipe CIF |
| `source_entity_name` / `dest_entity_name` | Entitas/ekosistem |
| `source_kode_dinas_desc` / `dest_kode_dinas_desc` | Dinas (+ varian sub & sub-sub) |

---

## 📂 Struktur Repository

```
.
├── app.py                              # Aplikasi Streamlit (visualisasi + AI analysis)
├── deploy_app.py                       # Entrypoint runtime (Cloudera Data Science Workbench)
├── requirements.txt                    # Dependensi Python
├── .streamlit/
│   └── config.toml                     # Konfigurasi tema (light theme dipaksa)
├── data_cache/
│   └── month=YYYYMM.zip                # Snapshot transaksi bulanan (cache yang dibaca app)
├── list_partitions/
│   └── available_partitions.csv        # Daftar bulan tersedia (kolom: year_month)
├── lib/                                # Aset front-end PyVis (vis-network, tom-select)
├── filtered_network.html               # Artefak graph yang digenerate PyVis saat runtime
└── README.md
```

---

## 🛠️ Teknologi

- **Python 3.9+** · **Streamlit** (UI dashboard)
- **PyVis** (Network Graph) · **Plotly** (Sankey) · **NetworkX** (PageRank/Betweenness)
- **Pandas** · **Matplotlib** / **Seaborn** · **SciPy**
- **OpenAI** (ringkasan pola berbantuan AI)
- Deploy pada **Cloudera Data Science Workbench (CDSW)**

---

## 🚀 Menjalankan Secara Lokal

```bash
# 1. (opsional) buat & aktifkan virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2. install dependency
pip install -r requirements.txt

# 3. jalankan
streamlit run app.py
```

Aplikasi membaca:
- `list_partitions/available_partitions.csv` — daftar bulan yang tersedia, dan
- `data_cache/month=YYYYMM.zip` — data bulan terpilih.

> Jalankan `streamlit run app.py` dari **folder root project** agar konfigurasi `.streamlit/config.toml` dan path data relatif terbaca dengan benar.

### 🔑 Konfigurasi OpenAI (untuk tab AI Pattern Analysis)

Tab **AI Pattern Analysis** memakai OpenAI lewat `st.secrets`. Buat berkas **`.streamlit/secrets.toml`** (sudah masuk `.gitignore`, jadi tidak ikut ter-commit):

```toml
OPENAI_API_KEY = "sk-..."
```

> Tab lain tetap berfungsi tanpa API key; hanya AI Pattern Analysis yang membutuhkannya.

### 🎨 Tema

Tema **light** dipaksa lewat `.streamlit/config.toml`:

```toml
[theme]
base = "light"
```

Konfigurasi ini mengabaikan preferensi tema OS pengguna, sehingga tampilan konsisten di mesin/folder mana pun.

---

## 🧭 Cara Pakai

1. **Pilih periode** di sidebar — **Tahun** lalu **Bulan**, klik **🔄 Load Data**.
2. (Opsional) persempit dengan **rentang tanggal**.
3. **Pilih perspektif** — *by Ecosystem* atau *by CIF* — dan simpul yang ingin ditelusuri.
4. Jelajahi tab: **Network Graph**, **Sankey (Input/Output)**, **Transaction Summary**.
5. Buka **AI Pattern Analysis** untuk rangkuman pola otomatis (perlu OpenAI key).

---

## ☁️ Deployment (CDSW)

`deploy_app.py` menjalankan aplikasi pada port yang disediakan workbench:

```bash
streamlit run app.py --server.port $CDSW_APP_PORT --server.address 127.0.0.1
```

---

## 🩹 Troubleshooting

| Gejala | Penyebab & solusi |
|---|---|
| **`TypeError: unsupported format string passed to NoneType.__format__`** | Daftar partisi kosong (data tidak ditemukan) sehingga dropdown bulan `None`. Pastikan `list_partitions/available_partitions.csv` (kolom `year_month`) dan `data_cache/month=YYYYMM.zip` ada di folder project. App kini menampilkan peringatan & berhenti dengan rapi alih-alih crash. |
| **"File partition list not found"** | `available_partitions.csv` tidak ada di `list_partitions/`. |
| **"Zip file not found: ...month=YYYYMM.zip"** | Cache bulan terpilih belum tersedia di `data_cache/`. |
| **AI Pattern Analysis error/kosong** | `OPENAI_API_KEY` belum diset di `.streamlit/secrets.toml`. |
| **Tema bukan light** | Pastikan `.streamlit/config.toml` ada dan `streamlit run` dijalankan dari folder root project. |

---

## 📝 Catatan

- Pipeline yang menghasilkan `data_cache/month=YYYYMM.zip` berada di hulu (Hive/Spark) dan **tidak** termasuk dalam repositori ini; repo ini fokus pada **aplikasi dashboard**.
- `filtered_network.html` adalah artefak yang dihasilkan PyVis saat runtime.
