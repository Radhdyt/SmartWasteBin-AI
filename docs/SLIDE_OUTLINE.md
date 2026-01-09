# Outline Slide Presentasi (10-12 Slides)

## Slide 1: Judul & Identitas

- **Judul:** Smart Waste Bin System
- **Sub-judul:** Pemilahan Sampah Otomatis Berbasis AI & IoT
- **Visual:** Foto alat + Nama Tim/Anggota.

## Slide 2: Latar Belakang & Masalah

- Sampah tercampur sulit didaur ulang.
- Ketergantungan pada pemilahan manual manusia.
- Solusi dibutuhkan: Sistem yang memilah otomatis di sumber (rumah tangga/kantor).

## Slide 3: Konsep Solusi (The Solution)

- **Visi:** "Tong sampah yang punya mata."
- **Teknologi:** Computer Vision (Melihat) + IoT (Menggerakkan).
- **Output:** Sampah terpisah otomatis ke bin Organik atau Non-Organik.

## Slide 4: Arsitektur Sistem (High Level)

- **Diagram Blok:**
  - [Kamera ESP32] --(Video)--> [Laptop AI Processing]
  - [Laptop] --(Perintah)--> [Mikrokontroler ESP32]
  - [ESP32] --(Sinyal)--> [Servo Motor & LCD]
- **Poin:** Hybrid Processing (Kombinasi PC & Embedded).

## Slide 5: Cara Kerja (Logic Flow)

1.  **Capture:** Kamera mengambil citra user membuang sampah.
2.  **Analyze (AI):** Deteksi objek & klasifikasi (Botol=Non-Org, Apel=Org).
3.  **Verify:** Menunggu konfirmasi kestabilan (2 detik).
4.  **Act:** Menggerakkan servo & update status bin.

## Slide 6: Teknologi AI (Software)

- **Model:** YOLOv8 (State-of-the-art Detection).
- **Fitur Cerdas:**
  - Object Tracking (BoTSORT).
  - Person Filtering (Abaikan manusia).
  - Smoothing Bounding Box (Anti-jitter).

## Slide 7: Implementasi Hardware

- **ESP32-CAM:** Modul murah, sudah ada kamera & WiFi.
- **Servo Motor:** Aktuator pemilah.
- **Ultrasonik:** Sensor kapasitas penuh.
- **LCD:** Antarmuka visual status (IP & Fill Level).

## Slide 8: Demo Flow (Skenario)

- User menunjukkan objek -> Box "Verifying".
- Sistem Konfirmasi -> Box "CONFIRMED".
- Servo bergerak membuka tutup yang sesuai.
- Status tercatat di Log & LCD.

## Slide 9: Hasil Pengujian

- **Akurasi:** Mampu mengenali objek umum (botol, buah, alat makan).
- **Kecepatan:** Respon rata-rata < 3 detik dari deteksi.
- _Tampilkan screenshot overlay deteksi dari laptop._

## Slide 10: Tantangan & Mitigasi

- **Pencahayaan:** Kamera noise di tempat gelap -> Butuh LED flash (sudah ada fitur).
- **Koneksi:** Ketergantungan WiFi -> Implementasi auto-reconnect.
- **Power:** Servo butuh daya besar -> Pakai power supply eksternal.

## Slide 11: Rencana Pengembangan (Future Work)

- Dataset spesifik sampah Indonesia.
- Porting ke Edge Device (Raspberry Pi) agar tanpa Laptop.
- Integrasi ke Cloud Dashboard.

## Slide 12: Kesimpulan

- Sistem berhasil membuktikan konsep pemilahan otomatis.
- Integrasi AI dan IoT berjalan mulus via protokol HTTP.
- Solusi praktis untuk edukasi dan efisiensi sampah.
- **Terima Kasih & QnA.**
