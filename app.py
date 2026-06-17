import streamlit as st
import pandas as pd
import zipfile
from pyvis.network import Network
import plotly.graph_objects as go
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from datetime import datetime
import os
import tempfile
import matplotlib.pyplot as plt
import seaborn as sns
import openai
import json
import networkx as nx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="Transactional Network Analysis", page_icon="🕸️", layout="wide")
st.title("🕸️ Transactional Network Analysis")

# ------------------- AI Prompt -------------------
# GANTI FUNGSI LAMA ANDA DENGAN VERSI BARU INI

# Jangan lupa import networkx di bagian atas file Anda
import networkx as nx

# GANTI FUNGSI LAMA ANDA DENGAN VERSI BARU INI
def find_most_influential_node(df, nodes, src_col, dst_col, method='pagerank'):
    """
    Menemukan node paling berpengaruh menggunakan berbagai metode centrality.
    Metode yang tersedia: 'amount', 'betweenness', 'pagerank'.
    """
    if not nodes or df.empty:
        return None

    # Filter hanya untuk transaksi yang relevan dengan node yang terlibat
    # Ini penting agar centrality dihitung dalam konteks pola yang ditemukan AI
    relevant_df = df[df[src_col].isin(nodes) | df[dst_col].isin(nodes)]
    if relevant_df.empty:
        return nodes[0]

    # --- Metode 1: Berdasarkan Total Amount (Cara Lama) ---
    if method == 'amount':
        source_amounts = relevant_df.groupby(src_col)['amount'].sum()
        dest_amounts = relevant_df.groupby(dst_col)['amount'].sum()
        total_amounts = source_amounts.add(dest_amounts, fill_value=0)
        relevant_amounts = total_amounts.reindex(nodes).fillna(0)
        if relevant_amounts.sum() == 0: return nodes[0]
        return relevant_amounts.idxmax()

    # --- Metode Canggih Menggunakan NetworkX ---
    # Buat graph dari DataFrame
    G = nx.from_pandas_edgelist(
        relevant_df,
        source=src_col,
        target=dst_col,
        edge_attr='amount',
        create_using=nx.DiGraph() # Gunakan Directed Graph karena transaksi punya arah
    )

    # Pastikan semua 'involved_nodes' ada di graph, tambahkan jika belum ada
    for node in nodes:
        if not G.has_node(node):
            G.add_node(node)

    centrality_scores = {}

    # --- Metode 2: Betweenness Centrality (Si Pialang) ---
    if method == 'betweenness':
        # Bobot diinversi agar transaksi besar dianggap 'jarak pendek'
        # Namun untuk simplisitas, kita hitung tanpa bobot agar fokus pada struktur
        centrality_scores = nx.betweenness_centrality(G, normalized=True)

    # --- Metode 3: PageRank Centrality (Si Paling Populer) ---
    elif method == 'pagerank':
        centrality_scores = nx.pagerank(G, alpha=0.85, weight='amount')

    if not centrality_scores:
        return nodes[0] # Fallback

    # Filter skor hanya untuk node yang ada di `involved_nodes`
    relevant_scores = {node: score for node, score in centrality_scores.items() if node in nodes}
    
    if not relevant_scores:
        return nodes[0] # Fallback

    # Kembalikan node dengan skor centrality tertinggi
    return max(relevant_scores, key=relevant_scores.get)

def generate_network_summary_for_ai(df_filtered, edge_data, display_name, node_type, src_col, dst_col):
    """Menyusun data jaringan dan meminta output JSON yang sangat terstruktur, termasuk node pusat."""
    
    total_transactions = len(df_filtered)
    total_amount = df_filtered['amount'].sum()
    
    if edge_data.empty:
        flows_amount_str = "Tidak ada aliran dana yang signifikan."
        flows_freq_str = "Tidak ada aliran dana yang signifikan."
    else:
        top_5_flows_amount = edge_data.sort_values('total_amount', ascending=False).head(5)
        flows_amount_str = "\n".join([f"- Dari '{row[src_col]}' ke '{row[dst_col]}': Rp {row['total_amount']:,.0f}" for _, row in top_5_flows_amount.iterrows()])
        top_5_flows_freq = edge_data.sort_values('frequency', ascending=False).head(5)
        flows_freq_str = "\n".join([f"- Dari '{row[src_col]}' ke '{row[dst_col]}': {int(row['frequency'])} transaksi" for _, row in top_5_flows_freq.iterrows()])

    # PROMPT BARU DENGAN INSTRUKSI LEBIH TEGAS DAN PERMINTAAN 'central_node'
    prompt = f"""
    Analisis Konteks:
    - Perspektif Analisis: {node_type}
    - Fokus Utama: Node '{display_name}'
    - Periode Waktu: Dari {df_filtered['dt_id'].min().date()} hingga {df_filtered['dt_id'].max().date()}
    - Total Nilai Transaksi: Rp {total_amount:,.0f}
    - Aliran Dana Terbesar:
    {flows_amount_str}
    - Aliran Dana Paling Sering:
    {flows_freq_str}

    TUGAS ANDA:
    Bertindaklah sebagai analis keuangan forensik. Identifikasi 2 hingga 4 pola transaksi paling menarik.

    INSTRUKSI FORMAT OUTPUT (WAJIB DIIKUTI):
    Anda HARUS mengembalikan respons HANYA dalam format sebuah JSON OBJECT tunggal. JSON object ini WAJIB memiliki sebuah key tunggal bernama "patterns", di mana value-nya adalah sebuah LIST dari beberapa object.
    Setiap object di dalam list "patterns" harus memiliki kunci-kunci berikut:
    1. "pattern_title": Judul singkat yang menarik.
    2. "pattern_type": Klasifikasi pola. Pilih dari: "ONE_TO_MANY", "MANY_TO_ONE", "HIGH_VOLUME_PAIR", "CYCLICAL_FLOW", "UNUSUAL_OUTLIER".
    3. "involved_nodes": Sebuah list berisi SEMUA nama node yang relevan dengan pola ini.
    4. "central_node": Nama node yang menjadi PUSAT dari pola. Untuk "ONE_TO_MANY", ini adalah sumbernya. Untuk "MANY_TO_ONE", ini adalah tujuannya. Untuk "HIGH_VOLUME_PAIR", bisa diisi dengan salah satu dari dua node. Untuk pola lain tanpa pusat yang jelas, isi dengan string kosong (""). INI SANGAT PENTING.
    5. "explanation": Penjelasan detail mengapa pola ini menarik dan rekomendasi investigasi.

    CONTOH OUTPUT JSON YANG BENAR:
    {{
      "patterns": [
        {{
          "pattern_title": "Distribusi Gaji dari Dinas Pendidikan",
          "pattern_type": "ONE_TO_MANY",
          "involved_nodes": ["DINAS PENDIDIKAN", "Karyawan A", "Karyawan B"],
          "central_node": "DINAS PENDIDIKAN",
          "explanation": "Terdeteksi satu sumber utama 'DINAS PENDIDIKAN' yang mengirimkan dana ke banyak tujuan. Ini khas dengan pola pembayaran gaji."
        }}
      ]
    }}

    PENTING: Pastikan output Anda adalah JSON object tunggal yang valid, dimulai dengan `{{` dan diakhiri dengan `}}`.
    """
    return prompt

