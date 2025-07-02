import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from db import get_connection, init_db

def show_nilai():
    st.title("📝 Input dan Rekap Nilai Siswa")
    init_db()

    # Cek login dan role
    if not st.session_state.get("logged_in", False) or st.session_state.get("role") != "guru":
        st.error("Anda tidak memiliki akses ke halaman ini. Silakan login sebagai guru.")
        if st.button("Kembali ke Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    conn = get_connection()
    cursor = conn.cursor()
    guru_id = st.session_state.user_id

    # 1. Dapatkan Semester Aktif
    cursor.execute("SELECT id, nama_semester FROM semester WHERE aktif = 1 LIMIT 1")
    semester_aktif = cursor.fetchone()

    if not semester_aktif:
        st.warning("Saat ini tidak ada semester yang aktif. Admin perlu mengaktifkan satu semester terlebih dahulu.")
        conn.close()
        return
    
    semester_aktif_id = semester_aktif['id']
    st.info(f"Anda sedang menginput nilai untuk Semester: **{semester_aktif['nama_semester']}**")

    # 2. Ambil daftar kelas yang diajar guru ini di semester aktif
    cursor.execute("""
        SELECT DISTINCT k.id, k.tingkat || ' - ' || k.nama_kelas AS nama_lengkap_kelas
        FROM guru_mapel_kelas gmk
        JOIN kelas k ON gmk.kelas_id = k.id
        WHERE gmk.user_id = ? AND gmk.semester_id = ?
        ORDER BY nama_lengkap_kelas ASC
    """, (guru_id, semester_aktif_id))
    kelas_options_raw = cursor.fetchall()

    if not kelas_options_raw:
        st.error("Anda belum ditugaskan mengajar kelas apapun di semester aktif ini.")
        conn.close()
        return
    
    kelas_options = [("", "Pilih Kelas...")] + [(k['id'], k['nama_lengkap_kelas']) for k in kelas_options_raw]
    selected_kelas_tuple = st.selectbox(
        "Pilih Kelas yang Diajar",
        options=kelas_options,
        format_func=lambda x: x[1],
        key="nilai_select_kelas"
    )

    if not selected_kelas_tuple or not selected_kelas_tuple[0]:
        conn.close()
        return 
    kelas_id = selected_kelas_tuple[0]
    nama_kelas_terpilih = selected_kelas_tuple[1]

    # 3. Ambil mata pelajaran yang diajar guru di kelas & semester aktif, dan mapel tersebut aktif
    cursor.execute("""
        SELECT DISTINCT mp.id, mp.nama_mapel || ' (' || mp.kode_mapel || ')' AS nama_lengkap_mapel
        FROM guru_mapel_kelas gmk
        JOIN mata_pelajaran mp ON gmk.mapel_id = mp.id
        JOIN mapel_semester_config msc ON mp.id = msc.mapel_id AND msc.semester_id = gmk.semester_id
        WHERE gmk.user_id = ? AND gmk.kelas_id = ? AND gmk.semester_id = ? AND msc.is_active = 1
        ORDER BY nama_lengkap_mapel ASC
    """, (guru_id, kelas_id, semester_aktif_id))
    mapel_options_raw = cursor.fetchall()

    if not mapel_options_raw:
        st.error(f"Tidak ada mata pelajaran aktif yang Anda ajar di kelas {nama_kelas_terpilih} untuk semester ini, atau mata pelajaran belum dikonfigurasi aktif oleh admin.")
        conn.close()
        return

    mapel_options = [("", "Pilih Mata Pelajaran...")] + [(m['id'], m['nama_lengkap_mapel']) for m in mapel_options_raw]
    selected_mapel_tuple = st.selectbox(
        "Pilih Mata Pelajaran yang Diajar",
        options=mapel_options,
        format_func=lambda x: x[1],
        key="nilai_select_mapel"
    )

    if not selected_mapel_tuple or not selected_mapel_tuple[0]:
        conn.close()
        return
    mapel_id = selected_mapel_tuple[0]
    nama_mapel_terpilih = selected_mapel_tuple[1]

    # 4. Ambil daftar Tahap Penilaian
    cursor.execute("SELECT id, nama_tahap FROM tahap_penilaian ORDER BY nama_tahap ASC")
    tahap_options_raw = cursor.fetchall()

    if not tahap_options_raw:
        st.error("Data Tahap Penilaian (UTS, UAS, dll.) belum ada. Admin perlu menambahkannya terlebih dahulu.")
        conn.close()
        return

    tahap_options = [("", "Pilih Tahap Penilaian...")] + [(t['id'], t['nama_tahap']) for t in tahap_options_raw]
    selected_tahap_tuple = st.selectbox(
        "Pilih Tahap Penilaian",
        options=tahap_options,
        format_func=lambda x: x[1],
        key="nilai_select_tahap"
    )

    if not selected_tahap_tuple or not selected_tahap_tuple[0]:
        conn.close()
        return
    tahap_id = selected_tahap_tuple[0]
    nama_tahap_terpilih = selected_tahap_tuple[1]
    
    # 5. Ambil daftar siswa di kelas tersebut
    cursor.execute("""
        SELECT id, nisn, nama 
        FROM siswa 
        WHERE kelas_id = ?
        ORDER BY nama ASC
    """, (kelas_id,))
    siswa_kelas = cursor.fetchall()

    if not siswa_kelas:
        st.info(f"Tidak ada siswa terdaftar di kelas {nama_kelas_terpilih}.")
        conn.close()
        return

    # 6. Form input nilai
    st.subheader(f"Input Nilai: {nama_mapel_terpilih} - Kelas {nama_kelas_terpilih} - Tahap {nama_tahap_terpilih}")
    with st.form("input_nilai_form"):
        nilai_siswa_input = {}
        st.markdown("Masukkan nilai antara 0 sampai 100.")
        for siswa in siswa_kelas:
            # Cek apakah nilai sudah ada untuk siswa, mapel, semester, tahap ini
            cursor.execute("""
                SELECT nilai FROM nilai 
                WHERE siswa_id = ? AND mapel_id = ? AND semester_id = ? AND tahap_id = ?
            """, (siswa['id'], mapel_id, semester_aktif_id, tahap_id))
            existing_nilai_row = cursor.fetchone()
            
            default_nilai = None
            input_disabled = False
            keterangan_nilai = ""

            if existing_nilai_row:
                default_nilai = float(existing_nilai_row['nilai'])
                input_disabled = True # Jika sudah ada, disable input baru, sarankan edit di riwayat
                keterangan_nilai = f"(Nilai sudah ada: {default_nilai})"
            
            col1_nama, col2_input, col3_ket = st.columns([3,1,2])
            with col1_nama:
                st.write(f"{siswa['nama']} (NISN: {siswa['nisn']})")
            with col2_input:
                nilai = st.number_input(
                    "Nilai",
                    min_value=0.0,
                    max_value=100.0,
                    value=default_nilai if default_nilai is not None else 75.0, # Default 75 jika belum ada
                    step=1.0,
                    format="%.1f",
                    key=f"nilai_{siswa['id']}",
                    label_visibility="collapsed",
                    disabled=input_disabled 
                )
                if not input_disabled:
                    nilai_siswa_input[siswa['id']] = nilai
            with col3_ket:
                if keterangan_nilai:
                    st.caption(keterangan_nilai)
        
        catatan_umum = st.text_area("Catatan Umum untuk Penilaian Ini (Opsional)", key="catatan_nilai")
        submitted = st.form_submit_button("Simpan Nilai")
        
        if submitted:
            if not nilai_siswa_input: # Jika semua field nilai disabled karena sudah ada
                st.warning("Semua siswa pada tahap penilaian ini sudah memiliki nilai. Anda dapat mengeditnya melalui tabel riwayat nilai di bawah jika diperlukan.")
            else:
                try:
                    tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")
                    berhasil_disimpan = 0
                    gagal_karena_duplikat = 0

                    for siswa_id, nilai_value in nilai_siswa_input.items():
                        # Double check duplikasi sebelum insert (meskipun sudah ada disable di UI)
                        cursor.execute("""
                            SELECT 1 FROM nilai 
                            WHERE siswa_id = ? AND mapel_id = ? AND semester_id = ? AND tahap_id = ?
                        """, (siswa_id, mapel_id, semester_aktif_id, tahap_id))
                        
                        if cursor.fetchone():
                            gagal_karena_duplikat += 1
                            # Seharusnya tidak terjadi jika UI disable bekerja, tapi sebagai fallback
                            st.warning(f"Nilai untuk siswa ID {siswa_id} sudah ada dan tidak akan disimpan ulang.")
                            continue
                            
                        cursor.execute("""
                            INSERT INTO nilai (siswa_id, mapel_id, semester_id, tahap_id, nilai, tanggal_input, guru_id, catatan) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (siswa_id, mapel_id, semester_aktif_id, tahap_id, nilai_value, tanggal_hari_ini, guru_id, catatan_umum))
                        berhasil_disimpan +=1
                    
                    conn.commit()
                    if berhasil_disimpan > 0:
                        st.success(f"✅ {berhasil_disimpan} data nilai berhasil disimpan!")
                    if gagal_karena_duplikat > 0 and berhasil_disimpan == 0:
                         st.warning("Tidak ada nilai baru yang disimpan karena semua data sudah ada.")
                    st.rerun() # Refresh halaman untuk update tampilan
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    st.error(f"❌ Gagal menyimpan nilai: {str(e)}")

    # 7. Tampilkan riwayat nilai (lebih komprehensif)
    st.divider()
    st.subheader("📋 Riwayat Nilai yang Pernah Diinput")
    
    try:
        query_riwayat = """
            SELECT 
                n.id as nilai_id,
                s.nisn, 
                s.nama as nama_siswa,
                k.tingkat || ' - ' || k.nama_kelas as nama_kelas,
                mp.nama_mapel,
                sem.nama_semester,
                tp.nama_tahap,
                n.nilai, 
                n.tanggal_input,
                n.catatan
            FROM nilai n
            JOIN siswa s ON n.siswa_id = s.id
            JOIN kelas k ON s.kelas_id = k.id
            JOIN mata_pelajaran mp ON n.mapel_id = mp.id
            JOIN semester sem ON n.semester_id = sem.id
            JOIN tahap_penilaian tp ON n.tahap_id = tp.id
            WHERE n.guru_id = ?
        """
        params_riwayat = [guru_id]

        # Filter Riwayat
        st.write("**Filter Riwayat:**")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        # Ambil semua kelas, mapel, semester, tahap untuk filter
        all_kelas_guru = cursor.execute("SELECT DISTINCT k.id, k.tingkat || ' - ' || k.nama_kelas as nama_lk FROM guru_mapel_kelas gmk JOIN kelas k ON gmk.kelas_id = k.id WHERE gmk.user_id = ? ORDER BY nama_lk", (guru_id,)).fetchall()
        all_mapel_guru = cursor.execute("SELECT DISTINCT mp.id, mp.nama_mapel FROM guru_mapel_kelas gmk JOIN mata_pelajaran mp ON gmk.mapel_id = mp.id WHERE gmk.user_id = ? ORDER BY mp.nama_mapel", (guru_id,)).fetchall()
        all_semester = cursor.execute("SELECT id, nama_semester FROM semester ORDER BY nama_semester DESC").fetchall()
        all_tahap = cursor.execute("SELECT id, nama_tahap FROM tahap_penilaian ORDER BY nama_tahap").fetchall()

        with col_f1:
            filter_kelas_id = st.selectbox("Filter Kelas", options=[("", "Semua Kelas")] + [(k['id'], k['nama_lk']) for k in all_kelas_guru], format_func=lambda x:x[1], key="filter_riwayat_kelas")
            if filter_kelas_id and filter_kelas_id[0]:
                query_riwayat += " AND s.kelas_id = ?"
                params_riwayat.append(filter_kelas_id[0])
        with col_f2:
            filter_mapel_id = st.selectbox("Filter Mapel", options=[("", "Semua Mapel")] + [(m['id'], m['nama_mapel']) for m in all_mapel_guru], format_func=lambda x:x[1], key="filter_riwayat_mapel")
            if filter_mapel_id and filter_mapel_id[0]:
                query_riwayat += " AND n.mapel_id = ?"
                params_riwayat.append(filter_mapel_id[0])
        with col_f3:
            filter_semester_id = st.selectbox("Filter Semester", options=[("", "Semua Semester")] + [(s['id'], s['nama_semester']) for s in all_semester], format_func=lambda x:x[1], key="filter_riwayat_semester")
            if filter_semester_id and filter_semester_id[0]:
                query_riwayat += " AND n.semester_id = ?"
                params_riwayat.append(filter_semester_id[0])
        with col_f4:
            filter_tahap_id = st.selectbox("Filter Tahap", options=[("", "Semua Tahap")] + [(t['id'], t['nama_tahap']) for t in all_tahap], format_func=lambda x:x[1], key="filter_riwayat_tahap")
            if filter_tahap_id and filter_tahap_id[0]:
                query_riwayat += " AND n.tahap_id = ?"
                params_riwayat.append(filter_tahap_id[0])

        query_riwayat += " ORDER BY n.tanggal_input DESC, s.nama ASC"
        cursor.execute(query_riwayat, tuple(params_riwayat))
        riwayat = cursor.fetchall()
        
        if riwayat:
            df_riwayat = pd.DataFrame(riwayat, columns=[
                "ID Nilai", "NISN", "Nama Siswa", "Kelas", 
                "Mata Pelajaran", "Semester", "Tahap Penilaian",
                "Nilai", "Tgl Input", "Catatan"
            ])
            
            # Tombol Edit dan Hapus per baris
            # Karena st.dataframe tidak mendukung tombol interaktif per baris secara langsung untuk edit/delete,
            # kita bisa tampilkan ID dan instruksikan untuk edit/hapus melalui form terpisah jika diperlukan,
            # atau loop manual seperti di modul siswa. Untuk rekap, dataframe sudah cukup informatif.
            # Untuk kesederhanaan, kita tampilkan dulu. Fitur edit/hapus nilai bisa ditambahkan kemudian.
            
            st.dataframe(
                df_riwayat,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "ID Nilai": st.column_config.NumberColumn(width="small"),
                    "NISN": st.column_config.TextColumn(width="small"),
                    "Nilai": st.column_config.NumberColumn(format="%.1f", width="small"),
                    "Tgl Input": st.column_config.DateColumn(format="DD-MM-YYYY", width="medium"),
                    "Catatan": st.column_config.TextColumn(width="large")
                }
            )
            st.caption(f"Menampilkan {len(df_riwayat)} data nilai.")
            
            # Fitur Edit/Hapus Nilai (Contoh Sederhana)
            st.subheader("✏️ Edit / Hapus Nilai Tertentu")
            if df_riwayat.empty:
                st.info("Tidak ada data nilai untuk diedit/dihapus pada filter saat ini.")
            else:
                id_nilai_to_action = st.selectbox(
                    "Pilih ID Nilai dari tabel di atas untuk Edit/Hapus",
                    options = [("", "Pilih ID Nilai...")] + [(id_val, f"ID: {id_val}") for id_val in df_riwayat["ID Nilai"].tolist()],
                    format_func=lambda x: x[1],
                    key="id_nilai_action"
                )

                if id_nilai_to_action and id_nilai_to_action[0]:
                    selected_nilai_id = id_nilai_to_action[0]
                    # Ambil detail nilai yang dipilih
                    cursor.execute("SELECT * FROM nilai WHERE id = ?", (selected_nilai_id,))
                    nilai_detail = cursor.fetchone()

                    if nilai_detail:
                        with st.form(key=f"form_action_nilai_{selected_nilai_id}"):
                            st.write(f"Mengubah nilai untuk ID: {selected_nilai_id} (Siswa ID: {nilai_detail['siswa_id']}, Mapel ID: {nilai_detail['mapel_id']})")
                            new_nilai_val = st.number_input("Nilai Baru", min_value=0.0, max_value=100.0, value=float(nilai_detail['nilai']), step=1.0, format="%.1f")
                            new_catatan_val = st.text_area("Catatan Baru (Opsional)", value=nilai_detail['catatan'] if nilai_detail['catatan'] else "")
                            
                            col_edit_btn, col_delete_btn = st.columns(2)
                            with col_edit_btn:
                                submit_edit_nilai = st.form_submit_button("Simpan Perubahan Nilai")
                            with col_delete_btn:
                                submit_delete_nilai = st.form_submit_button("Hapus Nilai Ini", type="secondary")

                            if submit_edit_nilai:
                                try:
                                    cursor.execute("UPDATE nilai SET nilai = ?, catatan = ?, tanggal_input = ? WHERE id = ?",
                                                   (new_nilai_val, new_catatan_val, datetime.now().strftime("%Y-%m-%d"), selected_nilai_id))
                                    conn.commit()
                                    st.success(f"Nilai ID {selected_nilai_id} berhasil diperbarui.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal memperbarui nilai: {e}")
                            
                            if submit_delete_nilai:
                                # Tambah konfirmasi sekali lagi sebelum hapus
                                st.session_state.confirm_delete_single_nilai_id = selected_nilai_id
                                st.rerun()
                                
        else:
            st.info("Belum ada data nilai yang tersimpan yang cocok dengan filter Anda.")

        # Konfirmasi hapus satu nilai
        if st.session_state.get('confirm_delete_single_nilai_id'):
            nilai_id_del = st.session_state.confirm_delete_single_nilai_id
            st.warning(f"Apakah Anda yakin ingin menghapus data nilai dengan ID {nilai_id_del}?")
            btn_confirm_del, btn_cancel_del = st.columns(2)
            with btn_confirm_del:
                if st.button("Ya, Hapus Nilai Ini", type="primary", key=f"confirm_del_nilai_{nilai_id_del}"):
                    try:
                        cursor.execute("DELETE FROM nilai WHERE id = ?", (nilai_id_del,))
                        conn.commit()
                        st.success(f"Nilai ID {nilai_id_del} berhasil dihapus.")
                        del st.session_state.confirm_delete_single_nilai_id
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus nilai: {e}")
                        del st.session_state.confirm_delete_single_nilai_id
            with btn_cancel_del:
                if st.button("Batal", key=f"cancel_del_nilai_{nilai_id_del}"):
                    del st.session_state.confirm_delete_single_nilai_id
                    st.rerun()
            
    except sqlite3.Error as e:
        st.error(f"Gagal memuat riwayat nilai: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Untuk pengujian lokal
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.role = "guru" 
        st.session_state.username = "siti" # Username guru
        st.session_state.user_id = 2      # ID guru siti (sesuai data awal di db.py)
    
    # init_db() # Pastikan tabel ada
    # # Anda mungkin perlu menambahkan data dummy untuk guru_mapel_kelas, mapel_semester_config, tahap_penilaian, dan siswa agar halaman ini berfungsi penuh saat testing.
    # # Pastikan juga ada semester yang aktif.
    
    show_nilai()