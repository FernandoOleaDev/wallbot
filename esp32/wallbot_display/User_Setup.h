// ===========================================
// User_Setup.h para WallBot ESP32-CAM + TFT ST7735
// ===========================================
//
// IMPORTANTE: Copia este archivo a la carpeta de la libreria TFT_eSPI:
//   Windows: Documentos/Arduino/libraries/TFT_eSPI/User_Setup.h
//   (reemplaza el archivo existente)
//
// O alternativamente, renombra este archivo a User_Setup.h en la carpeta
// de la libreria TFT_eSPI
// ===========================================

// Controlador de pantalla
#define ST7735_DRIVER

// Resolucion de pantalla
#define TFT_WIDTH  128
#define TFT_HEIGHT 160

// Tipo de pantalla ST7735 (descomenta solo UNO):
// Tab verde 128x160:
#define ST7735_GREENTAB

// Tab roja 128x160:
// #define ST7735_REDTAB

// Tab negra 128x160:
// #define ST7735_BLACKTAB

// ===========================================
// Pines ESP32-CAM -> TFT ST7735
// ===========================================
// Conexiones fisicas:
//   TFT VCC  -> ESP32-CAM 3.3V
//   TFT GND  -> ESP32-CAM GND
//   TFT CS   -> GPIO 15
//   TFT RST  -> GPIO 4 (o conectar a EN para reset con el ESP32)
//   TFT DC   -> GPIO 2
//   TFT SDA  -> GPIO 13 (MOSI)
//   TFT SCL  -> GPIO 14 (SCK)
//   TFT LED  -> 3.3V (backlight siempre encendido)
// ===========================================

#define TFT_CS   15  // Chip select
#define TFT_DC    2  // Data/Command
#define TFT_RST   4  // Reset (usar -1 si conectado a EN del ESP32)

// Pines SPI (HSPI en ESP32)
#define TFT_MOSI 13
#define TFT_SCLK 14
#define TFT_MISO -1  // No usado para pantalla TFT

// ===========================================
// Configuracion SPI
// ===========================================

// Frecuencia SPI (27MHz funciona bien, puedes probar 40MHz)
#define SPI_FREQUENCY  27000000

// Frecuencia para lectura (no usado normalmente)
#define SPI_READ_FREQUENCY  20000000

// Frecuencia para touch (no aplica aqui)
#define SPI_TOUCH_FREQUENCY  2500000

// ===========================================
// Fuentes
// ===========================================

// Cargar fuentes por defecto
#define LOAD_GLCD   // Font 1. Original Adafruit 8 pixel font
#define LOAD_FONT2  // Font 2. Small 16 pixel high font
#define LOAD_FONT4  // Font 4. Medium 26 pixel high font
#define LOAD_FONT6  // Font 6. Large 48 pixel numeric font
#define LOAD_FONT7  // Font 7. 7 segment 48 pixel font
#define LOAD_FONT8  // Font 8. Large 75 pixel font
#define LOAD_GFXFF  // FreeFonts

// Smooth fonts
#define SMOOTH_FONT

// ===========================================
// Otras configuraciones
// ===========================================

// Usar transacciones SPI para evitar conflictos
#define SUPPORT_TRANSACTIONS
