import streamlit as st
import pandas as pd
from db import get_connection, init_db
import sqlite3

def show_semester():
    # Pastikan user adalah admin
    if st.session_state.get("role") != "admin":
        st.error("Anda tidak memiliki akses ke halaman ini.")
        if st.button("Kembali ke Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    st.title("📅 Manajemen Semester")
    init_db() 

    conn = get_connection()
    cursor = conn.cursor()

    # Fungsi untuk memuat data
    def load_data_tahun_ajaran():
        cursor.execute("SELECT id, th_ajar FROM tahun_ajaran ORDER BY th_ajar DESC")
        return cursor.fetchall()

    def load_data_semester_pil():
        cursor.execute("SELECT id, sm_pil FROM semester_pil ORDER BY id ASC") # Ganjil, Genap
        return cursor.fetchall()

    def load_data_semester_lengkap():
        # Pastikan query ini menggunakan nama kolom yang benar dari tabel semester
        # yaitu 'nama_semester' bukan 'nama'
        cursor.execute("""
            SELECT s.id, ta.th_ajar, sp.sm_pil, s.nama_semester, s.aktif
            FROM semester s
            JOIN tahun_ajaran ta ON s.th_ajar_id = ta.id
            JOIN semester_pil sp ON s.sm_pil_id = sp.id
            ORDER BY ta.th_ajar DESC, sp.id ASC
        """)
        return cursor.fetchall()

    # --- Menampilkan Daftar Semester ---
    st.subheader("Daftar Semester Tersedia")
    data_semester_lengkap = load_data_semester_lengkap()

    if data_semester_lengkap:
        # Kolom yang diambil dari query adalah 'nama_semester'
        df_semester = pd.DataFrame(data_semester_lengkap, columns=["ID", "Tahun Ajaran", "Semester Pilihan", "Nama Semester", "Aktif"])
        df_semester["Aktif"] = df_semester["Aktif"].apply(lambda x: "✅ Aktif" if x else "Tidak Aktif")
        # Menampilkan kolom yang relevan, termasuk 'Nama Semester'
        st.dataframe(df_semester[["ID", "Nama Semester", "Aktif"]], use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data semester yang ditambahkan.")

    st.divider()

    # --- Form Tambah Semester Baru ---
    st.subheader("➕ Tambah Semester Baru")
    
    tahun_ajaran_list = load_data_tahun_ajaran()
    semester_pil_list = load_data_semester_pil()

    if not tahun_ajaran_list:
        st.warning("Data Tahun Ajaran belum ada. Silakan tambahkan melalui menu 'Manajemen Tahun Ajaran' terlebih dahulu.")
        conn.close()
        return
    
    if not semester_pil_list: # Seharusnya sudah ada dari init_db
        st.error("Data Pilihan Semester (Ganjil/Genap) tidak ditemukan. Periksa database.")
        conn.close()
        return

    with st.form("form_tambah_semester", clear_on_submit=True):
        selected_th_ajar_tuple = st.selectbox(
            "Pilih Tahun Ajaran",
            options=[(ta['id'], ta['th_ajar']) for ta in tahun_ajaran_list],
            format_func=lambda x: x[1],
            key="add_sem_th_ajar"
        )
        selected_sm_pil_tuple = st.selectbox(
            "Pilih Semester",
            options=[(sp['id'], sp['sm_pil']) for sp in semester_pil_list],
            format_func=lambda x: x[1],
            key="add_sem_sm_pil"
        )
        
        submit_tambah_semester = st.form_submit_button("Tambah Semester")

        if submit_tambah_semester:
            if selected_th_ajar_tuple and selected_sm_pil_tuple:
                th_ajar_id = selected_th_ajar_tuple[0]
                th_ajar_nama = selected_th_ajar_tuple[1]
                sm_pil_id = selected_sm_pil_tuple[0]
                sm_pil_nama = selected_sm_pil_tuple[1]
                
                # Menggunakan kolom 'nama_semester' untuk penyimpanan
                nama_semester_otomatis = f"{sm_pil_nama} {th_ajar_nama}"

                try:
                    cursor.execute(
                        "INSERT INTO semester (th_ajar_id, sm_pil_id, nama_semester, aktif) VALUES (?, ?, ?, ?)",
                        (th_ajar_id, sm_pil_id, nama_semester_otomatis, 0) # Default tidak aktif
                    )
                    conn.commit()
                    st.success(f"Semester '{nama_semester_otomatis}' berhasil ditambahkan.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"Semester '{nama_semester_otomatis}' sudah ada atau kombinasi Tahun Ajaran dan Pilihan Semester tersebut sudah terdaftar.")
                except Exception as e:
                    st.error(f"Gagal menambahkan semester: {e}")
            else:
                st.warning("Harap pilih Tahun Ajaran dan Semester.")
    
    st.divider()

    # --- Kelola Semester (Aktifkan/Nonaktifkan/Hapus) ---
    st.subheader("⚙️ Kelola Semester")
    if data_semester_lengkap:
        # Pilih semester untuk dikelola, menggunakan 'nama_semester' dari data yang sudah diload
        semester_options_manage = [(s['id'], s['nama_semester']) for s in data_semester_lengkap]
        selected_semester_manage_tuple = st.selectbox(
            "Pilih Semester untuk Dikelola",
            options=[("", "Pilih...")] + semester_options_manage,
            format_func=lambda x: x[1],
            key="manage_sem_select"
        )

        if selected_semester_manage_tuple and selected_semester_manage_tuple[0]:
            semester_id_to_manage = selected_semester_manage_tuple[0]
            selected_semester_detail = next((s for s in data_semester_lengkap if s['id'] == semester_id_to_manage), None)

            if selected_semester_detail:
                # Menampilkan 'nama_semester'
                st.write(f"Detail: **{selected_semester_detail['nama_semester']}** (Status: {'Aktif' if selected_semester_detail['aktif'] else 'Tidak Aktif'})")

                col1_manage, col2_manage = st.columns(2)
                with col1_manage:
                    if not selected_semester_detail['aktif']:
                        if st.button("✅ Jadikan Aktif", key=f"aktifkan_{semester_id_to_manage}"):
                            try:
                                # Nonaktifkan semua semester lain dulu
                                cursor.execute("UPDATE semester SET aktif = 0 WHERE aktif = 1")
                                # Aktifkan semester yang dipilih
                                cursor.execute("UPDATE semester SET aktif = 1 WHERE id = ?", (semester_id_to_manage,))
                                conn.commit()
                                st.success(f"Semester '{selected_semester_detail['nama_semester']}' berhasil diaktifkan.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal mengaktifkan semester: {e}")
                    else:
                        st.success("Semester ini sudah aktif.")
                
                with col2_manage:
                    if st.button("🗑️ Hapus Semester Ini", key=f"hapus_{semester_id_to_manage}", type="secondary"):
                        st.session_state.confirm_delete_semester_id = semester_id_to_manage
                        st.session_state.confirm_delete_semester_nama = selected_semester_detail['nama_semester']
                        st.rerun()
    else:
        st.info("Tidak ada semester untuk dikelola.")


    # Logika konfirmasi penghapusan semester
    if st.session_state.get('confirm_delete_semester_id'):
        st.warning(f"Apakah Anda yakin ingin menghapus semester '{st.session_state.confirm_delete_semester_nama}'? Menghapus semester akan menghapus SEMUA data terkait: Penugasan Guru, Konfigurasi Mata Pelajaran Semester, dan SEMUA NILAI pada semester ini. Tindakan ini TIDAK DAPAT DIURUNGKAN.")
        
        col_confirm_del_sem, col_cancel_del_sem = st.columns(2)
        with col_confirm_del_sem:
            if st.button("Ya, Hapus Semester Beserta Semua Data Terkait", type="primary"):
                try:
                    sem_id_to_del = st.session_state.confirm_delete_semester_id
                    
                    # Hapus data terkait dari tabel lain terlebih dahulu
                    cursor.execute("DELETE FROM nilai WHERE semester_id = ?", (sem_id_to_del,))
                    cursor.execute("DELETE FROM guru_mapel_kelas WHERE semester_id = ?", (sem_id_to_del,))
                    cursor.execute("DELETE FROM mapel_semester_config WHERE semester_id = ?", (sem_id_to_del,))
                    
                    # Hapus semester itu sendiri
                    cursor.execute("DELETE FROM semester WHERE id = ?", (sem_id_to_del,))
                    conn.commit()
                    st.success(f"Semester '{st.session_state.confirm_delete_semester_nama}' dan semua data terkaitnya berhasil dihapus.")
                    
                    del st.session_state.confirm_delete_semester_id
                    if 'confirm_delete_semester_nama' in st.session_state: del st.session_state.confirm_delete_semester_nama
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menghapus semester: {e}")
                    if 'confirm_delete_semester_id' in st.session_state: del st.session_state.confirm_delete_semester_id
                    if 'confirm_delete_semester_nama' in st.session_state: del st.session_state.confirm_delete_semester_nama
                    st.rerun()
        with col_cancel_del_sem:
            if st.button("Batal Hapus Semester"):
                if 'confirm_delete_semester_id' in st.session_state: del st.session_state.confirm_delete_semester_id
                if 'confirm_delete_semester_nama' in st.session_state: del st.session_state.confirm_delete_semester_nama
                st.rerun()

    conn.close()

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.role = "admin"
        st.session_state.username = "test_admin_semester"
    
    # Dummy data untuk testing jika diperlukan (pastikan tabel tahun_ajaran dan semester_pil ada isinya)
    # init_db() 
    # conn_test = get_connection()
    # cursor_test = conn_test.cursor()
    # cursor_test.execute("SELECT COUNT(*) FROM tahun_ajaran")
    # if cursor_test.fetchone()[0] == 0:
    #     cursor_test.execute("INSERT INTO tahun_ajaran (th_ajar) VALUES ('2023/2024'), ('2024/2025')")
    # cursor_test.execute("SELECT COUNT(*) FROM semester_pil") # Seharusnya sudah ada dari init_db di db.py
    # if cursor_test.fetchone()[0] == 0:
    #     cursor_test.execute("INSERT INTO semester_pil (sm_pil) VALUES ('Ganjil'), ('Genap')")
    # conn_test.commit()
    # conn_test.close()
        
    show_semester()
