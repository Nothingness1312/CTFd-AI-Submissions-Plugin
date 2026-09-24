# Plugin AI Submissions (AI Link)

Plugin self-contained untuk **CTFd** yang menambahkan kolom **"AI Link" (wajib diisi)** pada setiap pengiriman flag challenge.

Dirancang untuk memenuhi aturan kompetisi: peserta wajib menyertakan **URL AI yang digunakan** (mis. ChatGPT, dsb.) saat mengerjakan atau menyelesaikan sebuah challenge. Kolom ini langsung terekam ke database dan dikaitkan ke submission, sehingga panitia bisa mengaudit "challenge ini FA diselesaikan pakai AI apa".

> **Catatan penting:** Plugin ini 100% self-contained. Ia **tidak mengubah** file inti CTFd maupun file theme manapun. Semua injeksi dilakukan dari folder plugin sendiri (`/plugins/ai_submissions`). Aman dipasang di event yang sedang berjalan tanpa perlu takut merusak data.

- [English](README.md)

---

## Fitur

- **Backend (theme-agnostic, bekerja di semua theme CTFd):**
  - Menyimpan kolom `ai_link` di tabel `ai_links` pada database, berkaitan dengan setiap submission (solve, fail, partial, rate-limited).
  - Validasi server-side: submission **tanpa** `ai_link` **diblokir** (HTTP 400), jadi memaksa peserta mengisi URL AI sekalipun mereka membypass frontend.
  - Berfungsi pada mode **user** maupun **teams** (otomatis mendeteksi lewat `user_mode` CTFd).
  - Untuk **dynamic challenges**: nilai poin dihitung termasuk penyertaan AI Link (menghindari solusi "chat asal" yang dianggap menang).
  - Kolom **"AI Link"** ditampilkan langsung di halaman **Admin → Submissions** (`/admin/submissions`), ter-merge bersamaan dengan view **All Submissions / Correct / Incorrect**, tanpa menu terpisah. Data diambil via endpoint JSON plugin `/admin/ai-submissions/links?submission_ids=...` (admin only).
  - Halaman review penuh `/admin/ai-submissions` tetap tersedia (admin only). Dapat diakses via URL langsung (tanpa menu di header).
  - Challenge **preview** (admin) dikecualikan dari validasi, sehingga peninjauan challenge oleh admin tidak perlu AI Link.

- **Frontend (tampilan field):**
  - Field **"AI Link\*"** di-inject ke dalam modal challenge via JavaScript plugin (self-contained, ada di folder plugin ini).

---

## Isi Folder (struktur)

```
ai_submissions/
├── __init__.py                     # Logika plugin (registrasi, backend, admin bp)
├── assets/
│   ├── ai_submissions.js           # JS frontend: inject field AI Link ke modal
│   └── ai_submissions_admin.js     # JS admin: inject kolom AI Link di /admin/submissions
└── templates/
    └── ai_submissions.html         # Halaman review admin /admin/ai-submissions
```

---

## Persyaratan

- Docker + docker-compose yang menjalankan **CTFd** (ctfd:latest).

---

## Cara Pasang (Install)

1. **Letakkan folder plugin** ke dalam container CTFd pada jalur plugin CTFd. Bila kamu pakai docker-compose (misal project `ctfd`):

   ```
   # dari host, salin folder ke working dir yang di-mount ke container
   cp -r ai_submissions /path/project/CTFd/CTFd/plugins/
   ```

   atau salin langsung ke container (kalau tidak ada volume mount):

   ```
   docker cp ai_submissions ctfd-ctfd-1:/opt/CTFd/CTFd/plugins/
   ```

   Ganti `ctfd-ctfd-1` dengan nama container CTFd-mu (cek via `docker ps`).

2. **Restart CTFd** agar plugin di-load:

   ```
   docker-compose restart ctfd
   # atau
   docker restart <nama-container-ctfd>
   ```

3. **Verifikasi terpasang.** Buka halaman login/challenge dengan browser.
   - Backend valid di semua theme.
   - Field frontend terverifikasi bekerja penuh di theme `pixo`. Lihat bagian [Theme yang Didukung](#theme-yang-didukung) untuk detail.

4. **Cek tabel database (sekali saja).** Plugin membuat tabel `ai_links` secara otomatis saat pertama kali dimuat. Tidak ada migrasi manual yang diperlukan.

---

## Cara Pakai

1. Masuk sebagai user/team peserta (tidak harus admin).
2. Buka halaman **Challenges**.
3. Klik challenge yang dikerjakan.
4. **Isi AI Link** (URL beralamat http/https dari AI yang dipakai) lalu isi flag.
5. Submit. Tanpa AI Link, submit **ditolak** (frontend menampilkan alert & backend menolak).

---

## Theme yang Didukung

| Theme | Status |
|---|---|
| `pixo` | **Didukung penuh** |
| `core-deprecated` | **Didukung penuh** |

Untuk theme lain: validasi backend berlaku universal. Menampilkan field frontend cukup menyesuaikan satu file JS plugin (tetap tanpa menyentuh theme inti).

---

## Cara Cek Status / Debug

- Cek log container:

  ```
  docker logs ctfd-ctfd-1 --tail 100
  ```

- Cek dari dalam container apakah plugin ter-load:

  ```
  docker exec ctfd-ctfd-1 python -c "from CTFd import create_app; app=create_app(); print('plugins:', [p for p in app.plugins])"
  ```

- Cek database (tabel `ai_links`):

  ```
  docker exec ctfd-db-1 mariadb -uctfd -pctfd ctfd -e "SELECT * FROM ai_links;"
  ```

---

## Uninstall

1. Hapus tabel tambahan plugin dari DB (opsional, bisa diabaikan karena hanya berisi data AI Link):

   ```
   docker exec ctfd-db-1 mariadb -uctfd -pctfd ctfd -e "DROP TABLE IF EXISTS ai_links;"
   ```

2. Hapus folder plugin:

   ```
   docker exec ctfd-ctfd-1 rm -rf /opt/CTFd/CTFd/plugins/ai_submissions
   ```

3. Restart CTFd:

   ```
   docker-compose restart ctfd
   ```

4. (Opsional) Jika pernah men-set `CTFd` class override, plugin hanya berlaku selama folder plugin ada. Penghapusan folder + restart sudah mengembalikan perilaku asli.

---

## Lisensi

Open source di bawah lisensi **MIT**. Silakan pakai, modifikasi, dan distribusikan kembali. File lisensi lengkap: [LICENSE](LICENSE).
