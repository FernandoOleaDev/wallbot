/*
 * WallBot ESP32-S3 Display (Freenove FNK0104)
 * Muestra productos de Wallapop en pantalla ILI9341 240x320
 *
 * Hardware: Freenove ESP32-S3 Display 2.8" (ES3C28P/ES3N28P)
 * - Display: ILI9341V 240x320 IPS
 * - ESP32-S3 con 8MB PSRAM
 *
 * Pines del display (integrados en la placa):
 *   GPIO10  ->  TFT_CS   (Chip Select)
 *   GPIO46  ->  TFT_DC   (Data/Command)
 *   GPIO12  ->  TFT_SCLK (Clock)
 *   GPIO11  ->  TFT_MOSI (Data)
 *   GPIO45  ->  TFT_BL   (Backlight)
 *   CHIP_PU ->  TFT_RST  (Reset compartido)
 *   GPIO42  ->  RGB LED
 *
 * Librerias necesarias:
 *   - TFT_eSPI (v2.5.43) con configuracion Freenove
 *   - TJpg_Decoder (v1.1.0)
 *
 * IMPORTANTE: Instalar las librerias desde:
 *   docs/Freenove_ESP32_S3_Display-main/Libraries/
 *   - TFT_eSPI_v2.5.43.zip
 *   - TFT_eSPI_Setups_v1.2.zip
 *   - TJpg_Decoder_v1.1.0.zip
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>
#include <TJpg_Decoder.h>

// ============================================
// CONFIGURACION - MODIFICAR SEGUN TU RED
// ============================================

const char* WIFI_SSID = "MOVISTAR_F0F9";
const char* WIFI_PASSWORD = "orQ5ygyjkhYUnUcdnM5x";

const char* SERVER_HOST = "192.168.1.124";
const int SERVER_PORT = 9500;

// Intervalo de polling en milisegundos (30 segundos)
const unsigned long POLL_INTERVAL_MS = 30000;

// ============================================
// PINES FREENOVE ESP32-S3 DISPLAY
// ============================================

#define TFT_BL     45   // Backlight control
#define RGB_LED    42   // RGB LED (WS2812)

// Resolucion del display
#define SCREEN_WIDTH  240
#define SCREEN_HEIGHT 320

// ============================================
// OBJETOS GLOBALES
// ============================================

TFT_eSPI tft = TFT_eSPI();

unsigned long lastPollTime = 0;
bool backlightOn = true;

// Buffer para imagen JPEG (ESP32-S3 tiene mas memoria)
#define JPEG_BUFFER_SIZE 50000
uint8_t* jpegBuffer = nullptr;
size_t jpegSize = 0;

// ============================================
// COLORES PERSONALIZADOS (RGB565)
// ============================================

#define COLOR_BG        0x1A1E  // Azul oscuro (26, 26, 46)
#define COLOR_PRICE     0x0F17  // Teal/Cyan (19, 193, 172)
#define COLOR_SECONDARY 0x9CD3  // Gris (150, 150, 150)

// ============================================
// FUNCIONES DE BACKLIGHT
// ============================================

void setupBacklight() {
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);  // Encender backlight
  backlightOn = true;
}

void setBacklight(bool on) {
  digitalWrite(TFT_BL, on ? HIGH : LOW);
  backlightOn = on;
}

// ============================================
// FUNCIONES DE PANTALLA
// ============================================

void showMessage(const char* line1, const char* line2 = "", uint16_t bgColor = TFT_BLACK, uint16_t textColor = TFT_WHITE) {
  tft.fillScreen(bgColor);
  tft.setTextColor(textColor);
  tft.setTextSize(2);

  int y = SCREEN_HEIGHT / 2 - 20;
  tft.setCursor(20, y);
  tft.println(line1);
  if (strlen(line2) > 0) {
    tft.setTextSize(1);
    tft.setCursor(20, y + 30);
    tft.println(line2);
  }
}

void showConnecting() {
  tft.fillScreen(TFT_BLUE);
  tft.setTextColor(TFT_WHITE);

  // Logo WallBot
  tft.setTextSize(3);
  tft.setCursor(50, 100);
  tft.println("WallBot");

  tft.setTextSize(2);
  tft.setCursor(20, 160);
  tft.println("Conectando WiFi...");

  tft.setTextSize(1);
  tft.setCursor(20, 200);
  tft.print("SSID: ");
  tft.println(WIFI_SSID);
}

void showConnected() {
  tft.fillScreen(TFT_DARKGREEN);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);

  tft.setCursor(40, 100);
  tft.println("WiFi Conectado!");

  tft.setTextSize(1);
  tft.setCursor(40, 140);
  tft.print("IP: ");
  tft.println(WiFi.localIP().toString());

  tft.setCursor(40, 170);
  tft.print("Server: ");
  tft.print(SERVER_HOST);
  tft.print(":");
  tft.println(SERVER_PORT);

  tft.setCursor(40, 210);
  tft.println("Cargando datos...");
}

void showError(const char* error) {
  tft.fillScreen(TFT_RED);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);

  tft.setCursor(20, 120);
  tft.println("ERROR:");

  tft.setTextSize(1);
  tft.setCursor(20, 160);
  tft.println(error);
}

void showNoData() {
  tft.fillScreen(COLOR_BG);
  tft.setTextColor(TFT_WHITE);

  tft.setTextSize(3);
  tft.setCursor(60, 100);
  tft.println("SIN");
  tft.setCursor(40, 140);
  tft.println("DATOS");

  tft.setTextSize(1);
  tft.setTextColor(COLOR_SECONDARY);
  tft.setCursor(20, 220);
  tft.println("Configura una busqueda en:");
  tft.setCursor(20, 240);
  tft.print("http://");
  tft.print(SERVER_HOST);
  tft.print(":");
  tft.println(SERVER_PORT);
}

void showConnectingServer() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_CYAN);
  tft.setTextSize(2);

  tft.setCursor(20, 120);
  tft.println("Conectando con");
  tft.setCursor(20, 150);
  tft.println("el servidor...");

  tft.setTextSize(1);
  tft.setTextColor(TFT_WHITE);
  tft.setCursor(20, 200);
  tft.print(SERVER_HOST);
  tft.print(":");
  tft.println(SERVER_PORT);
}

void showServerUnavailable() {
  tft.fillScreen(TFT_ORANGE);
  tft.setTextColor(TFT_BLACK);
  tft.setTextSize(2);

  tft.setCursor(40, 100);
  tft.println("SERVIDOR");
  tft.setCursor(20, 130);
  tft.println("NO DISPONIBLE");

  tft.setTextSize(1);
  tft.setCursor(20, 180);
  tft.print(SERVER_HOST);
  tft.print(":");
  tft.println(SERVER_PORT);

  tft.setCursor(20, 220);
  tft.println("Reintentando en 30s...");
}

// ============================================
// DECODIFICADOR JPEG
// ============================================

// Callback para dibujar bloques del JPEG
bool tft_output(int16_t x, int16_t y, uint16_t w, uint16_t h, uint16_t* bitmap) {
  // Verificar que no estamos fuera de pantalla
  if (y >= tft.height()) return false;

  // Dibujar el bloque de pixeles
  tft.pushImage(x, y, w, h, bitmap);
  return true;  // Continuar decodificando
}

bool displayJpegFromBuffer() {
  if (jpegSize == 0 || jpegBuffer == nullptr) {
    Serial.println("Buffer JPEG vacio");
    return false;
  }

  // Obtener dimensiones del JPEG
  uint16_t w = 0, h = 0;
  TJpgDec.getJpgSize(&w, &h, jpegBuffer, jpegSize);
  Serial.printf("JPEG: %dx%d pixels\n", w, h);

  // La imagen del servidor ya viene en 240x320, no escalar
  TJpgDec.setJpgScale(1);

  // Dibujar directamente en 0,0 (la imagen ya tiene el tamaño correcto)
  tft.startWrite();
  TJpgDec.drawJpg(0, 0, jpegBuffer, jpegSize);
  tft.endWrite();

  return true;
}

// ============================================
// FUNCIONES DE RED
// ============================================

bool connectWiFi() {
  showConnecting();

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");

    // Mostrar progreso en pantalla
    tft.fillRect(20, 240, attempts * 5, 10, TFT_WHITE);
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    showConnected();
    delay(2000);
    return true;
  }

  Serial.println("\nError conectando WiFi");
  showError("WiFi Failed");
  return false;
}

bool fetchImage() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado, reconectando...");
    if (!connectWiFi()) {
      return false;
    }
  }

  // Mostrar mensaje de conexion al servidor
  showConnectingServer();

  HTTPClient http;

  // Usar endpoint para pantalla grande si existe, sino el normal
  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/api/v1/screen.jpg?width=240&height=320";

  Serial.print("GET ");
  Serial.println(url);

  http.begin(url);
  http.setTimeout(15000);  // 15 segundos timeout

  int httpCode = http.GET();

  if (httpCode == HTTP_CODE_OK) {
    int len = http.getSize();
    Serial.printf("Recibido: %d bytes\n", len);

    if (len > 0 && len < JPEG_BUFFER_SIZE) {
      WiFiClient* stream = http.getStreamPtr();

      jpegSize = 0;
      while (http.connected() && jpegSize < (size_t)len) {
        size_t available = stream->available();
        if (available) {
          size_t toRead = min(available, (size_t)(len - jpegSize));
          stream->readBytes(jpegBuffer + jpegSize, toRead);
          jpegSize += toRead;
        }
        delay(1);
      }

      http.end();

      if (jpegSize == (size_t)len) {
        Serial.println("Descarga completa, mostrando imagen...");
        return displayJpegFromBuffer();
      } else {
        Serial.printf("Descarga incompleta: %d/%d\n", jpegSize, len);
        showError("Download Error");
      }
    } else if (len == 0) {
      http.end();
      Serial.println("Respuesta vacia");
      showNoData();
      return true;
    } else {
      Serial.printf("Tamano muy grande: %d bytes\n", len);
      http.end();
      showError("Size Error");
    }
  } else if (httpCode == HTTP_CODE_NOT_FOUND) {
    http.end();
    Serial.println("404 - Sin busquedas configuradas");
    showNoData();
    return true;
  } else if (httpCode < 0) {
    // Error de conexion
    Serial.printf("Connection Error: %d\n", httpCode);
    http.end();
    showServerUnavailable();
  } else {
    Serial.printf("HTTP Error: %d\n", httpCode);
    http.end();
    showError("HTTP Error");
  }

  return false;
}

// ============================================
// SETUP Y LOOP
// ============================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n=== WallBot ESP32-S3 Display ===");
  Serial.println("Freenove FNK0104 - 240x320 ILI9341");

  // Configurar backlight
  setupBacklight();

  // Inicializar pantalla TFT
  Serial.println("Inicializando TFT...");
  tft.init();
  tft.setRotation(0);  // Portrait mode
  tft.fillScreen(TFT_BLACK);
  tft.setSwapBytes(true);  // Corregir orden de bytes para colores

  // Reservar buffer JPEG (ESP32-S3 tiene mas memoria)
  jpegBuffer = (uint8_t*)ps_malloc(JPEG_BUFFER_SIZE);  // Usar PSRAM si disponible
  if (!jpegBuffer) {
    jpegBuffer = (uint8_t*)malloc(JPEG_BUFFER_SIZE);  // Fallback a RAM normal
  }

  if (!jpegBuffer) {
    Serial.println("Error: Sin memoria para buffer JPEG");
    showError("Memory Error");
    while (1) delay(1000);
  }
  Serial.printf("Buffer JPEG: %d bytes\n", JPEG_BUFFER_SIZE);

  // Configurar decodificador JPEG
  TJpgDec.setJpgScale(1);
  TJpgDec.setCallback(tft_output);

  // Pantalla de inicio
  tft.fillScreen(TFT_BLUE);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(4);
  tft.setCursor(35, 100);
  tft.println("WallBot");

  tft.setTextSize(2);
  tft.setCursor(60, 170);
  tft.println("ESP32-S3");

  tft.setTextSize(1);
  tft.setCursor(80, 220);
  tft.println("v3.0");

  tft.setCursor(50, 280);
  tft.println("240x320 ILI9341");

  delay(2000);

  // Conectar WiFi
  if (!connectWiFi()) {
    Serial.println("Reintentando en 5s...");
    delay(5000);
    ESP.restart();
  }

  // Primera carga de imagen
  fetchImage();
  lastPollTime = millis();
}

void loop() {
  unsigned long currentTime = millis();

  // Polling periodico
  if (currentTime - lastPollTime >= POLL_INTERVAL_MS) {
    Serial.println("Actualizando pantalla...");
    fetchImage();
    lastPollTime = currentTime;
  }

  // Reconectar WiFi si se pierde
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi perdido, reconectando...");
    connectWiFi();
  }

  delay(100);
}
