/*
 * Test con libreria Adafruit para diagnostico
 * Si esto funciona y TFT_eSPI no, el problema es la config de TFT_eSPI
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

// Crear objeto TFT con pines personalizados
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_MOSI, TFT_SCLK, TFT_RST);

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== TEST ADAFRUIT ST7735 ===");

  // Probar diferentes inicializadores
  // OPCION 1: GREENTAB (pegatina verde)
  Serial.println("Probando INITR_GREENTAB...");
  tft.initR(INITR_GREENTAB);

  // Si no funciona, comenta la linea anterior y descomenta una de estas:
  // tft.initR(INITR_BLACKTAB);   // OPCION 2
  // tft.initR(INITR_REDTAB);     // OPCION 3
  // tft.initR(INITR_144GREENTAB); // OPCION 4 (para 128x128)

  Serial.println("Init completado");

  // Test 1: Rojo
  Serial.println("Test 1: ROJO");
  tft.fillScreen(ST77XX_RED);
  delay(2000);

  // Test 2: Verde
  Serial.println("Test 2: VERDE");
  tft.fillScreen(ST77XX_GREEN);
  delay(2000);

  // Test 3: Azul
  Serial.println("Test 3: AZUL");
  tft.fillScreen(ST77XX_BLUE);
  delay(2000);

  // Test 4: Blanco
  Serial.println("Test 4: BLANCO");
  tft.fillScreen(ST77XX_WHITE);
  delay(2000);

  // Test 5: Texto
  Serial.println("Test 5: TEXTO");
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.println("HOLA");
  tft.setCursor(10, 40);
  tft.println("MUNDO");
  tft.setTextSize(1);
  tft.setCursor(10, 80);
  tft.println("ESP32-CAM");
  tft.setCursor(10, 100);
  tft.setTextColor(ST77XX_GREEN);
  tft.println("Adafruit OK!");

  Serial.println("=== TEST COMPLETADO ===");
}

void loop() {
  delay(5000);
  Serial.println("Loop...");
}
