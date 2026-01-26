/*
 * Test de brillo con PWM para TFT ST7735
 * Conectar LED/BLK de la pantalla a GPIO4
 */

#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>

// Pines para ESP32-CAM (HSPI)
#define TFT_CS    15
#define TFT_RST   -1
#define TFT_DC     2
#define TFT_MOSI  13
#define TFT_SCLK  14
#define TFT_BL     0  // Backlight en GPIO0 (no usa el flash)

// Crear objeto TFT
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_MOSI, TFT_SCLK, TFT_RST);

// Variables para brillo
int currentBrightness = 255;  // Brillo actual (0-255)

void setupBacklight() {
  // Configurar PWM para backlight en ESP32 (API nueva v3.x)
  ledcAttach(TFT_BL, 5000, 8);  // GPIO, frecuencia 5kHz, resolucion 8 bits
  ledcWrite(TFT_BL, currentBrightness);
  Serial.println("Backlight configurado en GPIO4");
}

void setBrightness(int level) {
  currentBrightness = constrain(level, 0, 255);
  ledcWrite(TFT_BL, currentBrightness);
  Serial.print("Brillo: ");
  Serial.println(currentBrightness);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== TEST BRILLO ST7735 ===");

  // Primero configurar backlight
  setupBacklight();

  // Inicializar pantalla
  Serial.println("Inicializando pantalla...");
  tft.initR(INITR_GREENTAB);
  Serial.println("Pantalla inicializada");

  // Mostrar pantalla de prueba
  tft.fillScreen(ST77XX_BLUE);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(20, 20);
  tft.println("TEST");
  tft.setCursor(10, 50);
  tft.println("BRILLO");

  tft.setTextSize(1);
  tft.setCursor(10, 90);
  tft.println("Mira Serial Monitor");
  tft.setCursor(10, 105);
  tft.println("para comandos");

  Serial.println("");
  Serial.println("=== COMANDOS ===");
  Serial.println("Escribe en Serial Monitor:");
  Serial.println("  0   = Apagado");
  Serial.println("  64  = 25%");
  Serial.println("  128 = 50%");
  Serial.println("  192 = 75%");
  Serial.println("  255 = Maximo");
  Serial.println("================");
  Serial.println("");

  // Iniciar con brillo maximo
  setBrightness(255);
}

void loop() {
  // Leer comandos del Serial Monitor
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    int brightness = input.toInt();

    if (brightness >= 0 && brightness <= 255) {
      setBrightness(brightness);

      // Mostrar en pantalla
      tft.fillRect(0, 130, 128, 30, ST77XX_BLUE);
      tft.setCursor(10, 140);
      tft.setTextColor(ST77XX_YELLOW);
      tft.print("Brillo: ");
      tft.print(brightness);
    }
  }

  // Mantener el loop activo
  delay(100);
}
