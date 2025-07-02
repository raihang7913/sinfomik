import sqlite3

DB_PATH = "sinfomik.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        # Tabel Siswa: Ditambahkan kelas_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS siswa (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                nisn INTEGER NOT NULL UNIQUE,
                nama TEXT NOT NULL,
                kelas_id INTEGER,
                FOREIGN KEY (kelas_id) REFERENCES kelas(id) ON DELETE SET NULL
            );
        ''')

        # Tabel Tahun Ajaran: Tetap
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tahun_ajaran (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                th_ajar TEXT NOT NULL UNIQUE
            );
        ''')

        # Tabel Semester Pilihan (Ganjil/Genap): Tetap
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semester_pil (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                sm_pil TEXT NOT NULL UNIQUE
            );
        ''')
        # Pastikan ada data awal untuk semester_pil jika belum ada
        cursor.execute("SELECT COUNT(*) FROM semester_pil")
        if cursor.fetchone()[0] == 0:
            semester_pilihan_data = [('Ganjil',), ('Genap',)]
            cursor.executemany("INSERT INTO semester_pil (sm_pil) VALUES (?)", semester_pilihan_data)


        # Tabel Semester: Tetap, mungkin perlu penyesuaian data awal jika ada
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semester (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                th_ajar_id INTEGER NOT NULL,
                sm_pil_id INTEGER NOT NULL,
                aktif BOOLEAN DEFAULT 0, -- Menandakan semester aktif secara global
                nama_semester TEXT NOT NULL, -- Misal: "Ganjil 2023/2024"
                FOREIGN KEY (th_ajar_id) REFERENCES tahun_ajaran(id),
                FOREIGN KEY (sm_pil_id) REFERENCES semester_pil(id),
                UNIQUE (th_ajar_id, sm_pil_id)
            );
        ''')

        # Tabel User (Guru, Admin): Tetap
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE, 
                password TEXT NOT NULL, 
                role TEXT NOT NULL DEFAULT 'admin' CHECK(role IN ('admin', 'guru'))
            );
        ''')
        cursor.execute("SELECT COUNT(*) FROM user")
        if cursor.fetchone()[0] == 0:
            users = [
                ('admin', 'admin', 'admin'),
                ('siti', 'siti123', 'guru')
            ]
            cursor.executemany("INSERT INTO user (username, password, role) VALUES (?, ?, ?)", users)
        
        # Tabel Kelas: Tetap
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kelas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_kelas TEXT NOT NULL,
                tingkat TEXT NOT NULL, -- Misal: 10, 11, 12
                UNIQUE (nama_kelas, tingkat)
            );
        ''')
        cursor.execute("SELECT COUNT(*) FROM kelas")
        if cursor.fetchone()[0] == 0:
            kelas_awal = [
                ('A', '10'),
                ('B', '10'),
                ('C', '10'),
                ('A', '11'),
                ('B', '11')
            ]
            cursor.executemany("INSERT INTO kelas (nama_kelas, tingkat) VALUES (?, ?)", kelas_awal)

        # Tabel Mata Pelajaran: Tetap
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mata_pelajaran (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_mapel TEXT NOT NULL,
                kode_mapel TEXT UNIQUE
            );
        ''')
        cursor.execute("SELECT COUNT(*) FROM mata_pelajaran")
        if cursor.fetchone()[0] == 0:
            mapel_awal = [
                ('Matematika Wajib', 'MTK-WAJIB-X'),
                ('Bahasa Indonesia', 'BINDO-X'),
                ('Fisika', 'FIS-X'),
                ('Kimia', 'KIM-X')
            ]
            cursor.executemany("INSERT INTO mata_pelajaran (nama_mapel, kode_mapel) VALUES (?, ?)", mapel_awal)

        # Tabel Relasi Guru - Mata Pelajaran - Kelas: Tetap
        # Ini mendefinisikan guru siapa mengajar mapel apa di kelas mana
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guru_mapel_kelas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, -- id dari tabel user (guru)
                mapel_id INTEGER NOT NULL,
                kelas_id INTEGER NOT NULL,
                semester_id INTEGER NOT NULL, -- Ditambahkan untuk konteks semester pengajaran
                FOREIGN KEY (user_id) REFERENCES user(id),
                FOREIGN KEY (mapel_id) REFERENCES mata_pelajaran(id),
                FOREIGN KEY (kelas_id) REFERENCES kelas(id),
                FOREIGN KEY (semester_id) REFERENCES semester(id),
                UNIQUE(user_id, mapel_id, kelas_id, semester_id)
            );
        ''')
        # Contoh data awal, pastikan ID merujuk ke data yang valid setelah perubahan
        # cursor.execute("SELECT COUNT(*) FROM guru_mapel_kelas")
        # if cursor.fetchone()[0] == 0:
        #     # Asumsi user_id 2 adalah guru, mapel_id 1, kelas_id 1, semester_id 1 ada
        #     relasi_awal = [
        #         (2, 1, 1, 1) 
        #     ]
        #     cursor.executemany("INSERT INTO guru_mapel_kelas (user_id, mapel_id, kelas_id, semester_id) VALUES (?, ?, ?, ?)", relasi_awal)

        # Tabel Tahap (BARU)
        # Misalnya: UTS, UAS, Tugas Harian, Praktikum Mingguan, dll.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tahap_penilaian (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_tahap TEXT NOT NULL UNIQUE,
                deskripsi TEXT
            );
        ''')
        cursor.execute("SELECT COUNT(*) FROM tahap_penilaian")
        if cursor.fetchone()[0] == 0:
            tahap_awal = [
                ('UTS', 'Ujian Tengah Semester'),
                ('UAS', 'Ujian Akhir Semester'),
                ('Tugas Harian', 'Kumpulan tugas harian'),
                ('Praktikum', 'Kegiatan praktikum')
            ]
            cursor.executemany("INSERT INTO tahap_penilaian (nama_tahap, deskripsi) VALUES (?, ?)", tahap_awal)


        # Tabel Konfigurasi Mata Pelajaran per Semester dan Tahap (BARU)
        # Menentukan apakah suatu mapel aktif/tidak pada semester dan tahap tertentu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mapel_semester_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mapel_id INTEGER NOT NULL,
                semester_id INTEGER NOT NULL,
                -- tahap_id INTEGER, -- Bisa ditambahkan jika aktivasi mapel juga bergantung pada tahap tertentu
                is_active BOOLEAN NOT NULL DEFAULT 0, -- 0 = tidak aktif, 1 = aktif
                FOREIGN KEY (mapel_id) REFERENCES mata_pelajaran(id),
                FOREIGN KEY (semester_id) REFERENCES semester(id),
                -- FOREIGN KEY (tahap_id) REFERENCES tahap_penilaian(id), 
                UNIQUE (mapel_id, semester_id) -- Jika tahap_id ditambahkan, sertakan di UNIQUE
            );
        ''')
        
        # Tabel Nilai: Dimodifikasi untuk menyertakan semester_id dan tahap_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nilai (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siswa_id INTEGER NOT NULL,
                mapel_id INTEGER NOT NULL,
                semester_id INTEGER NOT NULL, 
                tahap_id INTEGER NOT NULL, -- Merujuk ke tahap_penilaian (UTS, UAS, dll)
                nilai REAL NOT NULL,
                tanggal_input DATE NOT NULL,
                guru_id INTEGER NOT NULL, -- id dari tabel user (guru yang menginput)
                catatan TEXT, -- Opsional, catatan dari guru
                FOREIGN KEY (siswa_id) REFERENCES siswa(id) ON DELETE CASCADE,
                FOREIGN KEY (mapel_id) REFERENCES mata_pelajaran(id),
                FOREIGN KEY (semester_id) REFERENCES semester(id),
                FOREIGN KEY (tahap_id) REFERENCES tahap_penilaian(id),
                FOREIGN KEY (guru_id) REFERENCES user(id),
                CHECK (nilai >= 0 AND nilai <= 100),
                UNIQUE(siswa_id, mapel_id, semester_id, tahap_id) -- Mencegah duplikasi nilai untuk kombinasi yang sama
            );
        ''')
        conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully with new schema.")
    # Anda bisa menambahkan query SELECT di sini untuk memeriksa struktur atau data awal
    # conn = get_connection()
    # print("\nSiswa:")
    # for row in conn.execute("SELECT * FROM siswa LIMIT 5"):
    #     print(dict(row))
    # print("\nKelas:")
    # for row in conn.execute("SELECT * FROM kelas LIMIT 5"):
    #     print(dict(row))
    # print("\nSemester:")
    # for row in conn.execute("SELECT * FROM semester LIMIT 5"):
    #     print(dict(row))
    # print("\nTahap Penilaian:")
    # for row in conn.execute("SELECT * FROM tahap_penilaian LIMIT 5"):
    #     print(dict(row))
    # conn.close()

