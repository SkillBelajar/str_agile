import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="Memory AI Pro - Ultimate Edition",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Timezone WIB ---
def now_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta"))

# --- Keamanan Password ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# --- Database Management ---
DB_PATH = "memory_ai_v5.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS visions (
        vision_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vision_name TEXT NOT NULL,
        description TEXT,
        user_id INTEGER,
        created_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sprints (
        sprint_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sprint_name TEXT NOT NULL,
        start_date DATE,
        end_date DATE,
        goal TEXT,
        status TEXT DEFAULT 'Planned',
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT NOT NULL,
        category TEXT,
        priority INTEGER DEFAULT 3,
        impact INTEGER DEFAULT 5,
        status TEXT DEFAULT 'Backlog',
        vision_id INTEGER,
        sprint_id INTEGER,
        user_id INTEGER,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY (vision_id) REFERENCES visions (vision_id) ON DELETE CASCADE,
        FOREIGN KEY (sprint_id) REFERENCES sprints (sprint_id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Session State ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- UI Otentikasi ---
def login_ui():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Akses Memory AI")
        choice = st.segmented_control("Opsi Akses", ["Login", "Daftar"], default="Login")
        
        with st.form("auth_form", clear_on_submit=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk Sekarang" if choice == "Login" else "Buat Akun")
            
            if submit:
                if not username or not password:
                    st.error("Isi semua kolom!")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    if choice == "Daftar":
                        try:
                            cursor.execute("INSERT INTO users (username, password) VALUES (?,?)", 
                                         (username, make_hashes(password)))
                            conn.commit()
                            st.success("Akun berhasil dibuat! Silakan pilih Login.")
                        except sqlite3.IntegrityError:
                            st.error("Username sudah digunakan.")
                    else:
                        cursor.execute("SELECT user_id, password FROM users WHERE username=?", (username,))
                        result = cursor.fetchone()
                        if result and check_hashes(password, result[1]):
                            st.session_state['logged_in'] = True
                            st.session_state['user_id'] = result[0]
                            st.session_state['username'] = username
                            st.rerun()
                        else:
                            st.error("Username atau password salah.")
                    conn.close()

# --- Logout ---
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- Main App ---
if not st.session_state['logged_in']:
    login_ui()
else:
    st.markdown("""
        <style>
        .stButton button { width: 100%; border-radius: 5px; }
        .stMetric { border: 1px solid #ddd; padding: 10px; border-radius: 8px; }
        .card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title("🧠 Memory AI")
        st.markdown(f"Halo, **{st.session_state['username']}**")
        menu = st.radio("Navigasi", ["🎯 Master Vision", "📋 Backlog", "🚀 Sprints", "⚙️ Execution", "📈 Analytics"])
        st.markdown("---")
        if st.button("🚪 Keluar"):
            logout()

    u_id = st.session_state['user_id']

    # ==============================
    # 🎯 MASTER VISION
    # ==============================
    if menu == "🎯 Master Vision":
        st.subheader("Visi & Tujuan Besar")
        tab1, tab2 = st.tabs(["Daftar Visi", "➕ Tambah Visi"])
        
        with tab2:
            with st.form("v_form", clear_on_submit=True):
                v_name = st.text_input("Nama Visi (Target Utama)")
                v_desc = st.text_area("Deskripsi Strategis")
                if st.form_submit_button("Simpan Visi"):
                    if v_name:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO visions (vision_name, description, user_id, created_at) VALUES (?,?,?,?)",
                                     (v_name, v_desc, u_id, now_wib()))
                        conn.commit()
                        conn.close()
                        st.toast("Visi berhasil disimpan!")
                        st.rerun()

        with tab1:
            conn = get_connection()
            df_v = pd.read_sql_query(f"SELECT * FROM visions WHERE user_id={u_id}", conn)
            conn.close()
            if df_v.empty: st.info("Belum ada visi.")
            for _, v in df_v.iterrows():
                with st.expander(f"🎯 {v['vision_name']}"):
                    with st.form(f"edit_v_{v['vision_id']}"):
                        ev_name = st.text_input("Nama", value=v['vision_name'])
                        ev_desc = st.text_area("Deskripsi", value=v['description'])
                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("Perbarui"):
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE visions SET vision_name=?, description=? WHERE vision_id=?", (ev_name, ev_desc, v['vision_id']))
                            conn.commit(); conn.close(); st.rerun()
                        if c2.form_submit_button("🗑️ Hapus Visi"):
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM visions WHERE vision_id=?", (v['vision_id'],))
                            conn.commit(); conn.close(); st.rerun()

    # ==============================
    # 📋 BACKLOG
    # ==============================
    elif menu == "📋 Backlog":
        conn = get_connection()
        df_v = pd.read_sql_query(f"SELECT * FROM visions WHERE user_id={u_id}", conn)
        conn.close()
        
        if df_v.empty:
            st.warning("Buat Visi terlebih dahulu sebelum menambah tugas.")
        else:
            tab1, tab2 = st.tabs(["List Backlog", "➕ Tambah Tugas"])
            
            with tab2:
                with st.form("t_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    t_name = c1.text_input("Nama Tugas")
                    t_vision = c1.selectbox("Tautkan ke Visi", df_v['vision_name'])
                    t_cat = c2.selectbox("Kategori", ["Career", "Personal", "Learning", "Health", "Finances"])
                    t_prio = c2.select_slider("Prioritas (1-5)", options=[1,2,3,4,5], value=3)
                    t_imp = st.slider("Dampak (1-10)", 1, 10, 5)
                    
                    if st.form_submit_button("Simpan ke Backlog"):
                        vid = df_v[df_v['vision_name'] == t_vision]['vision_id'].values[0]
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO tasks (task_name, category, priority, impact, vision_id, user_id, created_at, updated_at)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (t_name, t_cat, t_prio, t_imp, int(vid), u_id, now_wib(), now_wib()))
                        conn.commit(); conn.close(); st.rerun()

            with tab1:
                conn = get_connection()
                tasks = pd.read_sql_query(f"""
                    SELECT t.*, v.vision_name, (t.priority * t.impact) as score 
                    FROM tasks t JOIN visions v ON t.vision_id = v.vision_id 
                    WHERE t.user_id={u_id} AND t.status='Backlog' 
                    ORDER BY score DESC
                """, conn)
                conn.close()
                
                if tasks.empty: st.info("Backlog kosong.")
                for _, t in tasks.iterrows():
                    with st.expander(f"⭐ {t['score']} | {t['task_name']} ({t['vision_name']})"):
                        with st.form(f"edit_t_{t['task_id']}"):
                            et_name = st.text_input("Nama Tugas", value=t['task_name'])
                            c1, c2 = st.columns(2)
                            et_prio = c1.slider("Prioritas", 1, 5, int(t['priority']))
                            et_imp = c2.slider("Dampak", 1, 10, int(t['impact']))
                            if st.form_submit_button("Update Task"):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute("UPDATE tasks SET task_name=?, priority=?, impact=?, updated_at=? WHERE task_id=?",
                                             (et_name, et_prio, et_imp, now_wib(), t['task_id']))
                                conn.commit(); conn.close(); st.rerun()
                            if st.form_submit_button("🗑️ Hapus Tugas"):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM tasks WHERE task_id=?", (t['task_id'],))
                                conn.commit(); conn.close(); st.rerun()

    # ==============================
    # 🚀 SPRINTS
    # ==============================
    elif menu == "🚀 Sprints":
        st.subheader("Manajemen Waktu (Sprints)")
        tab1, tab2 = st.tabs(["Daftar Sprint", "➕ Create Sprint"])
        
        with tab2:
            with st.form("s_form"):
                s_name = st.text_input("Nama Sprint")
                c1, c2 = st.columns(2)
                s_start = c1.date_input("Tanggal Mulai")
                s_end = c2.date_input("Tanggal Selesai")
                s_goal = st.text_area("Fokus Utama Sprint")
                if st.form_submit_button("Launch!"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO sprints (sprint_name, start_date, end_date, goal, user_id) VALUES (?,?,?,?,?)",
                                 (s_name, s_start, s_end, s_goal, u_id))
                    conn.commit(); conn.close(); st.rerun()

        with tab1:
            conn = get_connection()
            sprints = pd.read_sql_query(f"SELECT * FROM sprints WHERE user_id={u_id} ORDER BY start_date DESC", conn)
            conn.close()
            for _, s in sprints.iterrows():
                with st.expander(f"📅 {s['sprint_name']} ({s['status']})"):
                    st.write(f"**Goal:** {s['goal']}")
                    st.caption(f"Periode: {s['start_date']} s/d {s['end_date']}")
                    c1, c2 = st.columns(2)
                    new_status = c1.selectbox("Ubah Status", ["Planned", "Active", "Completed"], 
                                            index=["Planned", "Active", "Completed"].index(s['status']), key=f"ss_{s['sprint_id']}")
                    if c1.button("Simpan Status", key=f"btn_s_{s['sprint_id']}"):
                        conn = get_connection(); cursor = conn.cursor()
                        cursor.execute("UPDATE sprints SET status=? WHERE sprint_id=?", (new_status, s['sprint_id']))
                        conn.commit(); conn.close(); st.rerun()
                    if c2.button("🗑️ Hapus Sprint", key=f"btn_del_s_{s['sprint_id']}"):
                        conn = get_connection(); cursor = conn.cursor()
                        cursor.execute("DELETE FROM sprints WHERE sprint_id=?", (s['sprint_id'],))
                        cursor.execute("UPDATE tasks SET sprint_id=NULL, status='Backlog' WHERE sprint_id=?", (s['sprint_id'],))
                        conn.commit(); conn.close(); st.rerun()
            
            st.divider()
            st.subheader("📎 Assign Tasks to Sprint")
            conn = get_connection()
            avail_tasks = pd.read_sql_query(f"SELECT * FROM tasks WHERE user_id={u_id} AND sprint_id IS NULL AND status='Backlog'", conn)
            active_sprints = pd.read_sql_query(f"SELECT * FROM sprints WHERE user_id={u_id} AND status != 'Completed'", conn)
            conn.close()
            
            if not avail_tasks.empty and not active_sprints.empty:
                with st.form("assign_form"):
                    target_s = st.selectbox("Pilih Sprint", active_sprints['sprint_name'])
                    selected_t = st.multiselect("Pilih Tugas", avail_tasks['task_name'])
                    if st.form_submit_button("Pindahkan ke Sprint"):
                        sid = active_sprints[active_sprints['sprint_name'] == target_s]['sprint_id'].values[0]
                        conn = get_connection(); cursor = conn.cursor()
                        for tn in selected_t:
                            cursor.execute("UPDATE tasks SET sprint_id=?, status='Todo' WHERE task_name=? AND user_id=?", (int(sid), tn, u_id))
                        conn.commit(); conn.close(); st.rerun()

    # ==============================
    # ⚙️ EXECUTION
    # ==============================
    elif menu == "⚙️ Execution":
        conn = get_connection()
        active_s = pd.read_sql_query(f"SELECT * FROM sprints WHERE user_id={u_id} AND status='Active'", conn)
        
        if active_s.empty:
            st.info("Tidak ada Sprint Aktif. Aktifkan salah satu sprint di menu Sprints.")
        else:
            sel_s = st.selectbox("Pilih Sprint Kerja", active_s['sprint_name'])
            sid = active_s[active_s['sprint_name'] == sel_s]['sprint_id'].values[0]
            st.info(f"🎯 **Goal:** {active_s[active_s['sprint_id'] == sid]['goal'].values[0]}")
            
            tasks = pd.read_sql_query(f"SELECT * FROM tasks WHERE sprint_id={sid}", conn)
            cols = st.columns(3)
            for i, status in enumerate(["Todo", "In Progress", "Done"]):
                with cols[i]:
                    st.markdown(f"### {status}")
                    subset = tasks[tasks['status'] == status]
                    for _, t in subset.iterrows():
                        with st.container(border=True):
                            st.write(f"**{t['task_name']}**")
                            new_s = st.selectbox("Ke:", ["Todo", "In Progress", "Done", "Unassign"], key=f"ex_{t['task_id']}", index=i)
                            if st.button("Update", key=f"up_{t['task_id']}"):
                                cursor = conn.cursor()
                                if new_s == "Unassign":
                                    cursor.execute("UPDATE tasks SET status='Backlog', sprint_id=NULL WHERE task_id=?", (t['task_id'],))
                                else:
                                    cursor.execute("UPDATE tasks SET status=? WHERE task_id=?", (new_s, t['task_id']))
                                conn.commit(); st.rerun()
        conn.close()

    # ==============================
    # 📈 ANALYTICS
    # ==============================
    elif menu == "📈 Analytics":
        conn = get_connection()
        df_all = pd.read_sql_query(f"SELECT t.*, v.vision_name FROM tasks t JOIN visions v ON t.vision_id = v.vision_id WHERE t.user_id={u_id}", conn)
        conn.close()
        
        if df_all.empty:
            st.info("Data belum cukup untuk analisis.")
        else:
            c1, c2, c3 = st.columns(3)
            total = len(df_all)
            done = len(df_all[df_all['status'] == 'Done'])
            c1.metric("Total Tugas", total)
            c2.metric("Selesai", done)
            c3.metric("Penyelesaian", f"{(done/total*100):.1f}%" if total > 0 else "0%")
            
            st.divider()
            st.subheader("Analisis Strategis")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("#### Prioritas vs Dampak")
                st.scatter_chart(df_all, x="priority", y="impact", color="category")
            with col_b:
                st.write("#### Beban per Visi")
                st.bar_chart(df_all['vision_name'].value_counts())

st.divider()
st.caption(f"Memory AI v5.0 | Sistem Siap ✅ | {now_wib().strftime('%d %b %Y %H:%M')}")