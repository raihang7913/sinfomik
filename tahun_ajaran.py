import streamlit as st
import pandas as pd
from db import get_connection, init_db
import sqlite3
import time

def show_tahun_ajaran():
    # Pastikan user adalah admin
    if st.session_state.get("role") != "admin":
        st.error("Anda tidak memiliki akses ke halaman ini.")
        return

    st.title("📚 Manajemen Tahun Ajaran")
    init_db() # Inisialisasi database jika belum ada

    conn = get_connection()
    cursor = conn.cursor()

    # Fungsi untuk memuat data tahun ajaran
    def load_data_tahun_ajaran():
        cursor.execute("SELECT id, th_ajar FROM tahun_ajaran ORDER BY th_ajar DESC")
        return cursor.fetchall()

    # Menampilkan daftar tahun ajaran
    st.subheader("Daftar Tahun Ajaran")
    data_tahun_ajaran = load_data_tahun_ajaran()

    if data_tahun_ajaran:
        df_tahun_ajaran = pd.DataFrame(data_tahun_ajaran, columns=["ID", "Tahun Ajaran"])
        st.dataframe(df_tahun_ajaran, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data tahun ajaran.")

    st.divider()

    # Form untuk menambah atau mengedit tahun ajaran
    st.subheader("Tambah/Edit Tahun Ajaran")

    # Pilihan untuk edit atau tambah baru
    # Default ke "Tambah Baru" jika session state belum ada atau kosong
    default_edit_option = ("", "Tambah Baru")
    if 'edit_th_ajar_id_selection' in st.session_state and st.session_state.edit_th_ajar_id_selection:
        # Coba cari apakah pilihan yang tersimpan masih valid di data_tahun_ajaran
        is_still_valid = any(th['id'] == st.session_state.edit_th_ajar_id_selection[0] for th in data_tahun_ajaran)
        if is_still_valid:
            default_edit_option = st.session_state.edit_th_ajar_id_selection
        else: # Jika tidak valid lagi (misalnya setelah dihapus), reset
            st.session_state.edit_th_ajar_id_selection = default_edit_option
            
    # Simpan pilihan selectbox ke session state yang berbeda agar tidak konflik
    # saat mencoba meresetnya secara manual setelah submit form.
    # Biarkan Streamlit menangani state widget ini.
    edit_id_tuple = st.selectbox("Pilih Tahun Ajaran untuk Diedit (kosongkan untuk menambah baru)", 
                           options=[("", "Tambah Baru")] + [(th['id'], th['th_ajar']) for th in data_tahun_ajaran],
                           index=0, # Selalu default ke "Tambah Baru" pada awalnya atau setelah rerun
                           format_func=lambda x: x[1], 
                           key="edit_th_ajar_selectbox") # Menggunakan key yang berbeda untuk selectbox

    current_th_ajar = ""
    edit_id_val = None # ID aktual yang akan digunakan untuk operasi DB

    if edit_id_tuple and edit_id_tuple[0]: # Jika memilih untuk edit dari selectbox
        selected_data = next((th for th in data_tahun_ajaran if th['id'] == edit_id_tuple[0]), None)
        if selected_data:
            current_th_ajar = selected_data['th_ajar']
            edit_id_val = edit_id_tuple[0] # Ambil ID untuk operasi
    
    with st.form("form_tahun_ajaran", clear_on_submit=True): # clear_on_submit akan mereset input di dalam form
        th_ajar_input = st.text_input("Tahun Ajaran (e.g., 2023/2024)", value=current_th_ajar if edit_id_val else "", placeholder="Contoh: 2023/2024")
        
        col_submit, col_delete = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button("Simpan")
        with col_delete:
            show_delete_button = bool(edit_id_val) 
            if show_delete_button:
                delete_pressed = st.form_submit_button("Hapus Tahun Ajaran Ini", type="secondary")
            else:
                delete_pressed = False


        if submitted:
            if not th_ajar_input:
                st.warning("Nama tahun ajaran tidak boleh kosong.")
            else:
                try:
                    if edit_id_val: # Mode Edit (menggunakan edit_id_val dari luar form)
                        cursor.execute("UPDATE tahun_ajaran SET th_ajar = ? WHERE id = ?", (th_ajar_input, edit_id_val))
                        conn.commit()
                        st.success(f"Tahun ajaran '{th_ajar_input}' berhasil diperbarui.")
                        st.toast(f"Berhasil perbarui: {th_ajar_input} 🎉", icon="✅")
                    else: # Mode Tambah Baru
                        cursor.execute("INSERT INTO tahun_ajaran (th_ajar) VALUES (?)", (th_ajar_input,))
                        conn.commit()
                        st.success(f"Tahun ajaran '{th_ajar_input}' berhasil ditambahkan.")
                        st.toast(f"Berhasil tambah: {th_ajar_input} ✨", icon="✅")
                    
                    # Tidak perlu mengubah session state selectbox secara manual di sini
                    # st.rerun() akan memuat ulang widget dan data
                    time.sleep(2)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"Tahun ajaran '{th_ajar_input}' sudah ada atau terjadi kesalahan integritas data.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")
        
        if delete_pressed and edit_id_val:
            st.session_state.confirm_delete_th_ajar_id = edit_id_val
            st.session_state.confirm_delete_th_ajar_nama = current_th_ajar # Nama yang ditampilkan di selectbox saat itu
            st.rerun()


    # Logika konfirmasi penghapusan
    if 'confirm_delete_th_ajar_id' in st.session_state and st.session_state.confirm_delete_th_ajar_id:
        st.warning(f"Apakah Anda yakin ingin menghapus tahun ajaran '{st.session_state.confirm_delete_th_ajar_nama}'? Tindakan ini tidak dapat diurungkan dan dapat mempengaruhi data terkait (misalnya Semester).")
        
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("Ya, Hapus", type="primary"):
                try:
                    cursor.execute("SELECT COUNT(*) FROM semester WHERE th_ajar_id = ?", (st.session_state.confirm_delete_th_ajar_id,))
                    if cursor.fetchone()[0] > 0:
                        st.error(f"Tidak dapat menghapus tahun ajaran '{st.session_state.confirm_delete_th_ajar_nama}' karena masih memiliki data semester terkait. Hapus semester terlebih dahulu.")
                    else:
                        cursor.execute("DELETE FROM tahun_ajaran WHERE id = ?", (st.session_state.confirm_delete_th_ajar_id,))
                        conn.commit()
                        st.success(f"Tahun ajaran '{st.session_state.confirm_delete_th_ajar_nama}' berhasil dihapus.")
                    
                    del st.session_state.confirm_delete_th_ajar_id
                    if 'confirm_delete_th_ajar_nama' in st.session_state: # Pastikan ada sebelum dihapus
                        del st.session_state.confirm_delete_th_ajar_nama
                    # Tidak perlu reset selectbox manual, biarkan rerun
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menghapus tahun ajaran: {e}")
                    if 'confirm_delete_th_ajar_id' in st.session_state: del st.session_state.confirm_delete_th_ajar_id # Bersihkan jika error
                    if 'confirm_delete_th_ajar_nama' in st.session_state: del st.session_state.confirm_delete_th_ajar_nama
                    st.rerun()
        with col_cancel:
            if st.button("Batal"):
                if 'confirm_delete_th_ajar_id' in st.session_state: del st.session_state.confirm_delete_th_ajar_id
                if 'confirm_delete_th_ajar_nama' in st.session_state: del st.session_state.confirm_delete_th_ajar_nama
                st.rerun()

    conn.close()

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True 
    
    show_tahun_ajaran()