@st.cache_data(show_spinner=False)
def get_ai_analysis_json(summary_prompt):
    """Mengirim prompt ke OpenAI, meminta JSON, dan mengembalikannya sebagai objek Python."""
    try:
        openai.api_key = st.secrets["OPENAI_API_KEY"]
        client = openai.OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Anda adalah seorang analis keuangan ahli yang mengembalikan output HANYA dalam format JSON yang valid sesuai instruksi."},
                {"role": "user", "content": summary_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000,
        )
        
        response_content = response.choices[0].message.content
        parsed_json = json.loads(response_content)
        
        # --- LOGIKA PARSING BARU YANG LEBIH CERDAS ---
        # Jika respons sudah berupa list, langsung kembalikan.
        if isinstance(parsed_json, list):
            return parsed_json
            
        # Jika berupa dictionary, cari value yang merupakan list (ini menangani kasus {"patterns": [...]})
        if isinstance(parsed_json, dict):
            for key, value in parsed_json.items():
                if isinstance(value, list):
                    return value # Ditemukan list-nya, kembalikan
        
        # Jika tidak ditemukan format yang benar, kembalikan sebagai error format
        return {"error": "Format JSON dari AI tidak sesuai (bukan list atau dict berisi list).", "raw_response": response_content}

    except json.JSONDecodeError as e:
        return {"error": f"Gagal mem-parsing JSON dari AI: {e}", "raw_response": response_content}
    except Exception as e:
        return {"error": f"Terjadi kesalahan saat menghubungi OpenAI API: {e}"}

# ------------------- UI & Sidebar -------------------
@st.cache_data(show_spinner=False)
def get_available_partitions():
    # Path relatif terhadap lokasi app.py agar portabel antar mesin/folder.
    local_path = os.path.join(BASE_DIR, "list_partitions", "available_partitions.csv")
    # Check if the file exists
    if not os.path.exists(local_path):
        st.warning(f"File partition list not found at {local_path}")
        return []
    try:
        # Read CSV into Pandas DataFrame
        df_pandas = pd.read_csv(local_path)
        # Clean and get unique year_month
        return sorted(df_pandas["year_month"].dropna().astype(int).unique().tolist())
    except Exception as e:
        st.error(f"Failed to read CSV file: {e}")
        return []

# Dynamic dropdown from Hive partitions
available_ym = get_available_partitions()

# Get the latest year_month from available partitions
if available_ym:
    latest_ym = max(available_ym)
    default_year = int(str(latest_ym)[:4])
    default_month = int(str(latest_ym)[4:6])

    # Set default value to session state if not already present
    if "year" not in st.session_state:
        st.session_state["year"] = default_year
    if "month" not in st.session_state:
        st.session_state["month"] = default_month

year_options = sorted(set(int(str(ym)[:4]) for ym in available_ym), reverse=True)

with st.sidebar.form("form_filter"):
    selected_year = st.selectbox("Select Year", year_options, key="year")
    month_options = sorted(set(int(str(ym)[4:]) for ym in available_ym if str(ym).startswith(str(selected_year))))
    selected_month = st.selectbox("Select Month", month_options, key="month")
    load_data = st.form_submit_button("🔄 Load Data")

if not available_ym or selected_year is None or selected_month is None:
    st.warning(
        "Tidak ada partisi data yang tersedia. Pastikan "
        "`list_partitions/available_partitions.csv` ada (berisi kolom `year_month`) "
        "dan data `data_cache/month=YYYYMM.zip` tersedia di folder project."
    )
    st.stop()

selected_ym = int(f"{selected_year}{selected_month:02}")

# ------------------- Load Data -------------------
@st.cache_data(show_spinner=False)
def load_data_from_month(ym: int):
    # Path relatif terhadap lokasi app.py agar portabel antar mesin/folder.
    local_zip_file = os.path.join(BASE_DIR, "data_cache", f"month={ym}.zip")

    if not os.path.exists(local_zip_file):
        st.error(f"❌ Zip file not found: {local_zip_file}")
        return None

    try:
        # Open ZIP and directly read the first CSV file within it
        with zipfile.ZipFile(local_zip_file, 'r') as zip_ref:
            csv_list = [f for f in zip_ref.namelist() if f.endswith(".csv")]
            if not csv_list:
                st.error("❌ No CSV file found within the ZIP.")
                return None

            # Read directly from the ZIP file (without extraction)
            with zip_ref.open(csv_list[0]) as csv_file:
                df = pd.read_csv(csv_file)
                df['dt_id'] = pd.to_datetime(df['dt_id'], errors='coerce')
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                # Clean account no to remove ".0"
                df['source_account_no'] = (
                    df['source_account_no']
                    .fillna('')
                    .astype(str)
                    .str.strip()
                    .str.replace(r'\.0$', '', regex=True)
                    .str.replace(r'^nan$', '', regex=True)
                )

                df['dest_account_no'] = (
                    df['dest_account_no']
                    .fillna('')
                    .astype(str)
                    .str.strip()
                    .str.replace(r'\.0$', '', regex=True)
                    .str.replace(r'^nan$', '', regex=True)
                )

                return df

    except Exception as e:
        st.error(f"❌ Failed to load data from ZIP: {e}")
        return None

# If no data in session_state and partitions are available, auto-load latest data
if "data" not in st.session_state and available_ym:
    selected_ym = int(f"{st.session_state['year']}{st.session_state['month']:02}")
    with st.spinner(f"🔄 Auto-loading latest data for {selected_ym}..."):
        df = load_data_from_month(selected_ym)
        if df is not None:
            st.session_state["data"] = df

if "data" not in st.session_state:
    st.session_state["data"] = None

if load_data:
    with st.spinner(f"Loading data for {selected_ym}..."):
        df = load_data_from_month(selected_ym)
        if df is None:
            st.warning("❌ No data available.")
            st.stop()
        st.session_state["data"] = df

data = st.session_state["data"]
if data is None:
    st.info("📂 Please load data first using the sidebar.")
    st.stop()

# ------------------- Date Filter -------------------
min_d = data['dt_id'].dropna().min().date()
max_d = data['dt_id'].dropna().max().date()
# Ensure min_d is less than or equal to max_d, and set max_d to today if it's in the future
today = datetime.now().date()
if max_d > today:
    max_d = today
if min_d > max_d:
    min_d = max_d


node_type = st.sidebar.radio("Choose Perspective", ["by Ecosystem", "by CIF"])
start_date = st.sidebar.date_input("Start Date", min_d)
end_date = st.sidebar.date_input("End Date", max_d)

if start_date > end_date:
    st.error("End date must be after start date.")
    st.stop()

