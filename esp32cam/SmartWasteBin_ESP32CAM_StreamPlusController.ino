/*
 * Smart Waste Bin - Multitasking Firmware (ESP32-CAM)
 *
 * FEATURES:
 * 1. MJPEG Stream (Port 81) -> Berjalan di Task Terpisah (Core 0)
 * 2. API Control (Port 80) -> Berjalan di Main Loop (Core 1)
 * 3. Hardware (Servo/LCD/Sonar) -> Berjalan di Main Loop (Core 1)
 *
 * KONSEP MULTITASKING:
 * Agar video tidak patah-patah saat Servo bergerak, dan
 * agar perintah Servo masuk saat Video sedang streaming.
 */

#include "esp_camera.h"
#include "soc/rtc_cntl_reg.h"
#include "soc/soc.h"
#include <ESP32Servo.h>
#include <LiquidCrystal_I2C.h>
#include <WiFi.h>
#include <Wire.h>

// ================= KONFIGURASI WIFI =================
const char *ssid = "AIS";            // GANTI DI SINI JIKA PERLU
const char *password = "qwerty1234"; // GANTI DI SINI JIKA PERLU

// ================= PIN DEFINITIONS =================
#define SERVO_PIN 12
#define TRIG_PIN 13
#define ECHO_PIN 2
#define I2C_SDA 14
#define I2C_SCL 15
#define FLASH_PIN 4 // Built-in Flash LED

// CAMERA PINS (AI THINKER)
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

// ================= GLOBALS =================
Servo myServo;
LiquidCrystal_I2C lcd(0x27, 16, 2);

WiFiServer server(80);       // API Server
WiFiServer streamServer(81); // Video Server

// Shared Variables (Volatile helper for multitasking)
volatile int fill_percent = 0;
volatile bool is_full = false;
volatile float current_dist = 0.0;
String last_label = "none";
bool servo_active = false;
unsigned long servo_timer = 0;

// ================= TASKS HANDLES =================
TaskHandle_t TaskStream;

// ================= HELPER FUNCTIONS =================

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QQVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Cam Init Fail");
  } else {
    Serial.println("Cam Ready");
  }
}

// ================= TASK: STREAMING (Core 0) =================
void streamLoop(void *parameter) {
  while (1) {
    WiFiClient client = streamServer.available();
    if (client) {
      String req = client.readStringUntil('\r');
      if (req.indexOf("GET /stream") != -1) {
        client.println("HTTP/1.1 200 OK");
        client.println(
            "Content-Type: multipart/x-mixed-replace; boundary=frame");
        client.println();

        while (client.connected()) {
          camera_fb_t *fb = esp_camera_fb_get();
          if (!fb) {
            delay(10);
            continue;
          }
          client.println("--frame");
          client.println("Content-Type: image/jpeg");
          client.println("Content-Length: " + String(fb->len));
          client.println();
          client.write(fb->buf, fb->len);
          client.println();
          esp_camera_fb_return(fb);
          delay(1); // Yield to IDLE task
        }
      }
      client.stop();
    }
    delay(10); // Check for clients every 10ms
  }
}

// ================= TASK: MAIN (Core 1 - Default) =================
// Handles API, Sensors, Servo, LCD

