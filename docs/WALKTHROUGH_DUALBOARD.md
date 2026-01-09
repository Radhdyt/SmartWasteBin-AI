# Dual Board Mode (Final Architecture)

Arsitektur "Sultan" yang memisahkan tugas Vision dan Control untuk performa maksimal.

### 1. Konsep

- **ESP32-CAM**: Hanya "mata" (Streamer). Tidak mengurus sensor/servo.
- **ESP32 DevKit V1**: Hanya "tangan" (Controller). Mengurus Servo, Ultrasonik, LCD.
- **Laptop**: "Otak" (AI). Mengambil stream -> Proses -> Kirim perintah ke DevKit.

### 2. Persiapan Firmware

#### A. ESP32-CAM (Streamer)

1. Buka `esp32cam/SmartWasteBin_ESP32CAM_StreamOnly.ino`.
2. Partition Scheme: **Huge APP (3MB No OTA)**.
3. Upload & Reset.
4. Cek Serial Monitor. Catat IP (misal `192.168.1.101`).
5. Tes di browser: `http://192.168.1.101:81/stream`. Pastikan video lancar.

#### B. ESP32 DevKit (Controller)

1. Buka `esp32devkit/SmartWasteBin_ESP32DEVKIT_Controller.ino`.
2. Upload (Default Partition Scheme OK).
3. Wiring Wajib:
   - **Servo**: GPIO 13 (Power 5V External!)
   - **Ultrasonik**: Trig 5, Echo 18 (Pakai Divider!)
   - **LCD**: SDA 21, SCL 22
4. Cek Serial Monitor. Catat IP (misal `192.168.1.102`).
5. Tes HTTP: `http://192.168.1.102/status`. Harus balas JSON.

### 3. Jalankan Python

Buka terminal laptop:

```bash
# Format: --source <URL MPJEG> --devkit-ip <IP DEVKIT>
python scripts/run_track_cls_stream_to_devkit.py \
  --source http://192.168.1.101:81/stream \
  --devkit-ip 192.168.1.102
```

_(Tips: Jika malas ketik URL panjang, gunakan `--cam-ip`)_

```bash
python scripts/run_track_cls_stream_to_devkit.py --cam-ip 192.168.1.101 --devkit-ip 192.168.1.102
```

### 4. Troubleshooting Umum

- **Stream Lag**: Sinyal WiFi lemah. Dekatkan keduanya ke router.
- **Servo Reset**: Power supply servo tidak kuat. Gunakan adaptor 2A terpisah.
- **Ultrasonik 0cm**: Cek wiring Echo. Pastikan divider 5V ke 3.3V benar.
- **LCD Blank**: Putar trimpot kontras di belakang LCD.
