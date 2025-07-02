import streamlit as st

# Impor modul-modul yang sudah ada dan yang baru
from dashboard import show_dashboard
from login import show_login
from logout import show_logout

from tahun_ajaran import show_tahun_ajaran
from semester import show_semester
from kelas import show_kelas
from matapelajaran import show_matapelajaran
from guru import show_guru
from siswa import show_siswa
from nilai import show_nilai


# Inisialisasi session state dasar jika belum ada
if "page" not in st.session_state:
    st.session_state.page = "dashboard" # Halaman default
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None


# --- Sidebar Navigasi ---
st.sidebar.title(" SINFOMIK")
st.sidebar.markdown("---")

# Fungsi bantuan untuk tombol navigasi dengan gaya
def nav_button(label, page_key, icon=""):
    # Cek apakah halaman saat ini adalah halaman yang dituju tombol
    is_active = st.session_state.page == page_key
    
    # Gaya untuk tombol aktif dan non-aktif (opsional, bisa disesuaikan)
    # Untuk kesederhanaan, kita tidak akan menggunakan CSS kompleks di sini,
    # Streamlit menangani tampilan tombol dengan baik.
    # Jika ingin gaya khusus, bisa menggunakan st.markdown dengan HTML/CSS.

    button_label = f"{icon} {label}" if icon else label
    if st.sidebar.button(button_label, key=page_key, use_container_width=True):
        st.session_state.page = page_key
        st.rerun() # Rerun agar halaman segera diperbarui

# Tombol navigasi berdasarkan status login dan peran
nav_button("Beranda", "dashboard", icon="🏠")

if st.session_state.get("logged_in", False):
    # Menu untuk pengguna yang sudah login
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Login sebagai: {st.session_state.username} ({st.session_state.role})")

    if st.session_state.get("role") == "admin":
        st.sidebar.markdown("**Menu Admin**")
        nav_button("Tahun Ajaran", "tahun_ajaran", icon="📚")
        nav_button("Semester & Aktifasi", "semester", icon="📅")
        nav_button("Manajemen Kelas", "kelas", icon="🏫")
        nav_button("Mata Pelajaran", "matapelajaran", icon="📖")
        nav_button("Guru & Penugasan", "guru", icon="🧑‍🏫")
        nav_button("Manajemen Siswa", "siswa", icon="👨‍🎓")
        # Admin mungkin tidak langsung input nilai, tapi bisa melihat halaman nilai jika diperlukan
        # nav_button("Lihat Nilai (Admin View)", "nilai_admin_view", icon="📝") 
        # Untuk saat ini, halaman nilai utama difokuskan untuk guru.

    elif st.session_state.get("role") == "guru":
        st.sidebar.markdown("**Menu Guru**")
        nav_button("Input & Rekap Nilai", "nilai", icon="📝")
        # Guru mungkin perlu melihat daftar siswa di kelasnya, atau jadwalnya.
        # Ini bisa ditambahkan sebagai fitur minor di masa depan.

    st.sidebar.markdown("---")
    nav_button("Logout", "logout", icon="🚪")

else:
    # Menu untuk pengguna yang belum login
    st.sidebar.markdown("---")
    nav_button("Login", "login", icon="🔑")

st.sidebar.markdown("---")
st.sidebar.info("© 2024 SINFOMIK App")


# --- Routing Halaman Utama ---
page_to_display = st.session_state.page

if page_to_display == "login":
    show_login()
elif page_to_display == "logout":
    if st.session_state.logged_in: # Hanya tampilkan jika benar-benar login
        show_logout()
    else: # Jika mencoba akses logout tanpa login, redirect ke login
        st.warning("Anda belum login.")
        st.session_state.page = "login"
        st.rerun()
else: # Halaman yang memerlukan atau tidak memerlukan login
    if page_to_display == "dashboard":
        show_dashboard()
    
    # Halaman yang memerlukan login
    elif not st.session_state.get("logged_in", False):
        st.warning("Sesi Anda telah berakhir atau Anda belum login. Silakan login terlebih dahulu.")
        # Tombol untuk kembali ke login jika sesi habis di tengah jalan
        if st.button("Ke Halaman Login"):
            st.session_state.page = "login"
            st.rerun()
    
    # Halaman setelah login
    else:
        current_role = st.session_state.get("role")
        if page_to_display == "tahun_ajaran":
            if current_role == "admin": show_tahun_ajaran()
            else: st.error("Akses ditolak. Hanya admin.")
        
        elif page_to_display == "semester":
            if current_role == "admin": show_semester()
            else: st.error("Akses ditolak. Hanya admin.")

        elif page_to_display == "kelas":
            if current_role == "admin": show_kelas()
            else: st.error("Akses ditolak. Hanya admin.")

        elif page_to_display == "matapelajaran":
            if current_role == "admin": show_matapelajaran()
            else: st.error("Akses ditolak. Hanya admin.")

        elif page_to_display == "guru":
            if current_role == "admin": show_guru()
            else: st.error("Akses ditolak. Hanya admin.")
            
        elif page_to_display == "siswa":
            # Modul siswa sekarang hanya untuk admin berdasarkan perubahan terakhir kita
            if current_role == "admin": show_siswa()
            else: st.error("Akses ditolak. Hanya admin.")
        
        elif page_to_display == "nilai":
            if current_role == "guru": show_nilai()
            # elif current_role == "admin": # Jika admin juga boleh lihat (tampilan read-only mungkin)
                # show_nilai_admin_view() # Perlu fungsi terpisah
            else: st.error("Akses ditolak. Hanya guru yang dapat mengakses input nilai.")
        
        else:
            # Jika halaman tidak dikenal setelah login, kembali ke dashboard
            st.warning(f"Halaman '{page_to_display}' tidak ditemukan. Mengarahkan ke Beranda.")
            st.session_state.page = "dashboard"
            st.rerun()