filtered_data = data[(data['dt_id'].dt.date >= start_date) & (data['dt_id'].dt.date <= end_date)]

# ------------------- Network Visualization -------------------
@st.cache_data(show_spinner=False)
def create_network_visualization(filtered_data, node_type, src_col_net, dst_col_net, full_data=None, 
                                 selected_entity_filter=None, selected_dinas_filter=None, selected_sub_dinas_filter=None):
    net = Network(height="550px", width="100%", bgcolor="white", font_color="black", directed=True)
    
    # Initialize color map based on Entity Name (always)
    node_color_map_by_entity = {}
    # Include 'Other Banks' here to allow it to be colored and appear in the legend
    all_entities = pd.unique(full_data[['source_entity_name', 'dest_entity_name']].values.ravel('K'))
    all_entities = [e for e in all_entities if pd.notnull(e)] 
    
    # Ensure a consistent colormap even if some entities are filtered out later
    cmap = cm.get_cmap('tab20', max(1, len(all_entities))) 
    for i, entity in enumerate(all_entities):
        node_color_map_by_entity[entity] = mcolors.to_hex(cmap(i))
            
    edge_data = (
        filtered_data
        .groupby([src_col_net, dst_col_net])
        .agg(
            total_amount=('amount', 'sum'),
            frequency=('amount', 'count'),
            transaction_types=('jenis_transaksi', lambda x: ', '.join(sorted(set(x.dropna())))),
            group_channels=('group_channel', lambda x: ', '.join(sorted(set(x.dropna()))))
        )
        .reset_index()
    )

    added_nodes = set()
    node_info_cache = {}

    def clean_node(val):
        return str(int(val)) if pd.notnull(val) and isinstance(val, float) else str(val)

    def build_cif_node_info(cif: str):
        if cif in node_info_cache:
            return node_info_cache[cif]

        lookup_data = full_data if full_data is not None else filtered_data
        rel = lookup_data[(lookup_data['source_cif'] == cif) | (lookup_data['dest_cif'] == cif)]

        # Get information from source first, if empty then from destination
        def get_column_value(src_col, dest_col):
            val_src = rel[rel['source_cif'] == cif][src_col].dropna().unique()
            
            val = [] # Initialize val as an empty list
            if len(val_src) == 0:
                val = rel[rel['dest_cif'] == cif][dest_col].dropna().unique()
            else:
                val = val_src # If val_src has content, use it for val
                
            return val[0] if len(val) > 0 else "-"

        name = get_column_value("source_customer_name", "dest_customer_name")
        cif_type = get_column_value("source_cif_type_name", "dest_cif_type_name")
        entity = get_column_value("source_entity_name", "dest_entity_name")
        dinas = get_column_value("source_kode_dinas_desc", "dest_kode_dinas_desc")
        sub_dinas = get_column_value("source_kode_sub_dinas_desc", "dest_kode_sub_dinas_desc")
        sub_sub_dinas = get_column_value("source_kode_sub_sub_dinas_desc", "dest_kode_sub_sub_dinas_desc")

        acc_no_src = rel[rel['source_cif'] == cif]['source_account_no'].dropna().astype(str).unique().tolist()
        acc_no_dest = rel[rel['dest_cif'] == cif]['dest_account_no'].dropna().astype(str).unique().tolist()
        account_numbers = [
            acc for acc in set(acc_no_src + acc_no_dest)
            if acc and acc != "0"
        ]

        title = (
            f"CIF: {cif} ({cif_type})\n"
            f"Name: {name}\n"
            f"Account No: {', '.join(account_numbers) if account_numbers else '-'}\n"
            f"Ecosystem: {entity}\n"
            f"Dinas: {dinas}\n"
            f"Sub Dinas: {sub_dinas}\n"
            f"Sub Sub Dinas: {sub_sub_dinas}"
        )
        
        node_info_cache[cif] = title
        return title

    # New function to build node info for Ecosystem perspective (adjusted)
    def build_ecosystem_node_info(node_value: str, node_level_col: str, full_data: pd.DataFrame,
                                  selected_entity_filter: str, selected_dinas_filter: str, selected_sub_dinas_filter: str):
        
        # Define a helper to get unique values from both source/dest columns
        def get_unique_values_for_tooltip(df_rel, src_col, dest_col):
            values = pd.concat([
                df_rel[src_col].dropna(),
                df_rel[dest_col].dropna()
            ]).astype(str).unique().tolist()
            return ", ".join(sorted(filter(None, values))) if values else "-"

        # Start with full_data (for month) and apply current date filters
        # Further refine this data by the *global* entity/dinas/sub_dinas filters *if they are not the level of the node itself*
        rel_data_context = full_data.copy()

        # Apply global entity filter if the node level is Dinas or Sub Dinas
        if node_level_col != 'source_entity_name' and selected_entity_filter and selected_entity_filter != "Unknown":
            rel_data_context = rel_data_context[
                (rel_data_context['source_entity_name'] == selected_entity_filter) |
                (rel_data_context['dest_entity_name'] == selected_entity_filter)
            ]
        
        # Apply global dinas filter if the node level is Sub Dinas
        if node_level_col != 'source_kode_dinas_desc' and selected_dinas_filter and selected_dinas_filter != "-":
            rel_data_context = rel_data_context[
                (rel_data_context['source_kode_dinas_desc'] == selected_dinas_filter) |
                (rel_data_context['dest_kode_dinas_desc'] == selected_dinas_filter)
            ]

        # Filter 'rel_data_context' specifically for the current 'node_value'
        if node_level_col == 'source_entity_name':
            rel_data = rel_data_context[(rel_data_context['source_entity_name'] == node_value) | (rel_data_context['dest_entity_name'] == node_value)]
            ecosystem_info = node_value # The node itself is the Ecosystem
            dinas_info = get_unique_values_for_tooltip(rel_data, 'source_kode_dinas_desc', 'dest_kode_dinas_desc')
            sub_dinas_info = get_unique_values_for_tooltip(rel_data, 'source_kode_sub_dinas_desc', 'dest_kode_sub_dinas_desc')
            sub_sub_dinas_info = get_unique_values_for_tooltip(rel_data, 'source_kode_sub_sub_dinas_desc', 'dest_kode_sub_sub_dinas_desc')
            cif_info = get_unique_values_for_tooltip(rel_data, 'source_cif', 'dest_cif')

        elif node_level_col == 'source_kode_dinas_desc':
            rel_data = rel_data_context[(rel_data_context['source_kode_dinas_desc'] == node_value) | (rel_data_context['dest_kode_dinas_desc'] == node_value)]
            ecosystem_info = selected_entity_filter if selected_entity_filter and selected_entity_filter != "Unknown" else get_unique_values_for_tooltip(rel_data, 'source_entity_name', 'dest_entity_name')
            dinas_info = node_value # The node itself is the Dinas
            sub_dinas_info = get_unique_values_for_tooltip(rel_data, 'source_kode_sub_dinas_desc', 'dest_kode_sub_dinas_desc')
            sub_sub_dinas_info = get_unique_values_for_tooltip(rel_data, 'source_kode_sub_sub_dinas_desc', 'dest_kode_sub_sub_dinas_desc')
            cif_info = get_unique_values_for_tooltip(rel_data, 'source_cif', 'dest_cif')

        elif node_level_col == 'source_kode_sub_dinas_desc':
            rel_data = rel_data_context[(rel_data_context['source_kode_sub_dinas_desc'] == node_value) | (rel_data_context['dest_kode_sub_dinas_desc'] == node_value)]
            ecosystem_info = selected_entity_filter if selected_entity_filter and selected_entity_filter != "Unknown" else get_unique_values_for_tooltip(rel_data, 'source_entity_name', 'dest_entity_name')
            dinas_info = selected_dinas_filter if selected_dinas_filter and selected_dinas_filter != "-" else get_unique_values_for_tooltip(rel_data, 'source_kode_dinas_desc', 'dest_kode_dinas_desc')
            sub_dinas_info = node_value # The node itself is the Sub Dinas
            sub_sub_dinas_info = get_unique_values_for_tooltip(rel_data, 'source_kode_sub_sub_dinas_desc', 'dest_kode_sub_sub_dinas_desc')
            cif_info = get_unique_values_for_tooltip(rel_data, 'source_cif', 'dest_cif')
        else:
            return f"Node: {node_value}" # Fallback for unexpected node_level_col

        title = (
            f"Ecosystem: {ecosystem_info}\n"
            f"Dinas: {dinas_info}\n"
            f"Sub Dinas: {sub_dinas_info}\n"
            f"Sub Sub Dinas: {sub_sub_dinas_info}\n"
            f"CIFs: {cif_info}"
        )
        return title

    # Function to get entity name for a given node (CIF, Entity Name, or Dinas)
    def get_entity_for_node(node_value, node_type, full_data, src_col_net):
        if node_type == 'by CIF':
            # For CIF, find its associated entity name
            entity = full_data[
                (full_data['source_cif'] == node_value)
            ]['source_entity_name'].dropna().unique()
            if len(entity) == 0:
                entity = full_data[
                    (full_data['dest_cif'] == node_value)
                ]['dest_entity_name'].dropna().unique()
            return entity[0] if len(entity) > 0 else "Unknown"
        elif src_col_net == 'source_entity_name':
            # If the network is built on entity names, the node_value IS the entity name
            return node_value
        elif src_col_net == 'source_kode_dinas_desc':
            # If the network is built on dinas, find the associated entity name for that dinas
            entity = full_data[
                (full_data['source_kode_dinas_desc'] == node_value)
            ]['source_entity_name'].dropna().unique()
            if len(entity) == 0:
                entity = full_data[
                    (full_data['dest_kode_dinas_desc'] == node_value)
                ]['dest_entity_name'].dropna().unique()
            return entity[0] if len(entity) > 0 else "Unknown"
        elif src_col_net == 'source_kode_sub_dinas_desc': # Added for Sub Dinas
            entity = full_data[
                (full_data['source_kode_sub_dinas_desc'] == node_value)
            ]['source_entity_name'].dropna().unique()
            if len(entity) == 0:
                entity = full_data[
                    (full_data['dest_kode_sub_dinas_desc'] == node_value)
                ]['dest_entity_name'].dropna().unique()
            return entity[0] if len(entity) > 0 else "Unknown"
        return "Unknown" # Fallback

    for _, row in edge_data.iterrows():
        src_node = clean_node(row[src_col_net])
        dst_node = clean_node(row[dst_col_net])

        # Determine color for source node
        src_entity = get_entity_for_node(src_node, node_type, full_data, src_col_net)
        src_color = node_color_map_by_entity.get(src_entity, "#cccccc") # Default grey if entity not found or 'Other Banks'

        if src_node not in added_nodes:
            # Modified this line to pass filter values to build_ecosystem_node_info
            title = build_cif_node_info(src_node) if node_type == 'by CIF' else \
                    build_ecosystem_node_info(src_node, src_col_net, full_data, 
                                              selected_entity_filter, selected_dinas_filter, selected_sub_dinas_filter)
            net.add_node(src_node, label=src_node, title=title, color=src_color)
            added_nodes.add(src_node) 

        # Determine color for destination node
        dst_entity = get_entity_for_node(dst_node, node_type, full_data, src_col_net)
        dst_color = node_color_map_by_entity.get(dst_entity, "#cccccc")

        if dst_node not in added_nodes:
            # Modified this line to pass filter values to build_ecosystem_node_info
            title = build_cif_node_info(dst_node) if node_type == 'by CIF' else \
                    build_ecosystem_node_info(dst_node, src_col_net, full_data, 
                                              selected_entity_filter, selected_dinas_filter, selected_sub_dinas_filter)
            net.add_node(dst_node, label=dst_node, title=title, color=dst_color)
            added_nodes.add(dst_node) 

        edge_title = (
                f"Frequency: {row['frequency']}\n"
                f"Total Amount: Rp.{row['total_amount']:,.2f}\n"
                f"Transaction: {row['transaction_types']}\n"
                f"Channel: {row['group_channels']}"
            )
        net.add_edge(src_node, dst_node, value=row['frequency'], title=edge_title, width=row['frequency'])

    return net, edge_data, node_color_map_by_entity # Return the entity-based color map

