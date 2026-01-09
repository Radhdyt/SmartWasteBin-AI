# Catatan Presentasi: Smart Waste Bin System

## A. Judul & Elevator Pitch

**Judul:** Smart Waste Bin: Sistem Pemilahan Sampah Otomatis Berbasis Computer Vision dan IoT.
**Pitch:** "Sebuah tong sampah cerdas yang 'melihat' jenis sampah Anda menggunakan AI, lalu memilahnya secara otomatis menjadi Organik atau Non-Organik dalam hitungan detik."

## B. Latar Belakang Masalah

1.  **Kesadaran Rendah:** Masyarakat sering malas atau bingung membedakan sampah organik dan anorganik.
2.  **Efisiensi Pengolahan:** Sampah yang tercampur sulit didaur ulang dan meningkatkan beban TPA.
3.  **Kebutuhan Otomatisasi:** Diperlukan sistem yang bisa memilah di sumbernya (hulu) tanpa intervensi manusia yang rumit.

## C. Tujuan & Scope Sistem

- **Tujuan:** Membuat prototipe tong sampah yang dapat mengidentifikasi objek sampah umum dan mengarahkannya ke wadah yang benar.
- **Scope:**
  - Klasifikasi 2 Kategori: Organik (Sisa makanan, buah) vs Non-Organik (Plastik, kaleng, elektronik).
  - Integrasi Computer Vision (Laptop) dengan Mikrokontroler (ESP32-CAM).
  - Mekanisme pemilahan fisik menggunakan Servo Motor.

## D. Arsitektur Sistem

Sistem menggunakan arsitektur **Hybrid Processing**:

1.  **Mata & Tangan (ESP32-CAM):**
    - **Kamera:** Mengambil video (streaming MJPEG) dan mengirimnya ke Laptop via WiFi.
    - **Kontroller:** Menerima perintah dari Laptop untuk menggerakkan Servo (pemilah) dan update LCD.
    - **Sensor:** Membaca sensor Ultrasonik untuk cek kepenuhan tong.
2.  **Otak (Laptop/PC):**
    - **Processing:** Menerima stream video, menjalankan algoritma AI (YOLOv8).
    - **Logic:** Menentukan jenis sampah dan mengirim perintah HTTP ke ESP32.

## E. Pipeline AI (Artificial Intelligence)

Proses pengolahan di `main.py`:

1.  **Deteksi (Detection):** Menggunakan **YOLOv8 Nano** (Model ringan & cepat).
    - _Smart Remapping:_ Memanfaatkan kelas COCO standar (botol, pisang, apel, keyboard) yang dipetakan ke kategori sampah.
2.  **Tracking:** Menggunakan algoritma **BoTSORT/ByteTrack** untuk melacak ID objek agar tidak terdeteksi ganda (flickering).
3.  **Filtrasi & Stabilisasi:**
    - **Single Object Focus:** Memilih objek terbesar di frame.
    - **Ignore Person:** Mengabaikan manusia agar fokus pada sampah yang dipegang.
    - **Verifikasi:** Sistem menunggu "CONFIRMED" (objek stabil selama ±2 detik) sebelum mengirim perintah, mencegah kesalahan deteksi sesaat.

## F. API & Komunikasi (Laptop <-> ESP32)

Komunikasi berjalan via WiFi (HTTP REST Protocol):

1.  **Laptop -> ESP32 (Kontrol):**
    - `GET /label?value=organic` -> Menggerakkan servo ke kiri (Organik).
    - `GET /label?value=non_org` -> Menggerakkan servo ke kanan (Non-Organik).
2.  **ESP32 -> Laptop (Video Stream):**
    - `GET :81/stream` -> Stream video MJPEG (Low latency).
3.  **Status & Monitoring:**
    - `GET /status` -> Mengembalikan JSON berisi level sampah dan status sensor.
    - _Format:_ `{"label": "...", "fill": 20, "full": false}`

## G. Demo Skenario (Step-by-Step)

1.  **Persiapan Hardware:**
    - Nyalakan alat. LCD menampilkan IP Address (misal: `192.168.1.100`).
    - Pastikan Laptop & ESP32 di jaringan WiFi yang sama.
2.  **Jalankan Aplikasi:**
    - Buka terminal: `python main.py --mode esp32cam --esp32cam-ip 192.168.1.100`
    - Jendela kamera muncul di layar laptop.
