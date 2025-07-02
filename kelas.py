import streamlit as st
import pandas as pd
from db import get_connection, init_db
import sqlite3

def show_kelas():
    # Pastikan user adalah admin
    if st.session_state.get("role") != "admin":
        st.error("Anda tidak memiliki akses ke halaman ini.")
        return

    st.title("🏫 Manajemen Kelas")
    init_db() # Inisialisasi database jika belum ada

    conn = get_connection()
    cursor = conn.cursor()

    # Fungsi untuk memuat data kelas
    def load_data_kelas():
        cursor.execute("SELECT id, nama_kelas, tingkat FROM kelas ORDER BY tingkat, nama_kelas ASC")
        return cursor.fetchall()

    # Menampilkan daftar kelas
    st.subheader("Daftar Kelas")
    data_kelas = load_data_kelas()

    if data_kelas:
        df_kelas = pd.DataFrame(data_kelas, columns=["ID", "Nama Kelas", "Tingkat"])
        st.dataframe(df_kelas, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data kelas.")

    st.divider()

    # Form untuk menambah atau mengedit kelas
    st.subheader("Tambah/Edit Kelas")

    # Pilihan untuk edit atau tambah baru
    edit_id_kelas = st.selectbox("Pilih Kelas untuk Diedit (kosongkan untuk menambah baru)", 
                                 options=[("", "Tambah Baru")] + [(k['id'], f"{k['tingkat']} - {k['nama_kelas']}") for k in data_kelas],
                                 format_func=lambda x: x[1], key="edit_kelas_id")

    current_nama_kelas = ""
    current_tingkat = ""
    if edit_id_kelas and edit_id_kelas[0]: # Jika memilih untuk edit
        selected_data_kelas = next((k for k in data_kelas if k['id'] == edit_id_kelas[0]), None)
        if selected_data_kelas:
            current_nama_kelas = selected_data_kelas['nama_kelas']
            current_tingkat = selected_data_kelas['tingkat']
    
    with st.form("form_kelas", clear_on_submit=True):
        nama_kelas_input = st.text_input("Nama Kelas (e.g., A, B, IPA 1)", value=current_nama_kelas, placeholder="Contoh: A")
        # Pilihan tingkat bisa dibuat lebih dinamis jika perlu, untuk sekarang menggunakan list statis
        tingkat_options = ["10", "11", "12", "Lainnya"] 
        if current_tingkat and current_tingkat not in tingkat_options:
            tingkat_options.append(current_tingkat) # Tambahkan tingkat saat ini jika tidak ada di opsi default
        
        # Set index default untuk selectbox tingkat
        default_tingkat_index = 0
        if current_tingkat:
            try:
                default_tingkat_index = tingkat_options.index(current_tingkat)
            except ValueError:
                default_tingkat_index = 0 # Jika tidak ditemukan, default ke opsi pertama

        tingkat_input = st.selectbox("Tingkat Kelas", options=tingkat_options, index=default_tingkat_index)
        
        col_submit_kelas, col_delete_kelas = st.columns(2)
        with col_submit_kelas:
            submitted_kelas = st.form_submit_button("Simpan")
        with col_delete_kelas:
            show_delete_button_kelas = bool(edit_id_kelas and edit_id_kelas[0])
            if show_delete_button_kelas:
                delete_pressed_kelas = st.form_submit_button("Hapus Kelas Ini", type="secondary")
            else:
                delete_pressed_kelas = False

        if submitted_kelas:
            if not nama_kelas_input or not tingkat_input:
                st.warning("Nama kelas dan tingkat tidak boleh kosong.")
            else:
                try:
                    if edit_id_kelas and edit_id_kelas[0]: # Mode Edit
                        cursor.execute("UPDATE kelas SET nama_kelas = ?, tingkat = ? WHERE id = ?", 
                                       (nama_kelas_input, tingkat_input, edit_id_kelas[0]))
                        conn.commit()
                        st.success(f"Kelas '{tingkat_input} - {nama_kelas_input}' berhasil diperbarui.")
                    else: # Mode Tambah Baru
                        cursor.execute("INSERT INTO kelas (nama_kelas, tingkat) VALUES (?, ?)", 
                                       (nama_kelas_input, tingkat_input))
                        conn.commit()
                        st.success(f"Kelas '{tingkat_input} - {nama_kelas_input}' berhasil ditambahkan.")
                    
                    st.session_state.edit_kelas_id = ("", "Tambah Baru")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"Kelas '{tingkat_input} - {nama_kelas_input}' sudah ada atau terjadi kesalahan integritas data.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")
        
        if delete_pressed_kelas and edit_id_kelas and edit_id_kelas[0]:
            st.session_state.confirm_delete_kelas_id = edit_id_kelas[0]
            st.session_state.confirm_delete_kelas_nama = f"{current_tingkat} - {current_nama_kelas}"
            st.rerun()

    # Logika konfirmasi penghapusan kelas
    if 'confirm_delete_kelas_id' in st.session_state and st.session_state.confirm_delete_kelas_id:
        st.warning(f"Apakah Anda yakin ingin menghapus kelas '{st.session_state.confirm_delete_kelas_nama}'? Menghapus kelas akan mengatur ulang `kelas_id` pada siswa yang terdaftar di kelas ini menjadi KOSONG (NULL). Data siswa tidak akan terhapus.")
        
        col_confirm_del_kelas, col_cancel_del_kelas = st.columns(2)
        with col_confirm_del_kelas:
            if st.button("Ya, Hapus Kelas", type="primary"):
                try:
                    # Hapus kelas (siswa.kelas_id akan di-set NULL karena ON DELETE SET NULL)
                    cursor.execute("DELETE FROM kelas WHERE id = ?", (st.session_state.confirm_delete_kelas_id,))
                    conn.commit()
                    st.success(f"Kelas '{st.session_state.confirm_delete_kelas_nama}' berhasil dihapus. Siswa yang sebelumnya di kelas ini kini tidak memiliki kelas.")
                    
                    del st.session_state.confirm_delete_kelas_id
                    if 'confirm_delete_kelas_nama' in st.session_state:
                        del st.session_state.confirm_delete_kelas_nama
                    st.session_state.edit_kelas_id = ("", "Tambah Baru")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menghapus kelas: {e}")
                    if 'confirm_delete_kelas_id' in st.session_state:
                        del st.session_state.confirm_delete_kelas_id
                    if 'confirm_delete_kelas_nama' in st.session_state:
                        del st.session_state.confirm_delete_kelas_nama
                    st.rerun()
        with col_cancel_del_kelas:
            if st.button("Batal Hapus"):
                if 'confirm_delete_kelas_id' in st.session_state:
                    del st.session_state.confirm_delete_kelas_id
                if 'confirm_delete_kelas_nama' in st.session_state:
                    del st.session_state.confirm_delete_kelas_nama
                st.rerun()

    conn.close()

if __name__ == "__main__":
    # Untuk pengujian lokal (opsional)
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.role = "admin"
        st.session_state.username = "test_admin_kelas"
    
    show_kelas()