# ------------------- Sankey Visualization -------------------
@st.cache_data(show_spinner=False)
def create_sankey_visualization(sankey_data, src_col, dst_col): # Receives src_col and dst_col
    # Ensure amount column is valid
    sankey_data['amount'] = pd.to_numeric(sankey_data['amount'], errors='coerce')
    sankey_data = sankey_data.dropna(subset=['amount'])

    # Remove self-loops (source & destination are the same)
    sankey_data = sankey_data[sankey_data[src_col] != sankey_data[dst_col]]

    # Group and get top-N edges by amount (optional: limit for speed)
    sankey_data = sankey_data.groupby([src_col, dst_col], as_index=False)['amount'].sum()
    sankey_data = sankey_data.sort_values('amount', ascending=False).head(500)   # 💡 Limit if needed

    # Build unique node index
    all_nodes = pd.unique(sankey_data[[src_col, dst_col]].values.ravel('K')).tolist()
    node_idx = {node: i for i, node in enumerate(all_nodes)}

    # Mapping source, target, and value
    sankey_source = sankey_data[src_col].map(node_idx).tolist()
    sankey_target = sankey_data[dst_col].map(node_idx).tolist()
    sankey_value = sankey_data['amount'].tolist()

    # Custom node colors
    custom_colors = [
        "#FF6F61", "#6B5B95", "#88B04B", "#F7CAC9", "#92A8D1",
        "#955251", "#B565A7", "#009B77", "#DD4124", "#45B8AC"
    ]
    node_colors = [custom_colors[i % len(custom_colors)] for i, _ in enumerate(all_nodes)] # Changed to use all_nodes length

    # Function to blend link colors based on origin & destination
    def blend_color(c1, c2):
        r1, g1, b1 = mcolors.to_rgb(c1)
        r2, g2, b2 = mcolors.to_rgb(c2)
        return mcolors.to_hex(((r1 + r2) / 2, (g1 + g2) / 2, (b1 + b2) / 2))

    link_colors = [blend_color(node_colors[s], node_colors[t]) for s, t in zip(sankey_source, sankey_target)]

    # Create sankey chart
    return go.Figure(go.Sankey(
        node=dict(label=all_nodes, color=node_colors, pad=20, thickness=30, line=dict(color="gray", width=0.5)),
        link=dict(source=sankey_source, target=sankey_target, value=sankey_value, color=link_colors)
    )).update_layout(height=600, font_size=12)


