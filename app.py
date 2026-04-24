import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="Memory AI Pro - Vision Driven",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Timezone WIB ---
def now_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta"))

# --- Database Management ---
DB_PATH = "memory_ai_v3.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table Visions (LAPISAN BARU)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS visions (
        vision_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vision_name TEXT NOT NULL,
        description TEXT,
        created_at DATETIME
    )
    """)
    
    # Table Sprints
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sprints (
        sprint_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sprint_name TEXT NOT NULL,
        start_date DATE,
        end_date DATE,
        goal TEXT,
        status TEXT DEFAULT 'Planned'
    )
    """)
    
    # Table Tasks (DENGAN VISION_ID)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT NOT NULL,
        category TEXT,
        priority INTEGER,
        impact INTEGER,
        status TEXT DEFAULT 'Backlog',
        vision_id INTEGER,
        sprint_id INTEGER,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY (vision_id) REFERENCES visions (vision_id) ON DELETE CASCADE,
        FOREIGN KEY (sprint_id) REFERENCES sprints (sprint_id) ON DELETE SET NULL
    )
    """)
    conn.commit()
    conn.close()

init_db()

# --- CSS Custom ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.title("🧠 Memory AI")
    st.markdown("---")
    menu = st.radio(
        "Navigasi Utama",
        ["🎯 Master Vision", "📋 Backlog", "🚀 Sprint Management", "⚙️ Execution", "📈 Analytics"],
        index=0
    )
    st.markdown("---")
    st.info(f"🕒 WIB: {now_wib().strftime('%H:%M:%S')}")

# --- Header ---
st.title(f"{menu}")

# ==============================
# 🎯 MASTER VISION (MENU BARU)
# ==============================
if "Vision" in menu:
    tab_v_list, tab_v_add = st.tabs(["Daftar Visi Utama", "➕ Tambah Visi Baru"])
    
    with tab_v_add:
        with st.form("add_vision_form", clear_on_submit=True):
            v_name = st.text_input("Nama Visi / Proyek Besar", placeholder="Contoh: Menjadi Data Scientist 2024")
            v_desc = st.text_area("Deskripsi / Harapan")
            if st.form_submit_button("Simpan Visi"):
                if v_name:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO visions (vision_name, description, created_at) VALUES (?, ?, ?)",
                                 (v_name, v_desc, now_wib()))
                    conn.commit()
                    conn.close()
                    st.success("Visi baru berhasil disimpan!")
                    st.rerun()
    
    with tab_v_list:
        conn = get_connection()
        df_visions = pd.read_sql_query("SELECT * FROM visions ORDER BY created_at DESC", conn)
        conn.close()
        
        if df_visions.empty:
            st.info("Belum ada visi. Mulailah dengan menentukan tujuan besar Anda.")
        else:
            for _, v in df_visions.iterrows():
                with st.expander(f"🎯 {v['vision_name']}"):
                    with st.form(f"edit_v_{v['vision_id']}"):
                        ev_name = st.text_input("Nama Visi", value=v['vision_name'])
                        ev_desc = st.text_area("Deskripsi", value=v['description'])
                        b1, b2 = st.columns([1, 4])
                        if b1.form_submit_button("Update"):
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE visions SET vision_name=?, description=? WHERE vision_id=?",
                                        (ev_name, ev_desc, v['vision_id']))
                            conn.commit()
                            conn.close()
                            st.rerun()
                        if b2.form_submit_button("🗑️ Hapus Visi & Backlog Terkait"):
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM visions WHERE vision_id=?", (v['vision_id'],))
                            # Backlog otomatis terhapus karena ON DELETE CASCADE (jika didukung) atau manual:
                            cursor.execute("DELETE FROM tasks WHERE vision_id=?", (v['vision_id'],))
                            conn.commit()
                            conn.close()
                            st.rerun()

# ==============================
# 📋 BACKLOG (GRUP BERDASARKAN VISI)
# ==============================
elif "Backlog" in menu:
    conn = get_connection()
    df_v = pd.read_sql_query("SELECT * FROM visions", conn)
    conn.close()

    if df_v.empty:
        st.warning("Silakan buat setidaknya satu **Visi** terlebih dahulu di menu 'Master Vision'.")
    else:
        tab_list, tab_add = st.tabs(["Daftar Backlog", "➕ Tambah Tugas"])

        with tab_add:
            with st.form("add_task_v_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    t_vision = st.selectbox("Pilih Visi Utama", df_v['vision_name'])
                    t_name = st.text_input("Nama Tugas")
                    t_cat = st.selectbox("Kategori", ["Personal", "Career", "Health", "Learning", "Project"])
                with col2:
                    t_prio = st.select_slider("Prioritas", options=[1,2,3,4,5], value=3)
                    t_imp = st.slider("Dampak", 1, 10, 5)
                
                if st.form_submit_button("Tambahkan ke Backlog"):
                    v_id = df_v[df_v['vision_name'] == t_vision]['vision_id'].values[0]
                    if t_name:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO tasks (task_name, category, priority, impact, vision_id, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (t_name, t_cat, t_prio, t_imp, int(v_id), now_wib(), now_wib()))
                        conn.commit()
                        conn.close()
                        st.success("Tugas berhasil ditambahkan!")
                        st.rerun()

        with tab_list:
            filter_v = st.selectbox("Filter berdasarkan Visi:", ["Semua Visi"] + df_v['vision_name'].tolist())
            
            conn = get_connection()
            query = """
                SELECT t.*, v.vision_name 
                FROM tasks t 
                LEFT JOIN visions v ON t.vision_id = v.vision_id 
                WHERE t.status = 'Backlog'
            """
            if filter_v != "Semua Visi":
                query += f" AND v.vision_name = '{filter_v}'"
            
            df_tasks = pd.read_sql_query(query, conn)
            conn.close()

            if df_tasks.empty:
                st.info("Tidak ada tugas di backlog untuk filter ini.")
            else:
                for _, row in df_tasks.iterrows():
                    with st.expander(f"[{row['vision_name']}] {row['task_name']}"):
                        # CRUD Task mirip sebelumnya namun dengan tambahan vision_id edit
                        with st.form(f"edit_task_{row['task_id']}"):
                            c1, c2 = st.columns(2)
                            new_name = c1.text_input("Nama Tugas", value=row['task_name'])
                            new_v = c2.selectbox("Ganti Visi", df_v['vision_name'], 
                                               index=df_v['vision_name'].tolist().index(row['vision_name']))
                            
                            if st.form_submit_button("Update"):
                                new_vid = df_v[df_v['vision_name'] == new_v]['vision_id'].values[0]
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute("UPDATE tasks SET task_name=?, vision_id=?, updated_at=? WHERE task_id=?",
                                            (new_name, int(new_vid), now_wib(), row['task_id']))
                                conn.commit()
                                conn.close()
                                st.rerun()

# ==============================
# 🚀 SPRINT MANAGEMENT
# ==============================
elif "Sprint" in menu:
    tab_manage, tab_assign = st.tabs(["Manajemen Sprint", "📎 Penugasan Sprint"])
    # (Logika Sprint tetap sama namun filter tugas saat assign bisa lebih spesifik)
    with tab_manage:
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            st.subheader("Buat Sprint")
            with st.form("sprint_create", clear_on_submit=True):
                s_name = st.text_input("Nama Sprint")
                s_start = st.date_input("Mulai")
                s_end = st.date_input("Selesai")
                s_goal = st.text_area("Tujuan Sprint")
                if st.form_submit_button("🚀 Launch Sprint"):
                    if s_name:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO sprints (sprint_name, start_date, end_date, goal) VALUES (?,?,?,?)",
                                    (s_name, s_start, s_end, s_goal))
                        conn.commit()
                        conn.close()
                        st.success("Sprint diluncurkan!")
                        st.rerun()
        with col_s2:
            st.subheader("Daftar Sprint")
            conn = get_connection()
            sprints = pd.read_sql_query("SELECT * FROM sprints ORDER BY start_date DESC", conn)
            conn.close()
            for _, s in sprints.iterrows():
                with st.expander(f"📅 {s['sprint_name']} ({s['status']})"):
                    with st.form(f"edit_sprint_{s['sprint_id']}"):
                        es_name = st.text_input("Nama", value=s['sprint_name'])
                        es_status = st.selectbox("Status", ["Planned", "Active", "Completed"], 
                                               index=["Planned", "Active", "Completed"].index(s['status']))
                        if st.form_submit_button("Simpan"):
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE sprints SET sprint_name=?, status=? WHERE sprint_id=?", (es_name, es_status, s['sprint_id']))
                            conn.commit()
                            conn.close()
                            st.rerun()

    with tab_assign:
        conn = get_connection()
        # Join dengan Vision agar user tahu tugas ini milik visi mana
        available_tasks = pd.read_sql_query("""
            SELECT t.task_id, t.task_name, v.vision_name 
            FROM tasks t 
            JOIN visions v ON t.vision_id = v.vision_id 
            WHERE t.sprint_id IS NULL AND t.status='Backlog'
        """, conn)
        active_sprints = pd.read_sql_query("SELECT sprint_id, sprint_name FROM sprints WHERE status != 'Completed'", conn)
        conn.close()

        if not active_sprints.empty and not available_tasks.empty:
            with st.form("assign_form"):
                target_sprint = st.selectbox("Pilih Sprint", active_sprints['sprint_name'])
                # Tampilkan format: [Nama Visi] Nama Tugas
                task_display = [f"[{t['vision_name']}] {t['task_name']}" for _, t in available_tasks.iterrows()]
                selected_display = st.multiselect("Pilih Tugas", task_display)
                
                if st.form_submit_button("Assign Sekarang"):
                    s_id = active_sprints[active_sprints['sprint_name'] == target_sprint]['sprint_id'].values[0]
                    # Ekstrak task_id asli
                    t_ids = []
                    for disp in selected_display:
                        t_name_part = disp.split("] ")[1]
                        v_name_part = disp.split("] ")[0][1:]
                        matched = available_tasks[(available_tasks['task_name'] == t_name_part) & (available_tasks['vision_name'] == v_name_part)]
                        if not matched.empty:
                            t_ids.append(matched['task_id'].values[0])
                    
                    conn = get_connection()
                    cursor = conn.cursor()
                    for tid in t_ids:
                        cursor.execute("UPDATE tasks SET sprint_id=?, status='Todo' WHERE task_id=?", (int(s_id), int(tid)))
                    conn.commit()
                    conn.close()
                    st.rerun()

# ==============================
# ⚙️ EXECUTION & ANALYTICS (Disesuaikan)
# ==============================
elif "Execution" in menu:
    conn = get_connection()
    sprints = pd.read_sql_query("SELECT sprint_id, sprint_name FROM sprints WHERE status='Active'", conn)
    if sprints.empty:
        st.info("Aktifkan sprint terlebih dahulu.")
    else:
        selected_sprint = st.selectbox("Pilih Sprint Aktif", sprints['sprint_name'])
        sid = sprints[sprints['sprint_name'] == selected_sprint]['sprint_id'].values[0]
        tasks = pd.read_sql_query(f"SELECT t.*, v.vision_name FROM tasks t JOIN visions v ON t.vision_id = v.vision_id WHERE t.sprint_id={sid}", conn)
        
        cols = st.columns(3)
        for i, status in enumerate(["Todo", "In Progress", "Done"]):
            with cols[i]:
                st.subheader(status)
                subset = tasks[tasks['status'] == status]
                for _, t in subset.iterrows():
                    with st.container(border=True):
                        st.caption(t['vision_name'])
                        st.write(f"**{t['task_name']}**")
                        new_s = st.selectbox("Pindah ke:", ["Todo", "In Progress", "Done", "Unassign"], key=f"ex_{t['task_id']}", index=i)
                        if st.button("Update", key=f"btn_{t['task_id']}"):
                            cursor = conn.cursor()
                            if new_s == "Unassign":
                                cursor.execute("UPDATE tasks SET status='Backlog', sprint_id=NULL WHERE task_id=?", (t['task_id'],))
                            else:
                                cursor.execute("UPDATE tasks SET status=? WHERE task_id=?", (new_s, t['task_id']))
                            conn.commit()
                            st.rerun()
    conn.close()

elif "Analytics" in menu:
    conn = get_connection()
    df_all = pd.read_sql_query("""
        SELECT t.*, v.vision_name 
        FROM tasks t 
        JOIN visions v ON t.vision_id = v.vision_id
    """, conn)
    conn.close()

    if not df_all.empty:
        st.write("#### Kemajuan Per Visi")
        for v_name in df_all['vision_name'].unique():
            v_tasks = df_all[df_all['vision_name'] == v_name]
            v_done = len(v_tasks[v_tasks['status'] == 'Done'])
            v_total = len(v_tasks)
            st.write(f"**{v_name}** ({v_done}/{v_total})")
            st.progress(v_done/v_total)
        
        st.divider()
        st.write("#### Distribusi Tugas Per Visi")
        st.bar_chart(df_all['vision_name'].value_counts())

st.divider()
st.caption("Memory AI - Vision Driven Framework")