import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="Memory AI Pro - Focus Edition",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Global untuk Animasi ---
st.markdown("""
<style>
    /* Animasi masuk (Fade In + Slide Up) */
    @keyframes fadeInSlide {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Menerapkan animasi pada form dan expander */
    div[data-testid="stForm"], div[data-testid="stExpander"] {
        animation: fadeInSlide 0.4s ease-out;
    }
    
    /* Transisi interaktif halus pada tombol */
    .stButton > button {
        transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

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
DB_PATH = "memory_ai_v6.db"

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
        status TEXT DEFAULT 'Active',
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
        vision_id INTEGER,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (vision_id) REFERENCES visions (vision_id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT NOT NULL,
        priority INTEGER DEFAULT 3,
        impact INTEGER DEFAULT 5,
        status TEXT DEFAULT 'Backlog',
        notes TEXT,
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
    
    # Migrasi sederhana jika kolom 'notes' belum ada
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN notes TEXT")
    except:
        pass
        
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
                            st.error("Login gagal. Periksa kembali username/password.")
                    conn.close()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- Main App ---
if not st.session_state['logged_in']:
    login_ui()
else:
    u_id = st.session_state['user_id']
    
    # --- GLOBAL FILTER LOGIC ---
    conn = get_connection()
    df_visions_sidebar = pd.read_sql_query(f"SELECT vision_id, vision_name, status FROM visions WHERE user_id={u_id}", conn)
    conn.close()

    with st.sidebar:
        st.title("🧠 Memory AI")
        st.write(f"User: **{st.session_state['username']}**")
        st.markdown("---")
        
        st.subheader("🎯 Focus Mode")
        active_v_options = df_visions_sidebar[df_visions_sidebar['status'] == 'Active']
        
        focus_option = st.selectbox(
            "Pilih Visi Fokus:",
            ["Semua Visi (Global)"] + active_v_options['vision_name'].tolist()
        )
        
        focus_vid = None
        if focus_option != "Semua Visi (Global)":
            focus_vid = active_v_options[active_v_options['vision_name'] == focus_option]['vision_id'].values[0]
            st.success(f"Fokus: {focus_option}")
        else:
            st.info("Mode Global Aktif")

        st.markdown("---")
        menu = st.radio("Navigasi", ["🎯 Master Vision", "📋 Backlog", "🚀 Sprints", "⚙️ Execution", "📈 Analytics"])
        st.markdown("---")
        if st.button("🚪 Keluar"):
            logout()

    # ==============================
    # 🎯 MASTER VISION
    # ==============================
    if menu == "🎯 Master Vision":
        st.subheader("Manajemen Visi")
        tab1, tab2 = st.tabs(["Daftar Visi", "➕ Tambah Visi"])
        
        with tab2:
            with st.form("v_form", clear_on_submit=True):
                v_name = st.text_input("Nama Visi")
                v_desc = st.text_area("Deskripsi Strategis")
                if st.form_submit_button("Simpan Visi"):
                    if v_name:
                        conn = get_connection(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO visions (vision_name, description, user_id, created_at) VALUES (?,?,?,?)",
                                     (v_name, v_desc, u_id, now_wib()))
                        conn.commit(); conn.close(); st.rerun()

        with tab1:
            conn = get_connection()
            df_v_display = pd.read_sql_query(f"SELECT * FROM visions WHERE user_id={u_id}", conn)
            conn.close()
            
            if df_v_display.empty: st.info("Belum ada visi.")
            for _, v in df_v_display.iterrows():
                status_icon = "🟢" if v['status'] == 'Active' else "⚪"
                with st.expander(f"{status_icon} {v['vision_name']}"):
                    with st.form(f"edit_v_{v['vision_id']}"):
                        ev_name = st.text_input("Nama", value=v['vision_name'])
                        ev_status = st.selectbox("Status", ["Active", "Archived"], 
                                               index=["Active", "Archived"].index(v['status']))
                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("Perbarui"):
                            conn = get_connection(); cursor = conn.cursor()
                            cursor.execute("UPDATE visions SET vision_name=?, status=? WHERE vision_id=?", 
                                         (ev_name, ev_status, v['vision_id']))
                            conn.commit(); conn.close(); st.rerun()
                        if c2.form_submit_button("🗑️ Hapus"):
                            conn = get_connection(); cursor = conn.cursor()
                            cursor.execute("DELETE FROM visions WHERE vision_id=?", (v['vision_id'],))
                            conn.commit(); conn.close(); st.rerun()

    # ==============================
    # 📋 BACKLOG
    # ==============================
    elif menu == "📋 Backlog":
        if df_visions_sidebar.empty:
            st.warning("Buat Visi terlebih dahulu.")
        else:
            tab1, tab2 = st.tabs(["List Backlog", "➕ Tambah Tugas"])
            
            with tab2:
                with st.form("t_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    t_name = c1.text_input("Nama Tugas")
                    t_vision_list = [focus_option] if focus_vid else df_visions_sidebar[df_visions_sidebar['status']=='Active']['vision_name'].tolist()
                    t_vision = c1.selectbox("Tautkan ke Visi", t_vision_list)
                    t_prio = c2.slider("Prioritas (1-5)", 1, 5, 3)
                    t_imp = c2.slider("Dampak (1-10)", 1, 10, 5)
                    t_notes = st.text_area("Catatan Awal (Opsional)")
                    if st.form_submit_button("Simpan ke Backlog"):
                        vid = df_visions_sidebar[df_visions_sidebar['vision_name'] == t_vision]['vision_id'].values[0]
                        conn = get_connection(); cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO tasks (task_name, priority, impact, notes, vision_id, user_id, created_at, updated_at)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (t_name, t_prio, t_imp, t_notes, int(vid), u_id, now_wib(), now_wib()))
                        conn.commit(); conn.close(); st.rerun()

            with tab1:
                query = f"SELECT t.*, v.vision_name FROM tasks t JOIN visions v ON t.vision_id = v.vision_id WHERE t.user_id={u_id} AND t.status='Backlog'"
                if focus_vid: query += f" AND t.vision_id = {focus_vid}"
                
                conn = get_connection()
                tasks = pd.read_sql_query(query, conn)
                conn.close()
                
                if tasks.empty: st.info("Tidak ada backlog.")
                for _, t in tasks.iterrows():
                    with st.expander(f"⭐ {t['priority']*t['impact']} | {t['task_name']} ({t['vision_name']})"):
                        with st.form(f"edit_t_{t['task_id']}"):
                            et_name = st.text_input("Nama", value=t['task_name'])
                            c1, c2 = st.columns(2)
                            et_prio = c1.slider("Prio", 1, 5, int(t['priority']))
                            et_imp = c2.slider("Imp", 1, 10, int(t['impact']))
                            et_notes = st.text_area("Catatan", value=t['notes'] if t['notes'] else "")
                            if st.form_submit_button("Simpan Perubahan"):
                                conn = get_connection(); cursor = conn.cursor()
                                cursor.execute("UPDATE tasks SET task_name=?, priority=?, impact=?, notes=?, updated_at=? WHERE task_id=?",
                                             (et_name, et_prio, et_imp, et_notes, now_wib(), t['task_id']))
                                conn.commit(); conn.close(); st.rerun()
                            if st.form_submit_button("🗑️ Hapus Tugas"):
                                conn = get_connection(); cursor = conn.cursor()
                                cursor.execute("DELETE FROM tasks WHERE task_id=?", (t['task_id'],))
                                conn.commit(); conn.close(); st.rerun()

    # ==============================
    # 🚀 SPRINTS
    # ==============================
    elif menu == "🚀 Sprints":
        if not focus_vid:
            st.warning("⚠️ Pilih **Visi Fokus** di sidebar untuk mengelola Sprint visi tersebut.")
        else:
            st.subheader(f"Manajemen Sprint: {focus_option}")
            tab_list, tab_create, tab_assign = st.tabs(["Daftar Sprint", "➕ Buat Sprint Baru", "📎 Penugasan Backlog"])
            
            with tab_create:
                with st.form("s_form", clear_on_submit=True):
                    s_name = st.text_input("Nama Sprint", placeholder="Contoh: Sprint 1 - Core Features")
                    c1, c2 = st.columns(2)
                    s_start = c1.date_input("Mulai", value=datetime.now())
                    s_end = c2.date_input("Selesai", value=datetime.now())
                    s_goal = st.text_area("Tujuan Utama Sprint")
                    if st.form_submit_button("Luncurkan Sprint 🚀"):
                        if s_name:
                            conn = get_connection(); cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO sprints (sprint_name, start_date, end_date, goal, status, vision_id, user_id) 
                                VALUES (?,?,?,?,'Planned',?,?)
                            """, (s_name, s_start, s_end, s_goal, int(focus_vid), u_id))
                            conn.commit(); conn.close(); st.rerun()

            with tab_list:
                conn = get_connection()
                sprints = pd.read_sql_query(f"SELECT * FROM sprints WHERE user_id={u_id} AND vision_id={focus_vid} ORDER BY start_date DESC", conn)
                conn.close()
                
                if sprints.empty: st.info("Belum ada sprint untuk visi ini.")
                for _, s in sprints.iterrows():
                    with st.expander(f"📅 {s['sprint_name']} ({s['status']})"):
                        with st.form(f"edit_s_{s['sprint_id']}"):
                            es_name = st.text_input("Nama", value=s['sprint_name'])
                            c1, c2 = st.columns(2)
                            es_start = c1.date_input("Mulai", value=datetime.strptime(s['start_date'], '%Y-%m-%d'))
                            es_end = c2.date_input("Selesai", value=datetime.strptime(s['end_date'], '%Y-%m-%d'))
                            es_goal = st.text_area("Goal", value=s['goal'])
                            es_status = st.selectbox("Status", ["Planned", "Active", "Completed"], 
                                                   index=["Planned", "Active", "Completed"].index(s['status']))
                            
                            b1, b2 = st.columns(2)
                            if b1.form_submit_button("Simpan Perubahan"):
                                conn = get_connection(); cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE sprints SET sprint_name=?, start_date=?, end_date=?, goal=?, status=? 
                                    WHERE sprint_id=?
                                """, (es_name, es_start, es_end, es_goal, es_status, s['sprint_id']))
                                conn.commit(); conn.close(); st.rerun()
                            if b2.form_submit_button("🗑️ Hapus Sprint"):
                                conn = get_connection(); cursor = conn.cursor()
                                cursor.execute("DELETE FROM sprints WHERE sprint_id=?", (s['sprint_id'],))
                                cursor.execute("UPDATE tasks SET sprint_id=NULL, status='Backlog' WHERE sprint_id=?", (s['sprint_id'],))
                                conn.commit(); conn.close(); st.rerun()

            with tab_assign:
                st.write("### Masukkan Tugas ke Sprint Aktif/Terencana")
                conn = get_connection()
                avail_tasks = pd.read_sql_query(f"""
                    SELECT task_id, task_name, (priority * impact) as score 
                    FROM tasks WHERE vision_id={focus_vid} AND sprint_id IS NULL AND status='Backlog'
                    ORDER BY score DESC
                """, conn)
                active_sprints = pd.read_sql_query(f"SELECT sprint_id, sprint_name FROM sprints WHERE vision_id={focus_vid} AND status != 'Completed'", conn)
                conn.close()
                
                if not avail_tasks.empty and not active_sprints.empty:
                    with st.form("assign_form"):
                        target_s = st.selectbox("Pilih Target Sprint", active_sprints['sprint_name'])
                        task_options = {f"⭐ {row['score']} | {row['task_name']}": row['task_id'] for _, row in avail_tasks.iterrows()}
                        selected_labels = st.multiselect("Pilih Tugas dari Backlog", list(task_options.keys()))
                        
                        if st.form_submit_button("Assign ke Sprint"):
                            sid = active_sprints[active_sprints['sprint_name'] == target_s]['sprint_id'].values[0]
                            conn = get_connection(); cursor = conn.cursor()
                            for label in selected_labels:
                                tid = task_options[label]
                                cursor.execute("UPDATE tasks SET sprint_id=?, status='Todo' WHERE task_id=?", (int(sid), int(tid)))
                            conn.commit(); conn.close(); st.rerun()
                else:
                    st.info("Pastikan ada tugas di Backlog dan Sprint yang belum selesai.")

    # ==============================
    # ⚙️ EXECUTION (UPDATED WITH NOTES & COLORS)
    # ==============================
    elif menu == "⚙️ Execution":
        if not focus_vid:
            st.warning("⚠️ Pilih **Visi Fokus** di sidebar.")
        else:
            conn = get_connection()
            active_s = pd.read_sql_query(f"SELECT * FROM sprints WHERE vision_id={focus_vid} AND status='Active'", conn)
            if active_s.empty:
                st.info(f"Tidak ada Sprint Aktif untuk '{focus_option}'. Silakan aktifkan sprint di menu Sprints.")
            else:
                sel_s = st.selectbox("Pilih Sprint Kerja", active_s['sprint_name'])
                
                # Ambil data detail untuk sprint yang dipilih
                selected_sprint = active_s[active_s['sprint_name'] == sel_s].iloc[0]
                sid = selected_sprint['sprint_id']
                
                # --- Kalkulasi Sisa Hari ---
                end_date_str = selected_sprint['end_date']
                try:
                    # Parse string tanggal menjadi objek date, lalu hitung selisih dengan hari ini
                    end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    today = now_wib().date()
                    sisa_hari = (end_date_obj - today).days
                    
                    if sisa_hari > 0:
                        sisa_text = f"⏳ **Sisa waktu:** {sisa_hari} hari"
                    elif sisa_hari == 0:
                        sisa_text = "⏳ **Sisa waktu:** Hari terakhir sprint!"
                    else:
                        sisa_text = f"⚠️ **Sisa waktu:** Terlambat {abs(sisa_hari)} hari"
                except Exception:
                    sisa_text = "⏳ **Sisa waktu:** Format tanggal tidak valid"

                # Menampilkan Tanggal Mulai & Akhir bersebelahan dengan Sisa Hari
                c_info1, c_info2 = st.columns([2, 1])
                c_info1.info(f"🗓️ **Periode Sprint:** {selected_sprint['start_date']} s/d {selected_sprint['end_date']}")
                if "Terlambat" in sisa_text:
                    c_info2.error(sisa_text)  # Gunakan warna merah (error) jika terlambat
                else:
                    c_info2.info(sisa_text)   # Gunakan warna biru (info) jika masih ada waktu
                
                tasks = pd.read_sql_query(f"SELECT * FROM tasks WHERE sprint_id={sid}", conn)
                
                cols = st.columns(3)
                status_list = ["Todo", "In Progress", "Done"]
                
                # Pemetaan Warna: Kuning, Biru, Hijau (Tone Adjusted untuk Kontras Tinggi)
                color_config = {
                    "Todo": {"bg": "#FFF4CC", "text": "#4D3800", "icon": "🟡"},       # Kuning (Soft bg, text cokelat gelap)
                    "In Progress": {"bg": "#D6E8FF", "text": "#002759", "icon": "🔵"}, # Biru (Soft bg, text navy gelap)
                    "Done": {"bg": "#D1F2D9", "text": "#0B421A", "icon": "🟢"}         # Hijau (Soft bg, text hijau tua gelap)
                }

                for i, status in enumerate(status_list):
                    with cols[i]:
                        st.markdown(f"### {color_config[status]['icon']} {status}")
                        subset = tasks[tasks['status'] == status]
                        for _, t in subset.iterrows():
                            with st.container(border=True):
                                # Header Kartu Tugas dengan Latar Warna
                                st.markdown(f"""
                                <div style="background-color: {color_config[status]['bg']}; 
                                            color: {color_config[status]['text']}; 
                                            padding: 8px 12px; 
                                            border-radius: 6px; 
                                            margin-bottom: 12px;
                                            font-weight: 600;
                                            border: 1px solid {color_config[status]['text']}60;
                                            transition: background-color 0.5s ease, color 0.5s ease;
                                            animation: fadeInSlide 0.5s ease-out;">
                                    {t['task_name']}
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Form Mini untuk setiap task agar notes bisa di-update
                                with st.form(key=f"exec_form_{t['task_id']}"):
                                    new_s = st.selectbox("Update Progres:", ["Todo", "In Progress", "Done", "Unassign"], 
                                                         index=status_list.index(status) if status in status_list else 0)
                                    
                                    # Catatan Progres
                                    new_notes = st.text_area("Catatan Progres:", 
                                                           value=t['notes'] if t['notes'] else "", 
                                                           placeholder="Tulis kendala atau update di sini...",
                                                           key=f"note_{t['task_id']}")
                                    
                                    if st.form_submit_button("Simpan Update"):
                                        cursor = conn.cursor()
                                        if new_s == "Unassign":
                                            cursor.execute("UPDATE tasks SET status='Backlog', notes=?, sprint_id=NULL, updated_at=? WHERE task_id=?", 
                                                         (new_notes, now_wib(), t['task_id']))
                                        else:
                                            cursor.execute("UPDATE tasks SET status=?, notes=?, updated_at=? WHERE task_id=?", 
                                                         (new_s, new_notes, now_wib(), t['task_id']))
                                        conn.commit(); st.rerun()
            conn.close()

    # ==============================
    # 📈 ANALYTICS
    # ==============================
    elif menu == "📈 Analytics":
        query = f"SELECT t.*, v.vision_name FROM tasks t JOIN visions v ON t.vision_id = v.vision_id WHERE t.user_id={u_id}"
        if focus_vid: query += f" AND t.vision_id = {focus_vid}"
        
        conn = get_connection()
        df_all = pd.read_sql_query(query, conn)
        conn.close()
        
        if df_all.empty:
            st.info("Belum ada data untuk dianalisis. Mulailah dengan membuat Visi dan Tugas!")
        else:
            st.subheader(f"📊 Dashboard Statistik: {focus_option}")
            st.markdown("---")
            
            # Kalkulasi Data
            total = len(df_all)
            done = len(df_all[df_all['status'] == 'Done'])
            in_progress = len(df_all[df_all['status'] == 'In Progress'])
            todo = len(df_all[df_all['status'].isin(['Todo', 'Backlog'])])
            
            # --- Baris Metrik Utama ---
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🎯 Penyelesaian", f"{(done/total*100):.1f}%" if total > 0 else "0%")
            with col2:
                st.metric("📦 Total Tugas", total)
            with col3:
                st.metric("🔥 In Progress", in_progress)
            with col4:
                st.metric("📌 Belum Selesai", todo)
            
            # --- Progress Bar ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 🚀 Progres Keseluruhan")
            st.progress(done/total if total > 0 else 0)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- Visualisasi & Insight ---
            c_chart, c_insight = st.columns([2, 1])
            
            with c_chart:
                with st.container(border=True):
                    st.write("#### 📊 Distribusi Status Tugas")
                    st.bar_chart(df_all['status'].value_counts())
                    
            with c_insight:
                with st.container(border=True):
                    st.write("#### 💡 Ringkasan Fokus")
                    if total > 0:
                        # Pesan Dinamis
                        if done == total:
                            st.success("🎉 Luar biasa! Semua tugas telah selesai.")
                        elif (done/total) > 0.5:
                            st.info("🔥 Lebih dari setengah jalan menuju garis akhir. Teruskan!")
                        elif in_progress > 0:
                            st.warning("⚡ Terus kerjakan tugas yang sedang berjalan!")
                        else:
                            st.error("⏳ Mari mulai ambil tugas dari backlog Anda.")
                        
                        st.markdown("---")
                        st.write("**Top Tugas Mendesak (Belum Selesai):**")
                        # Mengambil 3 tugas dengan prioritas & dampak tertinggi yang belum selesai
                        top_tasks = df_all[df_all['status'] != 'Done'].sort_values(by=['priority', 'impact'], ascending=[False, False]).head(3)
                        
                        if not top_tasks.empty:
                            for _, t in top_tasks.iterrows():
                                st.write(f"🔸 **{t['task_name']}** (Prio: {t['priority']})")
                        else:
                            st.write("✅ Tidak ada tugas mendesak.")

st.divider()
st.caption(f"Memory AI Focus v6.2 | Catatan Aktif ✅ | User: {st.session_state.get('username')} | {now_wib().strftime('%H:%M')}")