# ------------------- Filter by Node Logic -------------------
# Initialize variables for columns to be used outside the if/else block
selected_node_value = None
filter_mask = pd.Series([True] * len(filtered_data), index=filtered_data.index) # Default mask without filter

# Initialize empty or default DataFrame if no filter applies
filtered_network_data = pd.DataFrame(columns=filtered_data.columns)
input_data = pd.DataFrame(columns=filtered_data.columns)
output_data = pd.DataFrame(columns=filtered_data.columns)

# Initialize summary variables for "by CIF" case
name = "-"
cif_type = "-"
account_str = "-"
selected_entity = "-"
selected_kode_dinas = "-"
selected_kode_sub_dinas = "-"
selected_kode_sub_sub_dinas = "-"

# Initialize ecosystem-specific filter variables to a safe default
selected_entity_name = None
selected_dinas_desc = None
selected_sub_dinas_desc = None


# Default columns for network and sankey (will be overwritten if Ecosystem is chosen)
src_col_net_global = 'source_cif'
dst_col_net_global = 'dest_cif'
src_col_sankey_global = 'source_cif'
dst_col_sankey_global = 'dest_cif'
display_name = "CIF" # Default for CIF

if node_type == "by CIF":
    unique_nodes = sorted(set(filtered_data['source_cif'].dropna().astype(str)) | set(filtered_data['dest_cif'].dropna().astype(str)))
    
    col1, col2 = st.columns([2, 3])

    with col1:
        dropdown_cif = st.selectbox("Select a CIF", unique_nodes, key="cif_dropdown_manual")

    with col2:
        pasted_cif = st.text_input("Or paste CIF here (will override dropdown if valid)", key="cif_paste_manual")

    # Final selected_cif based on priority: paste > dropdown
    if pasted_cif.strip() and pasted_cif in unique_nodes:
        selected_node_value = pasted_cif
    elif pasted_cif.strip() and pasted_cif not in unique_nodes:
        st.warning("⚠️ CIF not found in the list.")
        selected_node_value = dropdown_cif
    else:
        selected_node_value = dropdown_cif
    
    # Get all transactions related to this CIF
    related_data = filtered_data[(filtered_data['source_cif'] == selected_node_value) | (filtered_data['dest_cif'] == selected_node_value)]

    # --- FUNCTION get_related_info (Fixed) ---
    def get_related_info(df_rel, cif_val, src_col, dest_col):
        val_src = df_rel[df_rel['source_cif'] == cif_val][src_col].dropna().unique()
        
        val = [] # Initialize val as an empty list
        if len(val_src) == 0:
            val = df_rel[df_rel['dest_cif'] == cif_val][dest_col].dropna().unique()
        else:
            val = val_src # If val_src has content, use it for val
            
        return val[0] if len(val) > 0 else "-"
    # --- END OF FUNCTION get_related_info ---

    selected_entity = get_related_info(related_data, selected_node_value, 'source_entity_name', 'dest_entity_name')
    selected_kode_dinas = get_related_info(related_data, selected_node_value, 'source_kode_dinas_desc', 'dest_kode_dinas_desc')
    selected_kode_sub_dinas = get_related_info(related_data, selected_node_value, 'source_kode_sub_dinas_desc', 'dest_kode_sub_dinas_desc')
    selected_kode_sub_sub_dinas = get_related_info(related_data, selected_node_value, 'source_kode_sub_sub_dinas_desc', 'dest_kode_sub_sub_dinas_desc')


    # Get CIF information
    name_lookup = related_data[related_data['source_cif'] == selected_node_value]['source_customer_name'].dropna().unique()
    name = name_lookup[0] if len(name_lookup) else "-"

    cif_type_lookup = related_data[related_data['source_cif'] == selected_node_value]['source_cif_type_name'].dropna().unique()
    cif_type = cif_type_lookup[0] if len(cif_type_lookup) else "-"

    account_numbers = pd.concat([
        related_data[related_data['source_cif'] == selected_node_value]['source_account_no'],
        related_data[related_data['dest_cif'] == selected_node_value]['dest_account_no']
    ]).dropna().unique()
    account_str = ", ".join(map(str, account_numbers))

    # Display small markdown
    col1, col2, col3 = st.columns(3)

    with col1:
        cif_value = selected_node_value
        st.markdown(f"""
        <div style="font-size:13px; line-height:1.6;">
        <b>Name</b>: {name}<br>
        <b>CIF</b>: {cif_value} ({cif_type})<br>
        <b>Account No</b>: {account_str if account_str else "-"}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="font-size:13px; line-height:1.6;">
        <b>Ecosystem</b>: {selected_entity if selected_entity else "-"}<br>
        <b>Dinas</b>: {selected_kode_dinas if selected_kode_dinas else "-"}
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="font-size:13px; line-height:1.6;">
        <b>Sub Dinas</b>: {selected_kode_sub_dinas if selected_kode_sub_dinas else "-"}<br>
        <b>Sub Sub Dinas</b>: {selected_kode_sub_sub_dinas if selected_kode_sub_sub_dinas else "-"}
        </div>
        """, unsafe_allow_html=True)

    # Basic filter based on CIF
    filter_mask = (filtered_data['source_cif'] == selected_node_value) | (filtered_data['dest_cif'] == selected_node_value)
    
    # Input/output data should still be from filtered_data, not strictly filtered cif_filtered_data
    input_data_base = filtered_data[filtered_data['dest_cif'] == selected_node_value]
    output_data_base = filtered_data[filtered_data['source_cif'] == selected_node_value]

    # Final data for visualization
    filtered_network_data = filtered_data[filter_mask]
    input_data = input_data_base
    output_data = output_data_base