3.  **Proses Deteksi:**
    - Arahkan sampah (misal: Pisang) ke kamera.
    - Box deteksi muncul dengan label "Pisang (Organic)". Status: "VERIFYING" (Kuning).
4.  **Eksekusi Pemilahan:**
    - Tahan posisi. Status berubah jadi "CONFIRMED" (Hijau).
    - Laptop mengirim perintah ke ESP32.
    - **Aksi:** Servo bergerak membuka pintu Organik, LCD menampilkan status, LED Flash berkedip (opsional).
5.  **Monitoring Level (Tambahan):**
    - Tunjukkan di LCD persentase kapasitas tong (via Ultrasonik).

## H. Hasil yang Ditunjukkan

- **Visual:** Overlay bounding box yang smooth (tidak bergetar) dengan nama objek Bahasa Indonesia (Botol, Gelas, dll).
- **Respon Fisik:** Servo bergerak akurat sesuai kategori.
- **Data:** Log deteksi tersimpan otomatis di `logs/history.csv` untuk laporan.

## I. Keterbatasan & Risiko

1.  **Ketergantungan WiFi:** Jika sinyal putus, video lag atau perintah servo gagal (ada fitur _reconnect_ di kode).
2.  **Cahaya:** Kualitas kamera ESP32-CAM sensitif terhadap cahaya minim (noise tinggi).
3.  **Daya Servo:** Servo membutuhkan arus tinggi; jika power supply tidak stabil, ESP32 bisa restart sendiri (Brownout).
4.  **Dataset:** Menggunakan model umum (COCO), mungkin salah mengenali sampah penyok atau kotor yang bentuknya absurd.

## J. Rencana Pengembangan

1.  **Custom Dataset Training:** Melatih model khusus sampah lokal Indonesia (kemasan indomie, kotak susu, dll) untuk presisi lebih tinggi.
2.  **Edge Computing:** Memindahkan proses AI langsung ke mikrokontroler yang lebih kuat (Raspberry Pi / Jetson) agar tidak butuh laptop.
3.  **IoT Dashboard:** Menampilkan grafik statistik sampah harian di web/aplikasi HP.

## 4. Analisis & Kesimpulan Model

### A. Hasil Training (Proof of Concept)

- **Model:** Custom CNN based on YOLOv8-Cls
- **Dataset:** Kaggle Waste Classification (Organic vs Recyclable)
- **Akurasi:** Mencapai **95.75%** pada data validasi.
- **Kesimpulan Awal:** Secara teori, model mampu membedakan sampah dengan sangat baik jika background bersih.

### B. Implementasi Real-World (Production)

Untuk demo yang lebih _robust_ (tahan banting) terhadap gangguan background ruangan kelas/kantor, kita menggunakan strategi **Hybrid Logic**:

1.  **Deteksi:** Menggunakan **YOLOv8 Nano (COCO)** yang sudah sangat matang mengenali objek sehari-hari (botol, gelas, hape, pisang).
2.  **Klasifikasi Pintar:** Kita memetakan objek tersebut ke kategori sampah:
    - _Organic:_ Pisang, Apel, Jeruk, Donat.
    - _Non-Organic:_ Botol, Gelas, Kaleng, Hape (Elektronik).
3.  **Hasil:** Sistem jauh lebih stabil dan tidak mudah salah deteksi dibanding model custom kecil.

### C. Kesimpulan Akhir

Sistem berhasil menggabungkan kecerdasan Computer Vision modern dengan mikrokontroler murah (ESP32) untuk menciptakan pemilah sampah otomatis yang **Real-time**, **Akurat**, dan **Respon Cepat (Low Latency)**.

## K. 5-8 Poin Talk Track (Kunci Bicara)

1.  "Sistem ini menggabungkan kecepatan AI modern dengan biaya hardware yang rendah."
2.  "Kami tidak hanya mendeteksi, tapi men-tracking objek untuk memastikan keputusan stabil (anti-error)."
3.  "Arsitekturnya terpisah: Laptop berpikir berat, ESP32 bekerja fisik. Ini optimal untuk prototipe."
4.  "Komunikasi menggunakan protokol HTTP standar, memudahkan debugging dan pengembangan."
5.  "Fitur 'Ignore Person' memastikan sistem tidak salah mengenali tangan user sebagai sampah."
6.  "Sistem ini siap demo, dengan feedback loop lengkap: Visual (Layar), Fisik (Servo), dan Data (LCD/Logs)."
7.  "Kode kami modular, mudah diganti model deteksinya tanpa merombak hardware."
