# Mix Design Beton - Aplikasi Laboratorium Teknik Sipil

## Menjalankan

    python -m venv .venv
    .venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
    python -m pip install -r requirements.txt
    streamlit run app.py              # jalankan dari folder ini agar tema (.streamlit/config.toml) terbaca

Uji otomatis: `python -m pip install -r requirements-dev.txt` lalu `pytest` (folder `tests/`).
Versi pada requirements.txt diuji untuk Python 3.10 - 3.12.

## Login dan izin akses

Aplikasi menampilkan gerbang login; hanya email yang diizinkan **pembuat** yang dapat masuk. Atur whitelist (digabung dari ketiganya):

1. daftar `EMAIL_DIIZINKAN` di `utils/auth.py`;
2. variabel lingkungan `MIXDESIGN_EMAIL_IZIN="a@gmail.com,b@gmail.com"`;
3. berkas `data/email_izin.txt` (satu email per baris).

Percobaan masuk tercatat di `data/log_akses.csv` agar Anda tahu siapa yang meminta izin. Email dibandingkan dalam bentuk baku Gmail
(huruf kecil, titik dan `+tag` diabaikan). Mode (variabel `MIXDESIGN_AUTH_MODE`):

- `email` (bawaan): pengguna mengetik Gmail. **Ini pembatas akses, bukan autentikasi**: aplikasi tidak memeriksa bahwa pengguna memang pemilik email,
  sehingga siapa pun yang tahu email yang diizinkan dapat masuk. Cocok untuk jaringan internal/lab, tidak untuk data sensitif di internet.
- `google`: login Google (OIDC) sehingga email terverifikasi Google. Butuh `pip install "streamlit[auth]>=1.42"` dan `.streamlit/secrets.toml`
  (contoh: `.streamlit/secrets.toml.example`).
- `off`: tanpa login (pengembangan lokal).

Sesi hilang saat halaman dimuat ulang, jadi pengguna masuk lagi. Tombol **Keluar** di sidebar membersihkan seluruh isian sesi.

## Manajemen akses multi-user (permintaan akses dan Panel Admin)

Alur: pengguna yang ditolak menekan **Kirim Permintaan Akses** -> tercatat di `data/pending_requests.json` -> admin membuka **Panel Admin**
(menu sidebar, hanya tampil untuk admin) -> **Setujui** memindahkan email ke `data/approved_emails.json` dan otomatis masuk whitelist
(atau **Tolak**; email yang sudah disetujui dapat **Dicabut**; admin juga bisa menambah email langsung).

Langkah pengaturan admin:

1. Isi email admin: `EMAIL_ADMIN` di `utils/auth.py` atau `MIXDESIGN_EMAIL_ADMIN="admin@gmail.com"`. Admin selalu diizinkan masuk.
2. Mode `email`: wajib atur sandi admin, mis. `MIXDESIGN_ADMIN_PASSWORD="sandi-panjang"` (atau hash SHA-256 heksadesimal di
   `MIXDESIGN_ADMIN_PASSWORD_SHA256`). Tanpa sandi, Panel Admin dinonaktifkan. Alasannya: mode `email` tidak membuktikan pemilik email,
   jadi tanpa sandi siapa pun yang mengetik email admin dapat menyetujui dirinya sendiri. Mode `google`: tanpa sandi (email terverifikasi Google).
3. Jalankan aplikasi, masuk dengan email admin, buka **Panel Admin** (masukkan sandi pada mode email).
4. Pengguna baru: masuk dengan Gmail -> ditolak -> **Kirim Permintaan Akses** (opsional isi nama/instansi). Admin menyetujui; pengguna masuk lagi.

Catatan: data akses berupa berkas di `data/` (tidak ikut git). Pada hosting dengan disk sementara (mis. Streamlit Community Cloud) berkas hilang
saat aplikasi dimulai ulang; pakai volume persisten atau simpan whitelist tetap di `MIXDESIGN_EMAIL_IZIN`. Penguncian berkas hanya berlaku dalam satu proses.

## Scroll halaman

`ui/theme.py` memuat CSS agar kontainer utama selalu dapat digulir, serta skrip kecil yang melepas fokus input angka saat roda mouse
digulir (roda pada input angka yang fokus mengubah nilainya dan menahan gulir halaman). Skrip dimuat lewat komponen HTML tak terlihat.

## Menu