else: # node_type == "by Ecosystem"
    
    # Dropdown 1 and 2 in one row
    col_level, col_entity = st.columns(2)

    with col_level:
        ecosystem_level_choice = st.selectbox(
            "Select Filter Level:", 
            ["Ecosystem", "Dinas", "Sub Dinas"], # Added "Sub Dinas"
            key="ecosystem_level_choice"
        )

    with col_entity:
        # Dropdown 2: entity_name (always present), Remove "Other Banks" from selectable options
        all_entity_names_for_dropdown = sorted(set(filtered_data['source_entity_name'].dropna().astype(str)) | 
                                               set(filtered_data['dest_entity_name'].dropna().astype(str)))
        
        unique_entity_names_for_dropdown = [e for e in all_entity_names_for_dropdown if e != 'Other Banks']
        
        if not unique_entity_names_for_dropdown:
            st.info("No Entity Names available for this date (after removing 'Other Banks').")
            filtered_network_data = pd.DataFrame(columns=filtered_data.columns)
            input_data = pd.DataFrame(columns=filtered_data.columns)
            output_data = pd.DataFrame(columns=filtered_data.columns)
            st.stop() 

        selected_entity_name = st.selectbox(
            "Select Ecosystem Name:", unique_entity_names_for_dropdown, key="select_entity_name"
        )

    # Dropdown 3: Dinas appears conditionally
    selected_dinas_desc = "-" # Default
    if ecosystem_level_choice == "Dinas" or ecosystem_level_choice == "Sub Dinas": # Condition updated
        # Get dinas from source_kode_dinas_desc if source_entity_name matches
        dinas_from_source = filtered_data[
            filtered_data['source_entity_name'] == selected_entity_name
        ]['source_kode_dinas_desc'].dropna().astype(str).tolist()

        # Get dinas from dest_kode_dinas_desc if dest_entity_name matches
        dinas_from_dest = filtered_data[
            filtered_data['dest_entity_name'] == selected_entity_name
        ]['dest_kode_dinas_desc'].dropna().astype(str).tolist()

        # Combine and get unique values
        unique_dinas_desc = sorted(list(set(dinas_from_source + dinas_from_dest)))
        
        if not unique_dinas_desc:
            st.info(f"No Dinas available for '{selected_entity_name}'.")
            st.selectbox("Select Dinas Name:", ["-"], key="select_dinas_desc_disabled", disabled=True)
        else:
            selected_dinas_desc = st.selectbox(
                "Select Dinas Name:", unique_dinas_desc, key="select_dinas_desc"
            )

    # Dropdown 4: Sub Dinas appears conditionally
    selected_sub_dinas_desc = "-" # Default
    if ecosystem_level_choice == "Sub Dinas":
        # Get sub dinas based on selected entity and dinas
        sub_dinas_from_source = filtered_data[
            (filtered_data['source_entity_name'] == selected_entity_name) &
            (filtered_data['source_kode_dinas_desc'] == selected_dinas_desc)
        ]['source_kode_sub_dinas_desc'].dropna().astype(str).tolist()

        sub_dinas_from_dest = filtered_data[
            (filtered_data['dest_entity_name'] == selected_entity_name) &
            (filtered_data['dest_kode_dinas_desc'] == selected_dinas_desc)
        ]['dest_kode_sub_dinas_desc'].dropna().astype(str).tolist()

        unique_sub_dinas_desc = sorted(list(set(sub_dinas_from_source + sub_dinas_from_dest)))

        if not unique_sub_dinas_desc:
            st.info(f"No Sub Dinas available for '{selected_entity_name}' and '{selected_dinas_desc}'.")
            st.selectbox("Select Sub Dinas Name:", ["-"], key="select_sub_dinas_desc_disabled", disabled=True)
        else:
            selected_sub_dinas_desc = st.selectbox(
                "Select Sub Dinas Name:", unique_sub_dinas_desc, key="select_sub_dinas_desc"
            )


    # --- Global Column and Filter Mask Settings ---
    
    if ecosystem_level_choice == "Ecosystem":
        src_col_net_global = 'source_entity_name'
        dst_col_net_global = 'dest_entity_name'
        src_col_sankey_global = 'source_entity_name'
        dst_col_sankey_global = 'dest_entity_name'
        display_name = selected_entity_name 
        selected_node_value = selected_entity_name # Set selected_node_value for Ecosystem
        filter_mask = (filtered_data['source_entity_name'] == selected_entity_name) | \
                      (filtered_data['dest_entity_name'] == selected_entity_name)
    elif ecosystem_level_choice == "Dinas":
        src_col_net_global = 'source_kode_dinas_desc'
        dst_col_net_global = 'dest_kode_dinas_desc'
        src_col_sankey_global = 'source_kode_dinas_desc'
        dst_col_sankey_global = 'dest_kode_dinas_desc'
        display_name = selected_dinas_desc 
        selected_node_value = selected_dinas_desc # Set selected_node_value for Dinas
        
        filter_mask = (
            ((filtered_data['source_entity_name'] == selected_entity_name) & 
             (filtered_data['source_kode_dinas_desc'] == selected_dinas_desc)) | 
            ((filtered_data['dest_entity_name'] == selected_entity_name) & 
             (filtered_data['dest_kode_dinas_desc'] == selected_dinas_desc))
        )
        # If no specific dinas is selected (i.e., it's "-"), revert to filtering only by entity name
        if selected_dinas_desc == "-":
            filter_mask = (filtered_data['source_entity_name'] == selected_entity_name) | \
                          (filtered_data['dest_entity_name'] == selected_entity_name)
            selected_node_value = selected_entity_name # If dinas is "-", then the "selected node" is the entity
    else: # ecosystem_level_choice == "Sub Dinas"
        src_col_net_global = 'source_kode_sub_dinas_desc'
        dst_col_net_global = 'dest_kode_sub_dinas_desc'
        src_col_sankey_global = 'source_kode_sub_dinas_desc'
        dst_col_sankey_global = 'dest_kode_sub_dinas_desc'
        display_name = selected_sub_dinas_desc
        selected_node_value = selected_sub_dinas_desc

        filter_mask = (
            ((filtered_data['source_entity_name'] == selected_entity_name) &
             (filtered_data['source_kode_dinas_desc'] == selected_dinas_desc) &
             (filtered_data['source_kode_sub_dinas_desc'] == selected_sub_dinas_desc)) |
            ((filtered_data['dest_entity_name'] == selected_entity_name) &
             (filtered_data['dest_kode_dinas_desc'] == selected_dinas_desc) &
             (filtered_data['dest_kode_sub_dinas_desc'] == selected_sub_dinas_desc))
        )
        # If no specific sub dinas is selected (i.e., it's "-"), revert to filtering by entity and dinas
        if selected_sub_dinas_desc == "-":
            filter_mask = (
                ((filtered_data['source_entity_name'] == selected_entity_name) & 
                 (filtered_data['source_kode_dinas_desc'] == selected_dinas_desc)) | 
                ((filtered_data['dest_entity_name'] == selected_entity_name) & 
                 (filtered_data['dest_kode_dinas_desc'] == selected_dinas_desc))
            )
            selected_node_value = selected_dinas_desc # If sub dinas is "-", then the "selected node" is the dinas

    # Final DataFrame for visualization
    filtered_network_data = filtered_data[filter_mask]

    # Determine input_data and output_data based on updated global columns
    if filtered_network_data.empty or selected_node_value == "-": 
        input_data = pd.DataFrame(columns=filtered_data.columns)
        output_data = pd.DataFrame(columns=filtered_data.columns)
        # Reset specific info for ecosystem
        name = "-"
        cif_type = "-"
        account_str = "-"
        selected_entity = selected_entity_name # This is the entity name, not selected_entity
        selected_kode_dinas = selected_dinas_desc if ecosystem_level_choice in ["Dinas", "Sub Dinas"] else "-"
        selected_kode_sub_dinas = selected_sub_dinas_desc if ecosystem_level_choice == "Sub Dinas" else "-"
        selected_kode_sub_sub_dinas = "-"
    else:
        input_data = filtered_network_data[filtered_network_data[dst_col_sankey_global] == selected_node_value]
        output_data = filtered_network_data[filtered_network_data[src_col_sankey_global] == selected_node_value]
        # For Ecosystem/Dinas, some CIF details might not be directly applicable
        if node_type == "by Ecosystem":
            name = "-" # Name is only for CIFs
            cif_type = "-"
            account_str = "-"
            selected_entity = selected_entity_name
            selected_kode_dinas = selected_dinas_desc if ecosystem_level_choice in ["Dinas", "Sub Dinas"] else "-"
            selected_kode_sub_dinas = selected_sub_dinas_desc if ecosystem_level_choice == "Sub Dinas" else "-"
            selected_kode_sub_sub_dinas = "-"


