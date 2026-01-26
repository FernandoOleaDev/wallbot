/*
 * Test minimo para TFT ST7735 con ESP32-CAM
 * Si esto no funciona, el problema es la configuracion de TFT_eSPI
 */

#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== TEST TFT ST7735 ===");
  Serial.println("Inicializando pantalla...");

  tft.init();
  Serial.println("tft.init() completado");

  tft.setRotation(0);
  Serial.println("Rotation: 0");

  // Test 1: Pantalla roja
  Serial.println("Test 1: Pantalla ROJA");
  tft.fillScreen(TFT_RED);
  delay(2000);

  // Test 2: Pantalla verde
  Serial.println("Test 2: Pantalla VERDE");
  tft.fillScreen(TFT_GREEN);
  delay(2000);

  // Test 3: Pantalla azul
  Serial.println("Test 3: Pantalla AZUL");
  tft.fillScreen(TFT_BLUE);
  delay(2000);

  // Test 4: Texto
  Serial.println("Test 4: Texto");
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.println("HOLA");
  tft.setCursor(10, 40);
  tft.println("MUNDO");
  tft.setTextSize(1);
  tft.setCursor(10, 80);
  tft.println("ESP32-CAM");
  tft.setCursor(10, 100);
  tft.println("TFT OK!");

  Serial.println("=== TEST COMPLETADO ===");
  Serial.println("Si no ves colores/texto, revisa User_Setup.h");
}

void loop() {
  // Parpadeo para saber que esta vivo
  delay(5000);
  Serial.println("Loop - ESP32 funcionando...");
}
