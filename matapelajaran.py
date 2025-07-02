import streamlit as st
import pandas as pd
from db import get_connection, init_db
import sqlite3

def show_matapelajaran():
    # Pastikan user adalah admin
    if st.session_state.get("role") != "admin":
        st.error("Anda tidak memiliki akses ke halaman ini.")
        return

    st.title("📖 Manajemen Mata Pelajaran")
    init_db() 

    conn = get_connection()
    cursor = conn.cursor()

    # Fungsi untuk memuat data
    def load_data_mapel():
        cursor.execute("SELECT id, nama_mapel, kode_mapel FROM mata_pelajaran ORDER BY nama_mapel ASC")
        return cursor.fetchall()

    def load_data_semester():
        cursor.execute("""
            SELECT s.id, ta.th_ajar || ' - ' || sp.sm_pil AS nama_semester_lengkap
            FROM semester s
            JOIN tahun_ajaran ta ON s.th_ajar_id = ta.id
            JOIN semester_pil sp ON s.sm_pil_id = sp.id
            ORDER BY ta.th_ajar DESC, sp.sm_pil ASC
        """)
        return cursor.fetchall()

    def load_mapel_semester_config(mapel_id):
        cursor.execute("""
            SELECT semester_id, is_active 
            FROM mapel_semester_config 
            WHERE mapel_id = ?
        """, (mapel_id,))
        return {row['semester_id']: row['is_active'] for row in cursor.fetchall()}

    # --- Manajemen Mata Pelajaran (CRUD) ---
    st.subheader("Daftar Mata Pelajaran")
    data_mapel = load_data_mapel()

    if data_mapel:
        df_mapel = pd.DataFrame(data_mapel, columns=["ID", "Nama Mata Pelajaran", "Kode"])
        st.dataframe(df_mapel, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data mata pelajaran.")

    st.divider()

    st.subheader("Tambah/Edit Mata Pelajaran")
    edit_id_mapel = st.selectbox("Pilih Mata Pelajaran untuk Diedit (kosongkan untuk menambah baru)", 
                                 options=[("", "Tambah Baru")] + [(m['id'], f"{m['nama_mapel']} ({m['kode_mapel']})") for m in data_mapel],
                                 format_func=lambda x: x[1], key="edit_mapel_id")

    current_nama_mapel = ""
    current_kode_mapel = ""
    if edit_id_mapel and edit_id_mapel[0]:
        selected_data_mapel = next((m for m in data_mapel if m['id'] == edit_id_mapel[0]), None)
        if selected_data_mapel:
            current_nama_mapel = selected_data_mapel['nama_mapel']
            current_kode_mapel = selected_data_mapel['kode_mapel']
    
    with st.form("form_mapel", clear_on_submit=False): # clear_on_submit=False agar state selectbox tidak reset saat submit
        nama_mapel_input = st.text_input("Nama Mata Pelajaran", value=current_nama_mapel, placeholder="Contoh: Matematika Wajib")
        kode_mapel_input = st.text_input("Kode Mata Pelajaran (UNIK)", value=current_kode_mapel, placeholder="Contoh: MTK-WAJIB-X")
        
        col_submit_mapel, col_delete_mapel = st.columns(2)
        with col_submit_mapel:
            submitted_mapel = st.form_submit_button("Simpan Mata Pelajaran")
        with col_delete_mapel:
            show_delete_button_mapel = bool(edit_id_mapel and edit_id_mapel[0])
            if show_delete_button_mapel:
                delete_pressed_mapel = st.form_submit_button("Hapus Mata Pelajaran Ini", type="secondary")
            else:
                delete_pressed_mapel = False

        if submitted_mapel:
            if not nama_mapel_input or not kode_mapel_input:
                st.warning("Nama dan Kode mata pelajaran tidak boleh kosong.")
            else:
                try:
                    if edit_id_mapel and edit_id_mapel[0]: # Mode Edit
                        cursor.execute("UPDATE mata_pelajaran SET nama_mapel = ?, kode_mapel = ? WHERE id = ?", 
                                       (nama_mapel_input, kode_mapel_input, edit_id_mapel[0]))
                        conn.commit()
                        st.success(f"Mata pelajaran '{nama_mapel_input}' berhasil diperbarui.")
                    else: # Mode Tambah Baru
                        cursor.execute("INSERT INTO mata_pelajaran (nama_mapel, kode_mapel) VALUES (?, ?)", 
                                       (nama_mapel_input, kode_mapel_input))
                        conn.commit()
                        st.success(f"Mata pelajaran '{nama_mapel_input}' berhasil ditambahkan.")
                    
                    # Reset form edit ke tambah baru setelah submit berhasil
                    st.session_state.edit_mapel_id = ("", "Tambah Baru")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"Kode mata pelajaran '{kode_mapel_input}' sudah ada. Harap gunakan kode yang unik.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")
        
        if delete_pressed_mapel and edit_id_mapel and edit_id_mapel[0]:
            st.session_state.confirm_delete_mapel_id = edit_id_mapel[0]
            st.session_state.confirm_delete_mapel_nama = f"{current_nama_mapel} ({current_kode_mapel})"
            st.rerun()

    # Logika konfirmasi penghapusan mata pelajaran
    if st.session_state.get('confirm_delete_mapel_id'):
        st.warning(f"Apakah Anda yakin ingin menghapus mata pelajaran '{st.session_state.confirm_delete_mapel_nama}'? Tindakan ini akan menghapus semua konfigurasi semester dan data nilai terkait mata pelajaran ini.")
        
        col_confirm_del_mapel, col_cancel_del_mapel = st.columns(2)
        with col_confirm_del_mapel:
            if st.button("Ya, Hapus Mata Pelajaran", type="primary"):
                try:
                    mapel_id_to_delete = st.session_state.confirm_delete_mapel_id
                    # Hapus dari tabel nilai, guru_mapel_kelas, mapel_semester_config, lalu mata_pelajaran
                    cursor.execute("DELETE FROM nilai WHERE mapel_id = ?", (mapel_id_to_delete,))
                    cursor.execute("DELETE FROM guru_mapel_kelas WHERE mapel_id = ?", (mapel_id_to_delete,))
                    cursor.execute("DELETE FROM mapel_semester_config WHERE mapel_id = ?", (mapel_id_to_delete,))
                    cursor.execute("DELETE FROM mata_pelajaran WHERE id = ?", (mapel_id_to_delete,))
                    conn.commit()
                    st.success(f"Mata pelajaran '{st.session_state.confirm_delete_mapel_nama}' dan data terkait berhasil dihapus.")
                    
                    del st.session_state.confirm_delete_mapel_id
                    if 'confirm_delete_mapel_nama' in st.session_state: del st.session_state.confirm_delete_mapel_nama
                    st.session_state.edit_mapel_id = ("", "Tambah Baru")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menghapus mata pelajaran: {e}")
                    if 'confirm_delete_mapel_id' in st.session_state: del st.session_state.confirm_delete_mapel_id
                    if 'confirm_delete_mapel_nama' in st.session_state: del st.session_state.confirm_delete_mapel_nama
                    st.rerun()
        with col_cancel_del_mapel:
            if st.button("Batal Hapus Mapel"):
                if 'confirm_delete_mapel_id' in st.session_state: del st.session_state.confirm_delete_mapel_id
                if 'confirm_delete_mapel_nama' in st.session_state: del st.session_state.confirm_delete_mapel_nama
                st.rerun()
    
    st.divider()

    # --- Konfigurasi Mata Pelajaran per Semester ---
    st.subheader("Konfigurasi Status Aktif Mata Pelajaran per Semester")
    
    data_semester = load_data_semester()

    if not data_mapel:
        st.info("Silakan tambahkan data mata pelajaran terlebih dahulu untuk melakukan konfigurasi semester.")
    elif not data_semester:
        st.info("Silakan tambahkan data semester terlebih dahulu (melalui menu Semester) untuk melakukan konfigurasi.")
    else:
        selected_mapel_id_for_config = st.selectbox(
            "Pilih Mata Pelajaran untuk Dikonfigurasi",
            options=[(m['id'], f"{m['nama_mapel']} ({m['kode_mapel']})") for m in data_mapel],
            format_func=lambda x: x[1],
            key="selected_mapel_config"
        )

        if selected_mapel_id_for_config:
            mapel_id = selected_mapel_id_for_config[0]
            mapel_nama = selected_mapel_id_for_config[1]
            st.write(f"Mengatur status aktif untuk: **{mapel_nama}**")

            current_config = load_mapel_semester_config(mapel_id)

            with st.form(f"form_config_mapel_{mapel_id}"):
                cols = st.columns(len(data_semester))
                new_configs = {}

                for i, semester in enumerate(data_semester):
                    with cols[i]:
                        semester_id = semester['id']
                        semester_nama = semester['nama_semester_lengkap']
                        is_active_db = current_config.get(semester_id, 0) # Default tidak aktif jika belum ada di DB
                        
                        # Gunakan nilai dari session state jika ada (untuk mempertahankan state setelah error/submit)
                        # Ini penting jika ada banyak checkbox dan terjadi error, agar tidak reset semua
                        session_key = f"mapel_{mapel_id}_sem_{semester_id}_active"
                        if session_key not in st.session_state:
                             st.session_state[session_key] = bool(is_active_db)
                        
                        is_active_ui = st.checkbox(
                            f"{semester_nama}", 
                            value=st.session_state[session_key], 
                            key=session_key # Key unik untuk setiap checkbox
                        )
                        new_configs[semester_id] = is_active_ui
                
                submit_config = st.form_submit_button("Simpan Konfigurasi Status Aktif")

                if submit_config:
                    try:
                        for semester_id, is_active in new_configs.items():
                            # Cek apakah sudah ada entri
                            cursor.execute("SELECT id FROM mapel_semester_config WHERE mapel_id = ? AND semester_id = ?", (mapel_id, semester_id))
                            existing_entry = cursor.fetchone()
                            if existing_entry:
                                cursor.execute("UPDATE mapel_semester_config SET is_active = ? WHERE id = ?", (is_active, existing_entry['id']))
                            else:
                                cursor.execute("INSERT INTO mapel_semester_config (mapel_id, semester_id, is_active) VALUES (?, ?, ?)",
                                               (mapel_id, semester_id, is_active))
                        conn.commit()
                        st.success(f"Konfigurasi status aktif untuk '{mapel_nama}' berhasil disimpan.")
                        # Tidak perlu rerun agar user bisa lanjut konfigurasi mapel lain atau semester lain
                        # Namun, state checkbox perlu diupdate jika ada perubahan
                        for sem_id, active_val in new_configs.items():
                            st.session_state[f"mapel_{mapel_id}_sem_{sem_id}_active"] = active_val
                        st.rerun() # Rerun untuk memuat ulang data dari DB dan memastikan UI konsisten
                    except Exception as e:
                        st.error(f"Gagal menyimpan konfigurasi: {e}")
    conn.close()

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True
        # st.session_state.role = "admin"
        # st.session_state.username = "test_admin_mapel"
    show_matapelajaran()