# ------------------- Tabs for Visualization -------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Network Graph", 
    "Sankey: Input Transactions", 
    "Sankey: Output Transactions", 
    "Transaction Summary",
    "AI Pattern Analysis"
])

with tab1:
    # Check if filtered_network_data is empty before creating visualization
    if filtered_network_data.empty:
        st.info("No connections found for the selected node in this date range.")
    else:
        # Pass dynamically selected columns to the create_network_visualization function
        net, edge_data, node_color_map_for_legend = create_network_visualization( # Retrieve node_color_map_by_entity
            filtered_network_data, 
            node_type, 
            src_col_net_global, 
            dst_col_net_global, 
            full_data=data, # Use 'data' (full dataset) for CIF info lookup
            selected_entity_filter=selected_entity_name, # Pass the filter values
            selected_dinas_filter=selected_dinas_desc,
            selected_sub_dinas_filter=selected_sub_dinas_desc
        )

        # Save HTML file to a unique temporary file (per session)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as tmpfile:
            net.save_graph(tmpfile.name)
            html_content = open(tmpfile.name).read()
            # --- Changes here: Legend font size and padding ---
            legend_html = "<div style='position:absolute;top:10px;left:10px;z-index:1000;padding:5px;background:white;border:1px solid gray;font-size:10px;'>" 
            
            for entity, color in sorted(node_color_map_for_legend.items()):
                legend_html += f"<div style='margin-bottom:2px'><span style='display:inline-block;width:10px;height:10px;background:{color};margin-right:4px;border-radius:2px'></span>{entity}</div>"
            # ----------------------------------------------------------------------
            
            legend_html += "</div>"
            html_content = html_content.replace("</body>", legend_html + "</body>")

        # Delete file after content is read
        os.remove(tmpfile.name)        
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.components.v1.html(html_content, height=750)
        with col2:
            st.markdown(f"**Network Connections:** {len(edge_data)}")
            st.markdown(f"**Total Frequency:** {filtered_network_data['amount'].count()}")
            st.markdown(f"**Total Amount:** Rp.{filtered_network_data['amount'].sum():,.2f}")
            with st.expander("📋 Show Detailed Data", expanded=False):
                selected_cols = [
                "source_cif", "source_account_no", "source_customer_name", "source_cif_type_name",
                "source_entity_name", "source_kode_dinas", "source_kode_dinas_desc",
                "source_kode_sub_dinas", "source_kode_sub_dinas_desc", "source_kode_sub_sub_dinas", "source_kode_sub_sub_dinas_desc",
                "dest_cif", "dest_account_no", "dest_customer_name", "dest_cif_type_name",
                "dest_entity_name", "dest_kode_dinas", "dest_kode_dinas_desc",
                "dest_kode_sub_dinas", "dest_kode_sub_dinas_desc", "dest_kode_sub_sub_dinas", "dest_kode_sub_sub_dinas_desc",
                "transaction_name", "jenis_transaksi", "amount", "dt_id", "group_channel"
                ]

                st.dataframe(
                    filtered_network_data[selected_cols].sort_values('dt_id', ascending=False).reset_index(drop=True),
                    use_container_width=True
                )

for title, df_raw, key in zip(["Input Transactions", "Output Transactions"], [input_data, output_data], ['input', 'output']):
    with (tab2 if key == 'input' else tab3):
        st.subheader(title)
        st.markdown("""<style>text { fill: white !important; font-weight: bold; text-shadow: 0 0 3px black; }</style>""", unsafe_allow_html=True)

        # Get source and destination columns from global variables
        src_col, dst_col = src_col_sankey_global, dst_col_sankey_global

        # Check if the columns used for sankey are in df_raw
        if src_col not in df_raw.columns or dst_col not in df_raw.columns:
            st.info(f"Columns '{src_col}' or '{dst_col}' not found in {title} transaction data. Cannot display Sankey Diagram.")
            continue # Continue to the next iteration

        # Clean data: remove nulls and self-loops
        df_clean = df_raw.dropna(subset=['amount', src_col, dst_col])
        df_clean = df_clean[df_clean[src_col] != df_clean[dst_col]]

        unique_src = df_clean[src_col].nunique()
        unique_dst = df_clean[dst_col].nunique()

        if df_clean.empty or min(unique_src, unique_dst) < 1:
            st.info(
                f"""
                ⚠️ Unable to display Sankey Diagram for **{title}**.

                This may happen because the selected node has:
                - No incoming or outgoing transactions, **or**
                - Only self-transactions or missing key fields.

                Please try selecting another node or adjust your filters.
                """
            )
        else:
            # Pass the appropriate columns to the create_sankey_visualization function
            fig = create_sankey_visualization(df_clean, src_col, dst_col)
            st.plotly_chart(fig, use_container_width=True, key=f'{key}_sankey')

