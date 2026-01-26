/*
 * WallBot ESP32-CAM Display
 * Muestra productos de Wallapop en una pantalla TFT ST7735 128x160
 *
 * Conexiones:
 *   ESP32-CAM  ->  TFT ST7735
 *   3.3V       ->  VCC
 *   GND        ->  GND
 *   GPIO15     ->  CS
 *   GPIO2      ->  DC (A0)
 *   GPIO13     ->  SDA (MOSI)
 *   GPIO14     ->  SCL (SCK)
 *   GPIO0      ->  LED (BLK) - Backlight con PWM
 *   3.3V       ->  RST (o GPIO12 si prefieres)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>
#include <JPEGDEC.h>

// ============================================
// CONFIGURACION - MODIFICAR SEGUN TU RED
// ============================================

const char* WIFI_SSID = "MOVISTAR_F0F9";
const char* WIFI_PASSWORD = "orQ5ygyjkhYUnUcdnM5x";

const char* SERVER_HOST = "192.168.1.41";
const int SERVER_PORT = 9500;

// Intervalo de polling en milisegundos
const unsigned long POLL_INTERVAL_MS = 10000;

// ============================================
// PINES ESP32-CAM
// ============================================

#define TFT_CS    15
#define TFT_RST   -1   // Conectado a 3.3V
#define TFT_DC     2
#define TFT_MOSI  13
#define TFT_SCLK  14
#define TFT_BL     0   // Backlight en GPIO0

// ============================================
// OBJETOS GLOBALES
// ============================================

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_MOSI, TFT_SCLK, TFT_RST);
JPEGDEC jpeg;

unsigned long lastPollTime = 0;
int brightness = 255;

// Buffer para imagen JPEG
#define JPEG_BUFFER_SIZE 30000
uint8_t* jpegBuffer = nullptr;
size_t jpegSize = 0;

// ============================================
// FUNCIONES DE PANTALLA
// ============================================

void setupBacklight() {
  ledcAttach(TFT_BL, 5000, 8);
  ledcWrite(TFT_BL, brightness);
}

void setBrightness(int level) {
  brightness = constrain(level, 0, 255);
  ledcWrite(TFT_BL, brightness);
}

void showMessage(const char* line1, const char* line2 = "", uint16_t color = ST77XX_WHITE) {
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(color);
  tft.setTextSize(1);

  int y = 60;
  tft.setCursor(10, y);
  tft.println(line1);
  if (strlen(line2) > 0) {
    tft.setCursor(10, y + 20);
    tft.println(line2);
  }
}

void showConnecting() {
  tft.fillScreen(ST77XX_BLUE);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(10, 40);
  tft.println("WallBot");
  tft.setTextSize(1);
  tft.setCursor(10, 80);
  tft.println("Conectando WiFi...");
}

void showConnected() {
  tft.fillScreen(ST77XX_GREEN);
  tft.setTextColor(ST77XX_BLACK);
  tft.setTextSize(1);
  tft.setCursor(10, 50);
  tft.println("WiFi OK!");
  tft.setCursor(10, 70);
  tft.println(WiFi.localIP().toString());
  tft.setCursor(10, 100);
  tft.println("Cargando...");
}

void showError(const char* error) {
  tft.fillScreen(ST77XX_RED);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(1);
  tft.setCursor(10, 60);
  tft.println("ERROR:");
  tft.setCursor(10, 80);
  tft.println(error);
}

void showNoData() {
  tft.fillScreen(ST77XX_BLUE);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(10, 40);
  tft.println("SIN");
  tft.setCursor(10, 65);
  tft.println("DATOS");
  tft.setTextSize(1);
  tft.setCursor(10, 100);
  tft.println("Configura busqueda");
  tft.setCursor(10, 115);
  tft.print("en ");
  tft.print(SERVER_HOST);
}

// ============================================
// DECODIFICADOR JPEG
// ============================================

// Callback para dibujar pixeles del JPEG
int drawJPEGPixels(JPEGDRAW *pDraw) {
  int x = pDraw->x;
  int y = pDraw->y;
  int w = pDraw->iWidth;
  int h = pDraw->iHeight;
  uint16_t *pixels = pDraw->pPixels;

  // Dibujar pixel por pixel (compatible con Adafruit)
  for (int j = 0; j < h; j++) {
    for (int i = 0; i < w; i++) {
      uint16_t color = pixels[j * w + i];
      tft.drawPixel(x + i, y + j, color);
    }
  }

  return 1; // Continuar decodificando
}

bool displayJpegFromBuffer() {
  if (jpegSize == 0 || jpegBuffer == nullptr) {
    return false;
  }

  // Abrir JPEG desde buffer
  if (jpeg.openRAM(jpegBuffer, jpegSize, drawJPEGPixels)) {
    Serial.print("JPEG: ");
    Serial.print(jpeg.getWidth());
    Serial.print("x");
    Serial.println(jpeg.getHeight());

    // Decodificar y dibujar
    jpeg.setPixelType(RGB565_LITTLE_ENDIAN);
    jpeg.decode(0, 0, 0);
    jpeg.close();
    return true;
  } else {
    Serial.println("Error abriendo JPEG");
    return false;
  }
}

// ============================================
// FUNCIONES DE RED
// ============================================

bool connectWiFi() {
  showConnecting();

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    showConnected();
    delay(1500);
    return true;
  }

  Serial.println("\nError WiFi");
  showError("WiFi Failed");
  return false;
}

bool fetchImage() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado");
    if (!connectWiFi()) {
      return false;
    }
  }

  HTTPClient http;
  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/api/v1/screen.jpg";

  Serial.print("GET ");
  Serial.println(url);

  http.begin(url);
  http.setTimeout(15000);

  int httpCode = http.GET();

  if (httpCode == HTTP_CODE_OK) {
    int len = http.getSize();
    Serial.print("Recibido: ");
    Serial.print(len);
    Serial.println(" bytes");

    if (len > 0 && len < JPEG_BUFFER_SIZE) {
      WiFiClient* stream = http.getStreamPtr();

      jpegSize = 0;
      while (http.connected() && jpegSize < len) {
        size_t available = stream->available();
        if (available) {
          size_t toRead = min(available, (size_t)(len - jpegSize));
          stream->readBytes(jpegBuffer + jpegSize, toRead);
          jpegSize += toRead;
        }
        delay(1);
      }

      http.end();

      if (jpegSize == len) {
        Serial.println("Descarga completa");
        return displayJpegFromBuffer();
      } else {
        Serial.println("Descarga incompleta");
        showError("Download Error");
      }
    } else if (len == 0) {
      http.end();
      Serial.println("Respuesta vacia");
      showNoData();
      return true;
    } else {
      Serial.print("Tamano muy grande: ");
      Serial.println(len);
      http.end();
      showError("Size Error");
    }
  } else if (httpCode == HTTP_CODE_NOT_FOUND) {
    http.end();
    Serial.println("404 - Sin busquedas");
    showNoData();
    return true;
  } else {
    Serial.print("HTTP Error: ");
    Serial.println(httpCode);
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

  Serial.println("\n=== WallBot ESP32 Display ===");

  // Configurar backlight
  setupBacklight();
  setBrightness(255);

  // Inicializar pantalla
  Serial.println("Inicializando TFT...");
  tft.initR(INITR_GREENTAB);
  tft.setRotation(0);
  tft.fillScreen(ST77XX_BLACK);

  // Reservar buffer JPEG
  jpegBuffer = (uint8_t*)malloc(JPEG_BUFFER_SIZE);
  if (!jpegBuffer) {
    Serial.println("Error: Sin memoria para JPEG");
    showError("Memory Error");
    while (1) delay(1000);
  }
  Serial.print("Buffer: ");
  Serial.print(JPEG_BUFFER_SIZE);
  Serial.println(" bytes");

  // Pantalla de inicio
  tft.fillScreen(ST77XX_BLUE);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(15, 50);
  tft.println("WallBot");
  tft.setTextSize(1);
  tft.setCursor(40, 90);
  tft.println("v2.0");
  delay(1000);

  // Conectar WiFi
  if (!connectWiFi()) {
    Serial.println("Reintentando en 5s...");
    delay(5000);
    ESP.restart();
  }

  // Primera carga
  fetchImage();
  lastPollTime = millis();
}

void loop() {
  unsigned long currentTime = millis();

  // Polling periodico
  if (currentTime - lastPollTime >= POLL_INTERVAL_MS) {
    fetchImage();
    lastPollTime = currentTime;
  }

  // Reconectar WiFi si se pierde
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi perdido");
    connectWiFi();
  }

  delay(100);
}
