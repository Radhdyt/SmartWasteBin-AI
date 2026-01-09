# SINGLE BOARD MODE (ESP32-CAM ONLY)

This mode uses a **single ESP32-CAM** to handle EVERYTHING:

1.  **Video Stream** (MJPEG)
2.  **Hardware Control** (Servo, Ultrasonik, LCD)
3.  **Communication** (Receives labels from laptop)

This simplifies the setup as you don't need a second ESP32 board.

---

## 1. Wiring (IMPORTANT)

Due to limited pins on ESP32-CAM, strict wiring is required.

| Component           | Pin on ESP32-CAM | Note                                            |
| :------------------ | :--------------- | :---------------------------------------------- |
| **Servo SG90**      | **GPIO 13**      | Signal Pin. VCC to 5V (Ext), GND to GND.        |
| **Ultrasonic Trig** | **GPIO 12**      | Output to Sensor Trig.                          |
| **Ultrasonic Echo** | **GPIO 2**       | **CRITICAL**: Use Voltage Divider (5V -> 3.3V). |
| **LCD I2C SDA**     | **GPIO 14**      | Data Line.                                      |
| **LCD I2C SCL**     | **GPIO 15**      | Clock Line.                                     |

**Power Notes:**

- **Servo**: MUST use external 5V power source. Do NOT power from ESP32-CAM 5V pin if possible, or add a capacitor (470uF) to prevent resets.
- **Common Ground**: Connect GND of Ext Power to GND of ESP32-CAM.
- **Voltage Divider**: Echo pin sends 5V, but ESP32 inputs tolerate 3.3V best. Use two resistors (e.g., 1kΩ and 2kΩ) to drop the voltage.

---

## 2. Upload Firmware

1.  Open Arduino IDE.
2.  File -> Open -> `esp32cam/SmartWasteBin_ESP32CAM_StreamPlusController.ino`
3.  Edit **SSID** and **PASSWORD** at the top of the file.
4.  Select Board: **AI Thinker ESP32-CAM**.
5.  Connect ESP32-CAM via FTDI Adapter (IO0 connected to GND).
6.  **Upload**.
7.  Disconnect IO0 from GND and Press Reset.
8.  Open Serial Monitor (115200 baud).
9.  Note the **IP ADDRESS** printed (e.g., `192.168.1.100`).

---

## 3. Testing the Hardware

Open your browser and test these URLs (replace IP):

- **Stream**: `http://192.168.1.100:81/stream` (Should show video)
- **Status**: `http://192.168.1.100/status` (Should show JSON with distance/fill level)
- **Test Servo**: `http://192.168.1.100/label?value=organic` (Servo moves to Organic position)

---

## 4. Running the AI (Laptop)

You have two ways to run the AI.

### Option A: Use ESP32-CAM VIDEO (Wireless)

The laptop grabs video from WiFi and sends commands back via WiFi.

```powershell
python main.py --mode esp32cam --esp32cam-ip 192.168.1.100
```

_Replace `192.168.1.100` with your actual ESP32-CAM IP._

### Option B: Use Laptop WEBCAM (More FPS)

The laptop uses its own webcam for video, but sends commands to ESP32-CAM.

```powershell
python main.py --mode webcam --source 0 --esp32cam-ip 192.168.1.100
```

---

## 6. Laptop Only Mode (Demo / No Hardware)

Use this if you want to test the detection accuracy without connecting any ESP32 hardware.

```powershell
python main.py --mode webcam
```

- **Source**: Laptop Webcam (Default 0).
- **Behavior**: Detection and Classification runs normally.
- **Servo**: **Inactive** (Commands are simulated, status shows `SIM-OK`).
- **Perfect for**: Demonstration or testing the model anywhere.

---

## 7. Troubleshooting

**Servo Jitter / Reset:**

- Problem: Board resets when servo moves.
- Fix: Power supply is weak. Use a dedicated 5V 2A adapter for the servo. Add a capacitor.

**Stream Lag:**

- Problem: Video is choppy.
- Fix: The board is doing dual duty (Stream + Control). We use QVGA resolution to keep it fast. Ensure strong WiFi signal.

**Ultrasonic 0 or 999:**

- Problem: Check wiring. Ensure Echo is on GPIO 2. Try restarting board.

**LCD Not Showing:**

- Fix: Default is `0x27`. If your LCD is different, edit the `.ino` file line `LiquidCrystal_I2C lcd(0x27, 16, 2);` to `0x3F`.

---

## 8. NEW: Improved Detection Mode (Recommended) 🚀

We have added a new script that provides **smoother tracking**, **better bounding boxes**, and **specific object names** (e.g., "Botol", "Hape") while ignoring people.

**Key Features:**

- **Single Object Focus:** Selects 1 main object to avoid clutter.
- **Ignore Person:** Does not detect people.
- **Stable Bounding Box:** Uses smoothing to prevent "jitter".
- **Indonesian Names:** Displays "Botol", "Gelas", etc.

### How to Run:

**1. Webcam Mode (Laptop Only)**

```powershell
python scripts/run_improved_detection.py --mode webcam
```

**2. ESP32-CAM Mode**

```powershell
python scripts/run_improved_detection.py --mode esp32cam --esp32cam-ip 192.168.x.x
```

**Options:**

- `--expand 0.30`: Expand box size by 30% (default).
- `--single-object true`: Only show 1 main object (default).
- `--ignore-person true`: Ignore humans (default).