with tab4:
    # --- Function to format numbers ---
    def format_amount(amount):
        if pd.isna(amount):
            return "-"
        if amount >= 1_000_000_000_000:
            return f"Rp.{amount / 1_000_000_000_000:.1f} T"
        elif amount >= 1_000_000_000:
            return f"Rp.{amount / 1_000_000_000:.1f} M"
        elif amount >= 1_000_000:
            return f"Rp.{amount / 1_000_000:.1f} JT" # JT for Juta (Million)
        else:
            return f"Rp.{amount:,.0f}"

    # Check if filtered_network_data is empty
    if filtered_network_data.empty:
        st.info("No transaction data matching the selected filters to display in the summary.")
    else:
        # Time Series Summary
        time_series = filtered_network_data.copy()
        time_series["date"] = time_series["dt_id"].dt.date
        summary_daily = time_series.groupby("date").agg(
            total_amount=("amount", "sum"),
            transaction_count=("amount", "count")
        ).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Total Amount per Day**")
            # Using Matplotlib/Seaborn with dots
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.lineplot(x="date", y="total_amount", data=summary_daily, ax=ax, marker='o') # Added marker='o'
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: format_amount(x)))
            ax.tick_params(axis='x', rotation=45)
            plt.xlabel("Date")
            plt.ylabel("Total Amount")
            st.pyplot(fig) # Display the matplotlib figure
            plt.close(fig) # Close the figure to prevent display issues

        with col2:
            st.markdown("**Transaction Count per Day**")
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.lineplot(x="date", y="transaction_count", data=summary_daily, ax=ax, marker='o') # Added marker='o'
            ax.tick_params(axis='x', rotation=45)
            plt.xlabel("Date")
            plt.ylabel("Transaction Count")
            st.pyplot(fig)
            plt.close(fig) # Close the figure to prevent display issues

        st.markdown("---")

with tab5:
    container = st.container(border=True)

    # Inisialisasi edge_data jika belum ada
    if 'edge_data' not in locals() and not filtered_network_data.empty:
        edge_data = filtered_network_data.groupby([src_col_net_global, dst_col_net_global]).agg(
            total_amount=('amount', 'sum'), frequency=('amount', 'count')
        ).reset_index()
    elif filtered_network_data.empty:
        edge_data = pd.DataFrame()

    if container.button("🔍 Analisis Jaringan dengan AI", type="primary", use_container_width=True):
        if 'ai_patterns' in st.session_state:
            del st.session_state['ai_patterns']
        with st.spinner("🧠 AI sedang berpikir keras... Menganalisis jutaan kemungkinan..."):
            summary = generate_network_summary_for_ai(
                filtered_network_data, edge_data, display_name, node_type, 
                src_col_net_global, dst_col_net_global
            )
            ai_patterns = get_ai_analysis_json(summary)
            if isinstance(ai_patterns, list) and all(isinstance(item, dict) for item in ai_patterns):
                st.session_state['ai_patterns'] = ai_patterns
                st.session_state['selected_pattern_index'] = 0
                st.rerun()
            else:
                st.session_state['ai_patterns'] = None
                error_detail = "Format respons tidak terduga."
                raw_response = None
                if isinstance(ai_patterns, dict):
                    error_detail = ai_patterns.get('error', error_detail)
                    raw_response = ai_patterns.get('raw_response')
                st.error(f"Gagal mendapatkan analisis dari AI. Detail: {error_detail}")
                if raw_response:
                    st.text_area("Respons Mentah AI", raw_response, height=200)
                else:
                    st.json(ai_patterns)

    # Tampilkan hasil jika sudah ada di session state
    if 'ai_patterns' in st.session_state and st.session_state['ai_patterns'] is not None:
        patterns = st.session_state['ai_patterns']
        
        if not patterns:
            st.success("✅ Analisis Selesai. AI tidak menemukan pola yang cukup signifikan untuk dilaporkan.")
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                pattern_titles = [p.get('pattern_title', f'Pola Tanpa Nama {i+1}') for i, p in enumerate(patterns)]
                selected_index = st.selectbox(
                    "Pola Menarik yang Ditemukan AI:", 
                    options=range(len(pattern_titles)),
                    format_func=lambda i: f"💡 {pattern_titles[i]}", 
                    key='selected_pattern_index'
                )
            with col2:
                influence_method = st.selectbox(
                    "Metode Penentuan Node Berpengaruh:",
                    options=['pagerank', 'betweenness', 'amount'],
                    format_func=lambda x: {'pagerank': 'PageRank (Pengaruh Relasional)', 'betweenness': 'Betweenness (Peran Pialang)', 'amount': 'Total Nominal (Sederhana)'}[x],
                    help="Pilih cara untuk menentukan node pusat dari sebuah pola. PageRank menemukan 'tujuan populer', Betweenness menemukan 'jembatan/perantara'."
                )

            selected_pattern = patterns[selected_index]
            involved_nodes = selected_pattern.get('involved_nodes', [])

            st.markdown(f"#### 📖 Penjelasan AI: *{selected_pattern.get('pattern_title', '')}*")
            st.info(f"**Analisis:** {selected_pattern.get('explanation', 'Tidak ada penjelasan.')}")

            if not involved_nodes:
                st.warning("Visualisasi tidak dapat dibuat karena AI tidak menyertakan daftar node yang terlibat.")
            else:
                context_df = filtered_network_data[
                    (filtered_network_data[src_col_net_global].isin(involved_nodes)) |
                    (filtered_network_data[dst_col_net_global].isin(involved_nodes))
                ]
                if context_df.empty:
                    st.warning("Tidak ditemukan transaksi yang sesuai dengan detail pola dari AI.")
                else:
                    pivot_node = find_most_influential_node(context_df, involved_nodes, src_col_net_global, dst_col_net_global, method=influence_method)
                    
                    st.info(f"Visualisasi berikut difokuskan pada node yang dianggap paling berpengaruh berdasarkan metode **{influence_method.capitalize()}**: **{pivot_node}**")

                    st.markdown("**Network Graph Kontekstual**")
                    net_pattern, _, _ = create_network_visualization(
                        context_df, node_type, src_col_net_global, dst_col_net_global,
                        full_data=data, selected_entity_filter=selected_entity_name,
                        selected_dinas_filter=selected_dinas_desc, selected_sub_dinas_filter=selected_sub_dinas_desc
                    )
                    
                    try:
                        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding='utf-8') as tmpfile:
                            filepath = tmpfile.name
                            net_pattern.save_graph(filepath)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        os.remove(filepath)
                        st.components.v1.html(html_content, height=650, scrolling=True)
                    except Exception as e:
                        st.error(f"Gagal membuat network graph: {e}")
                        
                    if not pivot_node:
                        st.warning("Tidak dapat menentukan node pusat untuk membuat Sankey Diagram.")
                    else:
                        st.markdown(f"**Aliran Dana MASUK ke `{pivot_node}`**")
                        input_df = context_df[context_df[dst_col_net_global] == pivot_node]
                        if not input_df.empty:
                            fig_sankey_input = create_sankey_visualization(input_df, src_col_net_global, dst_col_net_global)
                            st.plotly_chart(fig_sankey_input, use_container_width=True)
                        else:
                            st.info(f"Tidak ada aliran dana masuk yang signifikan ke `{pivot_node}` dalam konteks ini.")
                    
                        st.markdown(f"**Aliran Dana KELUAR dari `{pivot_node}`**")
                        output_df = context_df[context_df[src_col_net_global] == pivot_node]
                        if not output_df.empty:
                            fig_sankey_output = create_sankey_visualization(output_df, src_col_net_global, dst_col_net_global)
                            st.plotly_chart(fig_sankey_output, use_container_width=True)
                        else:
                            st.info(f"Tidak ada aliran dana keluar yang signifikan dari `{pivot_node}` dalam konteks ini.")