- **Pekerjaan Beton**: parameter dasar, Mix Design (SNI konvensional / ACI 211.1 + admixture), bandingkan SNI vs ACI,
  input lab agregat halus & kasar (analisa saringan, uji cuci No. 200), grafik, prediksi umur dini, trial mix,
  troubleshooter slump, penerimaan kuat tekan 28 hari, laporan & Sertifikat Mutu (PDF, Word, HTML putih siap cetak).
- **Inventory Stock**: barang masuk/keluar (CSV lokal, SQLite, atau Supabase).
- **Cost Estimation**: biaya material per m3 dan per volume pekerjaan.
- Sidebar: kop surat, **simpan/muat proyek (JSON)** yang memulihkan semua isian.

## Tiga koreksi terhadap Excel referensi (APLIKOM_BETON.xlsx)

1. **Bobot Wh/Wk SNI terbalik.** Sheet MIX DESIGN SNI menandai kerikil = alami dan pasir = batu pecah, tetapi rumus kadar air bebas
   `=((2/3)*175)+((1/3)*205)` (= 185 kg/m3) memberi bobot 2/3 pada nilai batu *alami* (175). SNI 03-2834-2000: W = 2/3 Wh + 1/3 Wk, dengan
   Wh = air untuk agregat **halus** dan Wk untuk agregat **kasar**. Dengan label Excel sendiri hasil yang benar 2/3 x 205 + 1/3 x 175 = 195 kg/m3.
   Aplikasi memakai rumus SNI dan jenis agregat dipilih per agregat (pasir alami + kerikil batu pecah menghasilkan 185 kg/m3).
2. **f'cr vs f'c pada ACI.** Sheet MIX DESIGN ACI membaca FAS dari f'c (24 MPa) langsung. ACI 211.1 memakai kuat tekan rata-rata target f'cr
   (f'c + nilai tambah); tanpa nilai tambah beton berisiko tidak mencapai f'c. Aplikasi memakai f'cr = f'c + k.s (k = 1,64) atau tabel
   ACI 318 bila deviasi standar tidak diketahui.
3. **Berat jenis kerikil untuk volume agregat kasar.** Pada metode volume absolut sheet ACI membagi massa kerikil dengan berat jenis *pasir*
   (2,58) padahal seharusnya berat jenis kerikil (2,35); akibatnya pasir terlalu besar (sekitar 822 kg/m3 dibanding 719 kg/m3 pada data contoh).
   Aplikasi memakai berat jenis kerikil dan memberi peringatan bila metode massa dan volume berselisih lebih dari 5%.

Temuan lain yang dikoreksi menurut ACI 211.1 (verifikasi dengan buku standar): salah ketik pada tabel air ACI (208 dan 288 seharusnya 228), kolom massa beton ACI beton ber-udara, serta
nilai tambah ACI 318.

## Grafik SNI (Grafik 1, 14, 15, 16)

`standards/sni_grafik.py` berisi tabel interpolasi hasil digitalisasi gambar grafik pada sheet 'GRAFIK DAN TABEL FAS' (dibaca per piksel,
dikalibrasi pada garis grid). Ketelitian +-0,5 MPa (Grafik 1), +-0,3 poin persen (Grafik 14/15), +-3 kg/m3 (Grafik 16). Keterbatasan:
Grafik 13 (10 mm) tidak ada pada file sehingga ukuran 10 mm memakai estimasi berlabel; gambar Grafik 14 tidak berjudul pada file dan
dipetakan ke 20 mm berdasarkan urutan nilai terhadap Grafik 15 (40 mm); persen pasir diambil di titik tengah pita zona (batas bawah-atas
ditampilkan); berat isi beton Grafik 16 mengasumsikan agregat batu pecah. Verifikasi terhadap grafik cetak sebelum dipakai untuk dokumen resmi.

## Penyimpanan stok

Bawaan: CSV di `data/`. Pilihan lewat variabel lingkungan:

    MIXDESIGN_STOK_BACKEND=sqlite   MIXDESIGN_STOK_DB=/path/stok.db
    MIXDESIGN_STOK_BACKEND=supabase SUPABASE_URL=https://xxxx.supabase.co  SUPABASE_KEY=...   # skema SQL ada di utils/inventory.py

Google Sheets belum diimplementasikan.

## Struktur

app.py | .streamlit/config.toml | ui/ (navigasi, tema, inputs, header, proyek_ui, halaman_beton, tab_*) |
standards/ (sni, sni_grafik, aci, admixture, base) | utils/ (material_db, sieve, checks, prediksi, trialmix, penerimaan,
gradasi_gabungan, slump_assistant, inventory, biaya, dokumen, laporan_pdf, laporan_docx, laporan_html, proyek, format_id, charts) | tests/
