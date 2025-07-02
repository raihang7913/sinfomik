import streamlit as st
from db import get_connection
import time
import sqlite3

def authenticate(username, password):
    conn = sqlite3.connect('sinfomik.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, role 
        FROM user 
        WHERE username = ? AND password = ?
    """, (username, password))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "username": user[1],
            "role": user[2]
        }
    return None

def show_login():
    # Inisialisasi session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "role" not in st.session_state:
        st.session_state.role = ""
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "guru_data" not in st.session_state:
        st.session_state.guru_data = {}

    # Jika sudah login, tampilkan info
    if st.session_state.logged_in:
        role_display = "Admin" if st.session_state.role == "admin" else "Guru"
        st.info(f"Anda sudah login sebagai {role_display} {st.session_state.username}.")
        return

    # Form login
    st.subheader("Silakan Login untuk Melanjutkan")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            if username and password:
                try:
                    with get_connection() as conn:
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        
                        # Query login
                        cursor.execute(
                            """SELECT id, username, role 
                               FROM user 
                               WHERE username = ? AND password = ?""",
                            (username, password)
                        )
                        user = cursor.fetchone()
                        
                        if user:
                            # Set session state
                            st.session_state.logged_in = True
                            st.session_state.user_id = user['id']
                            st.session_state.username = user['username']
                            st.session_state.role = user['role']
                            
                            # Jika guru, ambil data mengajar
                            if user['role'] == 'guru':
                                cursor.execute(
                                    """SELECT mp.nama_mapel, k.nama_kelas 
                                       FROM guru_mapel_kelas gmk
                                       JOIN mata_pelajaran mp ON gmk.mapel_id = mp.id
                                       JOIN kelas k ON gmk.kelas_id = k.id
                                       WHERE gmk.user_id = ?""",
                                    (user['id'],)  # Perhatikan tanda koma dan kurung tutup
                                )
                                mengajar = cursor.fetchall()
                                
                                st.session_state.guru_data = {
                                    "mapel": list(set([m['nama_mapel'] for m in mengajar])),
                                    "kelas": [m['nama_kelas'] for m in mengajar]
                                }
                            
                            st.success("Login berhasil!")
                            time.sleep(1.5)
                            st.session_state.page = "dashboard"
                            st.rerun()
                        else:
                            st.error("Username atau password salah.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat login: {e}")
            else:
                st.warning("Harap isi username dan password.")