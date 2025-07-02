import streamlit as st
from db import get_connection, init_db
import math
import pandas as pd
import sqlite3

def show_siswa():
    # Pastikan user adalah admin
    if st.session_state.get("role") != "admin":
        st.error("Anda tidak memiliki akses ke halaman ini.")
        if st.button("Kembali ke Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    st.title("👨‍🎓 Manajemen Data Siswa")
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    # Fungsi untuk memuat data kelas
    def load_kelas_options():
        cursor.execute("SELECT id, tingkat || ' - ' || nama_kelas as nama_lengkap_kelas FROM kelas ORDER BY tingkat, nama_kelas ASC")
        return cursor.fetchall()

    kelas_options_list = load_kelas_options()
    
    # --- Form to Add New Student ---
    st.subheader("➕ Tambah Siswa Baru")
    with st.form(key='add_siswa_form', clear_on_submit=True):
        nisn = st.number_input("NISN", min_value=0, max_value=9999999999, step=1, value=None, format="%010d")
        nama = st.text_input("Nama Lengkap Siswa", placeholder="Masukkan nama lengkap")
        
        # Pilihan Kelas untuk siswa baru
        selected_kelas_id_add = None
        if kelas_options_list:
            kelas_choices_add = [("", "Pilih Kelas...")] + [(k['id'], k['nama_lengkap_kelas']) for k in kelas_options_list]
            selected_kelas_id_add_tuple = st.selectbox("Pilih Kelas untuk Siswa Baru", 
                                                       options=kelas_choices_add, 
                                                       format_func=lambda x: x[1], 
                                                       key="add_siswa_kelas")
            if selected_kelas_id_add_tuple and selected_kelas_id_add_tuple[0]:
                selected_kelas_id_add = selected_kelas_id_add_tuple[0]
        else:
            st.caption("Belum ada data kelas. Tambahkan kelas terlebih dahulu di menu Manajemen Kelas.")

        submit_button = st.form_submit_button(label="Tambah Siswa")

        if submit_button:
            if nisn and nama:
                try:
                    cursor.execute("INSERT INTO siswa (nisn, nama, kelas_id) VALUES (?, ?, ?)", 
                                   (nisn, nama, selected_kelas_id_add))
                    conn.commit()
                    st.success(f"Siswa '{nama}' (NISN: {nisn}) berhasil ditambahkan.")
                    st.rerun() 
                except sqlite3.IntegrityError as e:
                    if "UNIQUE constraint failed: siswa.nisn" in str(e):
                        st.error(f"Gagal menambahkan siswa: NISN {nisn} sudah terdaftar.")
                    else:
                        st.error(f"Gagal menambahkan siswa: Terjadi kesalahan integritas data. {e}")
                except Exception as e:
                    st.error(f"Gagal menambahkan siswa: {e}")
            else:
                st.warning("Mohon isi NISN dan Nama Lengkap Siswa.")

    st.divider()

    # --- Pencarian Siswa ---
    st.subheader("🔍 Cari Siswa")
    search_term = st.text_input("Cari berdasarkan NISN atau Nama", "", placeholder="Kosongkan untuk tampilkan semua siswa")

    # --- Students List ---
    st.subheader("📋 Daftar Siswa")

    # Inisialisasi session state untuk edit dan delete
    if "confirm_delete_siswa_id" not in st.session_state:
        st.session_state.confirm_delete_siswa_id = None
    if "edit_siswa_id" not in st.session_state:
        st.session_state.edit_siswa_id = None
        st.session_state.is_editing_siswa = False

    try:
        # Query untuk mengambil data siswa beserta nama kelasnya
        query_siswa = """
            SELECT s.id, s.nisn, s.nama, s.kelas_id, k.tingkat || ' - ' || k.nama_kelas as nama_kelas 
            FROM siswa s
            LEFT JOIN kelas k ON s.kelas_id = k.id
        """
        params_siswa = []
        if search_term:
            query_siswa += " WHERE s.nisn LIKE ? OR s.nama LIKE ?"
            params_siswa.extend([f"%{search_term}%", f"%{search_term}%"])
        
        query_siswa += " ORDER BY s.nama ASC" # Atau s.id, s.nisn
        
        cursor.execute(query_siswa, tuple(params_siswa))
        siswa_list = cursor.fetchall()

        if siswa_list:
            # Menggunakan Pandas DataFrame untuk tampilan yang lebih baik dan interaktif
            df_siswa = pd.DataFrame(siswa_list, columns=["ID", "NISN", "Nama Siswa", "Kelas ID", "Kelas"])
            
            # Kolom aksi (Edit dan Hapus)
            # Kita akan membuat kolom ini secara manual di loop karena st.dataframe tidak mendukung tombol secara langsung
            
            st.write(f"Total siswa ditemukan: {len(df_siswa)}")

            # Header tabel manual
            cols_header = st.columns([1, 2, 3, 2, 1, 1]) # Sesuaikan rasio kolom
            with cols_header[0]: st.markdown("**ID**")
            with cols_header[1]: st.markdown("**NISN**")
            with cols_header[2]: st.markdown("**Nama Siswa**")
            with cols_header[3]: st.markdown("**Kelas**")
            with cols_header[4]: st.markdown("**Edit**")
            with cols_header[5]: st.markdown("**Hapus**")

            for index, siswa_row in df_siswa.iterrows():
                cols_data = st.columns([1, 2, 3, 2, 1, 1])
                with cols_data[0]: st.write(siswa_row['ID'])
                with cols_data[1]: st.write(f"{siswa_row['NISN']:010d}" if siswa_row['NISN'] else "-")
                with cols_data[2]: st.write(siswa_row['Nama Siswa'])
                with cols_data[3]: st.write(siswa_row['Kelas'] if siswa_row['Kelas'] else "Belum ada kelas")
                
                with cols_data[4]: # Tombol Edit
                    if st.button("✏️", key=f"edit_siswa_{siswa_row['ID']}", help="Edit Siswa"):
                        st.session_state.edit_siswa_id = siswa_row['ID']
                        st.session_state.edit_nisn = siswa_row['NISN']
                        st.session_state.edit_nama = siswa_row['Nama Siswa']
                        st.session_state.edit_kelas_id_current = siswa_row['Kelas ID']
                        st.session_state.is_editing_siswa = True
                        st.rerun()
                
                with cols_data[5]: # Tombol Hapus
                    if st.session_state.confirm_delete_siswa_id == siswa_row['ID']:
                        if st.button("✅ Hapus?", key=f"confirm_del_siswa_{siswa_row['ID']}", type="primary", help="Konfirmasi Hapus"):
                            try:
                                cursor.execute("DELETE FROM siswa WHERE id = ?", (siswa_row['ID'],))
                                # Juga hapus nilai terkait siswa ini
                                cursor.execute("DELETE FROM nilai WHERE siswa_id = ?", (siswa_row['ID'],))
                                conn.commit()
                                st.success(f"Siswa '{siswa_row['Nama Siswa']}' dan semua nilainya berhasil dihapus.")
                                st.session_state.confirm_delete_siswa_id = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal menghapus siswa: {e}")
                                st.session_state.confirm_delete_siswa_id = None # Reset state
                        if st.button("❌ Batal", key=f"cancel_del_siswa_{siswa_row['ID']}", help="Batal Hapus"):
                            st.session_state.confirm_delete_siswa_id = None
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"hapus_siswa_{siswa_row['ID']}", help="Hapus Siswa"):
                            st.session_state.confirm_delete_siswa_id = siswa_row['ID']
                            st.rerun()
        else:
            st.info("Belum ada data siswa yang cocok dengan pencarian atau belum ada data siswa sama sekali.")

    except Exception as e:
        st.error(f"Gagal melakukan fetching data siswa: {e}")

    # --- Form Edit Siswa (Modal-like Expander) ---
    if st.session_state.get("is_editing_siswa", False) and st.session_state.edit_siswa_id is not None:
        with st.expander("✏️ Edit Data Siswa", expanded=True):
            
            edit_siswa_id = st.session_state.edit_siswa_id
            edit_nisn_val = st.session_state.get('edit_nisn', '')
            edit_nama_val = st.session_state.get('edit_nama', '')
            edit_kelas_id_current_val = st.session_state.get('edit_kelas_id_current', None)

            st.write(f"Mengedit Siswa: **{edit_nama_val}** (ID: {edit_siswa_id})")

            with st.form(key="edit_siswa_form_modal"):
                nisn_edit = st.number_input("NISN", value=edit_nisn_val, min_value=0, max_value=9999999999, step=1, format="%010d", key=f"nisn_edit_{edit_siswa_id}")
                nama_edit = st.text_input("Nama Lengkap Siswa", value=edit_nama_val, key=f"nama_edit_{edit_siswa_id}")

                # Pilihan Kelas untuk edit siswa
                selected_kelas_id_edit = None
                if kelas_options_list:
                    kelas_choices_edit = [("", "Pilih Kelas...")] + [(k['id'], k['nama_lengkap_kelas']) for k in kelas_options_list]
                    
                    # Cari index kelas saat ini untuk default selectbox
                    current_kelas_index = 0
                    if edit_kelas_id_current_val:
                        for i, option in enumerate(kelas_choices_edit):
                            if option[0] == edit_kelas_id_current_val:
                                current_kelas_index = i
                                break
                    
                    selected_kelas_id_edit_tuple = st.selectbox("Pilih Kelas Baru", 
                                                                options=kelas_choices_edit, 
                                                                index=current_kelas_index,
                                                                format_func=lambda x: x[1], 
                                                                key=f"edit_siswa_kelas_{edit_siswa_id}")
                    if selected_kelas_id_edit_tuple and selected_kelas_id_edit_tuple[0]:
                        selected_kelas_id_edit = selected_kelas_id_edit_tuple[0]
                    elif not selected_kelas_id_edit_tuple[0]: # Jika memilih "Pilih Kelas..." (kosong)
                         selected_kelas_id_edit = None


                col_save, col_cancel_edit = st.columns(2)
                with col_save:
                    save_edit = st.form_submit_button("Simpan Perubahan")
                with col_cancel_edit:
                    cancel_edit_button = st.form_submit_button("Batal Edit")


                if save_edit:
                    if nisn_edit and nama_edit:
                        try:
                            cursor.execute(
                                "UPDATE siswa SET nisn = ?, nama = ?, kelas_id = ? WHERE id = ?",
                                (nisn_edit, nama_edit, selected_kelas_id_edit, edit_siswa_id)
                            )
                            conn.commit()
                            st.success(f"Data siswa '{nama_edit}' berhasil diperbarui.")
                            st.session_state.is_editing_siswa = False
                            st.session_state.edit_siswa_id = None 
                            st.rerun()
                        except sqlite3.IntegrityError as e:
                            if "UNIQUE constraint failed: siswa.nisn" in str(e):
                                st.error(f"Gagal memperbarui: NISN {nisn_edit} sudah terdaftar untuk siswa lain.")
                            else:
                                st.error(f"Gagal memperbarui: Terjadi kesalahan integritas data. {e}")
                        except Exception as e:
                            st.error(f"Gagal memperbarui data siswa: {e}")
                    else:
                        st.warning("NISN dan Nama tidak boleh kosong.")
                
                if cancel_edit_button:
                    st.session_state.is_editing_siswa = False
                    st.session_state.edit_siswa_id = None
                    st.rerun()
    conn.close()

if __name__ == "__main__":
    # Untuk pengujian lokal
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.role = "admin" # Atau "guru" jika ingin tes akses
    
    # Inisialisasi db jika belum ada tabelnya
    # init_db() 
    # conn_test = get_connection()
    # cursor_test = conn_test.cursor()
    # # Tambahkan beberapa data kelas dummy jika belum ada untuk testing
    # cursor_test.execute("SELECT COUNT(*) FROM kelas")
    # if cursor_test.fetchone()[0] == 0:
    #     kelas_dummy = [('X IPA 1', '10'), ('XI IPS 2', '11')]
    #     cursor_test.executemany("INSERT INTO kelas (nama_kelas, tingkat) VALUES (?,?)", kelas_dummy)
    #     conn_test.commit()
    # conn_test.close()

    show_siswa()