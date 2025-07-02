import streamlit as st
import pandas as pd
from db import get_connection, init_db
import sqlite3
import time


def show_guru():
    if st.session_state.get("role") != "admin":
        st.error("Anda tidak memiliki akses ke halaman ini.")
        return

    st.title("🧑‍🏫 Manajemen Guru dan Penugasan")
    init_db()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    def load_guru_users():
        cursor.execute("SELECT id, username, role FROM user WHERE role = 'guru' ORDER BY username ASC")
        return cursor.fetchall()

    def load_all_users_for_edit():
        cursor.execute("SELECT id, username, role FROM user ORDER BY username ASC")
        return cursor.fetchall()

    def load_mapel():
        cursor.execute("SELECT id, nama_mapel, kode_mapel FROM mata_pelajaran ORDER BY nama_mapel ASC")
        return cursor.fetchall()

    def load_kelas():
        cursor.execute("SELECT id, nama_kelas, tingkat FROM kelas ORDER BY tingkat, nama_kelas ASC")
        return cursor.fetchall()

    def load_semester():
        cursor.execute("""
            SELECT s.id, ta.th_ajar || ' - ' || sp.sm_pil AS nama_semester_lengkap
            FROM semester s
            JOIN tahun_ajaran ta ON s.th_ajar_id = ta.id
            JOIN semester_pil sp ON s.sm_pil_id = sp.id
            ORDER BY ta.th_ajar DESC, sp.sm_pil ASC
        """)
        return cursor.fetchall()

    def load_penugasan():
        cursor.execute("""
            SELECT gmk.id, u.username as nama_guru, mp.nama_mapel, k.tingkat || ' - ' || k.nama_kelas as nama_kelas, 
                   (SELECT ta.th_ajar || ' - ' || sp.sm_pil FROM semester s 
                    JOIN tahun_ajaran ta ON s.th_ajar_id = ta.id 
                    JOIN semester_pil sp ON s.sm_pil_id = sp.id WHERE s.id = gmk.semester_id) as nama_semester
            FROM guru_mapel_kelas gmk
            JOIN user u ON gmk.user_id = u.id
            JOIN mata_pelajaran mp ON gmk.mapel_id = mp.id
            JOIN kelas k ON gmk.kelas_id = k.id
            ORDER BY u.username, nama_semester, mp.nama_mapel
        """)
        return cursor.fetchall()

    tab1, tab2 = st.tabs(["👤 Manajemen Akun Guru", "📚 Manajemen Penugasan Mengajar"])

    with tab1:
        st.subheader("Daftar Akun Guru")
        guru_users = load_guru_users()
        if guru_users:
            df_guru = pd.DataFrame(guru_users, columns=["ID", "Username", "Role"])
            st.dataframe(df_guru, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada pengguna dengan role 'guru'.")

        st.divider()
        st.subheader("Tambah/Edit Akun Pengguna (Guru/Admin)")
        
        def reset_edit_user_form():
            """Mengatur ulang selectbox ke state default 'Tambah Baru'."""
            st.session_state.edit_user_id = ("", "Tambah Baru")

        all_users = load_all_users_for_edit()
        
        if 'edit_user_id' not in st.session_state:
            st.session_state.edit_user_id = ("", "Tambah Baru")

        edit_user_id_options = [("", "Tambah Baru")] + [(u['id'], f"{u['username']} ({u['role']})") for u in all_users]
        
        edit_user_id_selection = st.selectbox(
            "Pilih Pengguna untuk Diedit (kosongkan untuk menambah baru)",
            options=edit_user_id_options,
            format_func=lambda x: x[1],
            key="edit_user_id"
        )

        current_username = ""
        current_role = "guru"
        selected_user_data = None
        if edit_user_id_selection and edit_user_id_selection[0]:
            user_id_to_edit = edit_user_id_selection[0]
            selected_user_data = next((u for u in all_users if u['id'] == user_id_to_edit), None)
            if selected_user_data:
                current_username = selected_user_data['username']
                current_role = selected_user_data['role']

        with st.form("form_manage_user", clear_on_submit=True):
            username_input = st.text_input("Username", value=current_username)
            
            if not (edit_user_id_selection and edit_user_id_selection[0]):
                password_input = st.text_input("Password (untuk user baru)", type="password")
            else:
                password_input = st.text_input("Password Baru (opsional)", type="password", placeholder="Kosongkan jika tidak ingin ganti password")

            role_input = st.selectbox("Role", options=["guru", "admin"], index=["guru", "admin"].index(current_role))
            
            col_submit_user, col_delete_user = st.columns(2)
            with col_submit_user:
                submitted_user = st.form_submit_button("Simpan Pengguna")
            with col_delete_user:
                show_delete_user_button = bool(edit_user_id_selection and edit_user_id_selection[0] and selected_user_data and selected_user_data['username'] != st.session_state.get('username'))
                if show_delete_user_button:
                    delete_pressed_user = st.form_submit_button("Hapus Pengguna Ini", type="secondary")
                else:
                    delete_pressed_user = False
            
            if submitted_user:
                if not username_input:
                    st.warning("Username tidak boleh kosong.")
                elif not (edit_user_id_selection and edit_user_id_selection[0]) and not password_input:
                    st.warning("Password tidak boleh kosong untuk pengguna baru.")
                else:
                    try:
                        if edit_user_id_selection and edit_user_id_selection[0]: # Mode Edit
                            user_id = edit_user_id_selection[0]
                            if password_input:
                                cursor.execute("UPDATE user SET username = ?, password = ?, role = ? WHERE id = ?",
                                               (username_input, password_input, role_input, user_id))
                            else:
                                cursor.execute("UPDATE user SET username = ?, role = ? WHERE id = ?",
                                               (username_input, role_input, user_id))
                            conn.commit()
                            st.success(f"Pengguna '{username_input}' berhasil diperbarui.")
                        else: # Mode Tambah Baru
                            cursor.execute("INSERT INTO user (username, password, role) VALUES (?, ?, ?)",
                                           (username_input, password_input, role_input))
                            conn.commit()
                            st.success(f"Pengguna '{username_input}' dengan role '{role_input}' berhasil ditambahkan.")
                        
                        
                        reset_edit_user_form()
                        st.rerun()
                        
                    except sqlite3.IntegrityError:
                        st.error(f"Username '{username_input}' sudah ada. Harap gunakan username yang unik.")
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat menyimpan: {e}")
            
            if delete_pressed_user:
                if selected_user_data and selected_user_data['username'] == st.session_state.get('username'):
                    st.error("Anda tidak dapat menghapus akun Anda sendiri.")
                else:
                    st.session_state.confirm_delete_user_id = edit_user_id_selection[0]
                    st.session_state.confirm_delete_user_nama = current_username
                    st.rerun()

        if st.session_state.get('confirm_delete_user_id'):
            st.warning(f"Apakah Anda yakin ingin menghapus pengguna '{st.session_state.get('confirm_delete_user_nama')}'? Tindakan ini juga akan menghapus semua penugasan mengajar terkait pengguna ini.")
            
            col_confirm_del_usr, col_cancel_del_usr = st.columns([1,1])
            with col_confirm_del_usr:
                if st.button("Ya, Hapus Pengguna", type="primary", on_click=reset_edit_user_form):
                    try:
                        user_id_to_delete = st.session_state.confirm_delete_user_id
                        cursor.execute("DELETE FROM guru_mapel_kelas WHERE user_id = ?", (user_id_to_delete,))
                        cursor.execute("DELETE FROM user WHERE id = ?", (user_id_to_delete,))
                        conn.commit()
                        st.success(f"Pengguna '{st.session_state.get('confirm_delete_user_nama')}' dan penugasan mengajarnya berhasil dihapus.")
                        
                        del st.session_state.confirm_delete_user_id
                        if 'confirm_delete_user_nama' in st.session_state:
                            del st.session_state.confirm_delete_user_nama
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus pengguna: {e}")
            with col_cancel_del_usr:
                if st.button("Batal"):
                    del st.session_state.confirm_delete_user_id
                    if 'confirm_delete_user_nama' in st.session_state:
                        del st.session_state.confirm_delete_user_nama
                    st.rerun()

    with tab2:
        st.subheader("Daftar Penugasan Mengajar")
        penugasan_data = load_penugasan()
        if penugasan_data:
            df_penugasan = pd.DataFrame(penugasan_data, columns=["ID", "Nama Guru", "Mata Pelajaran", "Kelas", "Semester"])
            st.dataframe(df_penugasan, use_container_width=True, hide_index=True, 
                         column_config={"ID": st.column_config.NumberColumn(width="small")})
        else:
            st.info("Belum ada data penugasan mengajar.")

        st.divider()
        st.subheader("Tambah/Hapus Penugasan Mengajar")

        guru_list = load_guru_users()
        mapel_list = load_mapel()
        kelas_list = load_kelas()
        semester_list = load_semester()
        
        col_tambah, col_hapus = st.columns(2)

        with col_tambah:
            st.subheader("Tambah Penugasan")
            if not all([guru_list, mapel_list, kelas_list, semester_list]):
                st.warning("Pastikan data Guru, Mapel, Kelas, dan Semester sudah ada.")
            else:
                with st.form("form_penugasan"):
                    selected_guru_id = st.selectbox("Pilih Guru", options=[(g['id'], g['username']) for g in guru_list], format_func=lambda x: x[1])
                    selected_mapel_id = st.selectbox("Pilih Mata Pelajaran", options=[(m['id'], f"{m['nama_mapel']} ({m['kode_mapel']})") for m in mapel_list], format_func=lambda x: x[1])
                    selected_kelas_id = st.selectbox("Pilih Kelas", options=[(k['id'], f"{k['tingkat']} - {k['nama_kelas']}") for k in kelas_list], format_func=lambda x: x[1])
                    selected_semester_id = st.selectbox("Pilih Semester", options=[(s['id'], s['nama_semester_lengkap']) for s in semester_list], format_func=lambda x: x[1])
                    
                    submitted_penugasan = st.form_submit_button("Simpan Penugasan")

                    if submitted_penugasan:
                        try:
                            guru_id = selected_guru_id[0]
                            mapel_id = selected_mapel_id[0]
                            kelas_id = selected_kelas_id[0]
                            semester_id = selected_semester_id[0]
                            
                            cursor.execute("INSERT INTO guru_mapel_kelas (user_id, mapel_id, kelas_id, semester_id) VALUES (?, ?, ?, ?)",
                                           (guru_id, mapel_id, kelas_id, semester_id))
                            conn.commit()
                            st.success("Penugasan berhasil ditambahkan.")
                            time.sleep(1)
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Penugasan ini sudah ada (kombinasi Guru, Mapel, Kelas, Semester yang sama).")
                        except Exception as e:
                            st.error(f"Gagal menambahkan penugasan: {e}")

        with col_hapus:
            st.subheader("Hapus Penugasan")
            if penugasan_data:
                penugasan_id_to_delete = st.selectbox(
                    "Pilih Penugasan untuk Dihapus", 
                    options=[(p['id'], f"ID {p['id']}: {p['nama_guru']} - {p['nama_mapel']} di {p['nama_kelas']}") for p in penugasan_data],
                    format_func=lambda x: x[1],
                    key="delete_penugasan_id_selection"
                )
                
                if st.button("Hapus Penugasan Terpilih", type="secondary"):
                    try:
                        id_to_del = penugasan_id_to_delete[0]
                        cursor.execute("DELETE FROM guru_mapel_kelas WHERE id = ?", (id_to_del,))
                        conn.commit()
                        st.success("Penugasan berhasil dihapus.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus penugasan: {e}")
            else:
                st.info("Tidak ada penugasan yang bisa dihapus.")

    conn.close()

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True
        #st.session_state.role = "admin"
        #st.session_state.username = "admin"
    
    show_guru()