void handleAPI() {
  WiFiClient client = server.available();
  if (!client)
    return;

  String req = client.readStringUntil('\r');
  client.flush();

  if (req.indexOf("/label?value=") != -1) {
    String val = "unknown";
    if (req.indexOf("value=organic") != -1)
      val = "organic";
    else if (req.indexOf("value=non") != -1 || req.indexOf("value=anorg") != -1)
      val = "non_org";

    last_label = val;
    Serial.println("CMD: " + val);

    // BYPASS SAFETY CHECK for Debugging
    if (!servo_active) {
      if (val == "organic") {
        // 1. Flash Dulu
        Serial.println("Flash Organic");
        digitalWrite(FLASH_PIN, HIGH);
        delay(1000); // Nyala 1 Detik
        digitalWrite(FLASH_PIN, LOW);
        delay(500); // Jeda

        // 2. Baru Servo
        Serial.println("Gerak Servo Organic");
        // PAKAI RANGE STANDARD (500-2400) BIAR LEBIH AMAN
        myServo.attach(SERVO_PIN, 500, 2400);
        myServo.write(180);

        servo_active = true;
        servo_timer = millis() + 5000;
        client.println("HTTP/1.1 200 OK\r\nConnection: close\r\n\r\nOK-GC");
      } else if (val == "non_org") {
        // 1. Flash Dulu (Kedip)
        Serial.println("Flash Non-Organic");
        digitalWrite(FLASH_PIN, HIGH);
        delay(300);
        digitalWrite(FLASH_PIN, LOW);
        delay(300);
        digitalWrite(FLASH_PIN, HIGH);
        delay(300);
        digitalWrite(FLASH_PIN, LOW);
        delay(500); // Jeda

        // 2. Baru Servo
        Serial.println("Gerak Servo Non-Organic");
        // PAKAI RANGE STANDARD (500-2400)
        myServo.attach(SERVO_PIN, 500, 2400);
        myServo.write(0);

        servo_active = true;
        servo_timer = millis() + 5000;
        client.println("HTTP/1.1 200 OK\r\nConnection: close\r\n\r\nOK-NON");
      }
    } else {
      Serial.println("IGNORE: Servo is BUSY!");
      client.println(
          "HTTP/1.1 429 Too Many Requests\r\nConnection: close\r\n\r\nBUSY");
    }
  } else if (req.indexOf("/status") != -1) {
    String json = "{";
    json += "\"label\":\"" + last_label + "\",";
    json += "\"fill\":" + String(fill_percent) + ",";
    json += "\"full\":" + String(is_full ? "true" : "false");
    json += "}";

    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: application/json");
    client.println("Connection: close");
    client.println();
    client.print(json);
  } else {
    client.println("HTTP/1.1 404 Not Found\r\n\r\n");
  }
  client.stop();
}

float readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long dur = pulseIn(ECHO_PIN, HIGH, 25000);
  if (dur == 0)
    return 999;
  return dur * 0.034 / 2;
}

// ================= SETUP =================
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);

  // Hardware Init
  myServo.setPeriodHertz(50);
  // myServo.attach... DIPINDAH ke handleAPI biar hemat daya saat boot
  // myServo.write(90);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  pinMode(FLASH_PIN, OUTPUT);
  digitalWrite(FLASH_PIN, LOW);

  // TEST FLASH SAAT BOOT <- DIHAPUS BIAR HEMAT DAYA
  // digitalWrite(FLASH_PIN, HIGH);
  // delay(500);
  // digitalWrite(FLASH_PIN, LOW);

  Wire.begin(I2C_SDA, I2C_SCL);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("System Start");

  // Camera & WiFi
  // setupCamera(); // DISABLED for Hybrid Mode

  WiFi.mode(WIFI_STA);               // Set Station Mode explicitly
  WiFi.setTxPower(WIFI_POWER_11dBm); // Reduce WiFi Power to prevent Brownout!

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi OK: " + WiFi.localIP().toString());

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("IP:");
  lcd.print(WiFi.localIP());

  // Start Servers
  server.begin();
  // streamServer.begin(); // DISABLED

  // Create Streaming Task on Core 0
  /*
  xTaskCreatePinnedToCore(streamLoop,   // Function
                          "StreamTask", // Name
                          10000,        // Stack size
                          NULL,         // Params
                          1,            // Priority
                          &TaskStream,  // Handle
                          0             // Core 0
  );
  */
}

// ================= LOOP (Core 1) =================
void loop() {
  // 1. API
  handleAPI();

  // 2. Servo Timer
  if (servo_active && millis() > servo_timer) {
    Serial.println("Servo Reset to Standby");
    myServo.write(90); // Kembali ke Tengah (Standby)
    delay(500);
    // myServo.detach();  <- JANGAN DETACH (Supaya nahan posisi)
    servo_active = false;
  }

  // 3. Sensors (Interval 200ms)
  static unsigned long last_m = 0;
  if (millis() - last_m > 200) {
    last_m = millis();
    float d = readDistance();
    current_dist = d;

    // Calc Fill (5cm=100%, 25cm=0%)
    int f = map((long)d, 25, 5, 0, 100);
    fill_percent = constrain(f, 0, 100);
    is_full = (fill_percent >= 90);
  }

  // 4. LCD (Interval 500ms)
  static unsigned long last_lcd = 0;
  if (millis() - last_lcd > 500) {
    last_lcd = millis();
    lcd.setCursor(0, 1);
    if (is_full)
      lcd.print("FULL!       ");
    else {
      lcd.print("Fill: ");
      lcd.print(fill_percent);
      lcd.print("%   ");
    }
  }

  delay(10); // Yield
}