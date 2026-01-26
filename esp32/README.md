# WallBot ESP32-CAM + TFT Display

Guia completa para programar la ESP32-CAM AI-Thinker con una pantalla TFT ST7735 128x160.

## Hardware Necesario

- ESP32-CAM AI-Thinker
- Pantalla TFT ST7735 128x160
- USB-TTL (FTDI, CP2102, CH340, etc.)
- Cables dupont
- Cable USB para el programador

---

## PASO 1: Conexiones USB-TTL -> ESP32-CAM (Para Programar)

```
 USB-TTL                    ESP32-CAM
+--------+                 +-----------+
|        |                 |           |
|   GND  |---------------->|   GND     |
|        |                 |           |
|   VCC  |-----(5V)------->|   5V      |
|  (5V)  |                 |           |
|        |                 |           |
|   TX   |---------------->|   U0R     |
|        |                 |           |
|   RX   |---------------->|   U0T     |
|        |                 |           |
+--------+                 |           |
                           |  GPIO0 ---|---+
                           |           |   |
                           |   GND  ---|---+ (JUMPER para programar)
                           +-----------+
```

**IMPORTANTE:** El jumper entre GPIO0 y GND es necesario SOLO para subir codigo.

### Tabla de Conexiones USB-TTL

| USB-TTL | ESP32-CAM | Notas |
|---------|-----------|-------|
| GND | GND | Tierra comun |
| VCC (5V) | 5V | Alimentacion |
| TX | U0R | TX del programador al RX del ESP32 |
| RX | U0T | RX del programador al TX del ESP32 |

### Jumper de Programacion

| Estado | GPIO0 | Modo |
|--------|-------|------|
| **Programar** | Conectado a GND | Flash/Download mode |
| **Ejecutar** | Sin conectar | Normal execution |

---

## PASO 2: Conexiones ESP32-CAM -> Pantalla TFT ST7735

```
 ESP32-CAM                  TFT ST7735
+-----------+              +------------+
|           |              |            |
|   3.3V    |------------->|   VCC      |
|           |              |            |
|   GND     |------------->|   GND      |
|           |              |            |
|  GPIO 15  |------------->|   CS       |
|           |              |            |
|  GPIO 4   |------------->|   RST      |
|           |              |            |
|  GPIO 2   |------------->|   DC (A0)  |
|           |              |            |
|  GPIO 13  |------------->|   SDA/MOSI |
|           |              |            |
|  GPIO 14  |------------->|   SCL/SCK  |
|           |              |            |
|   3.3V    |------------->|   LED/BLK  |
|           |              |            |
+-----------+              +------------+
```

### Tabla de Conexiones TFT

| ESP32-CAM | TFT ST7735 | Funcion |
|-----------|------------|---------|
| 3.3V | VCC | Alimentacion pantalla |
| GND | GND | Tierra comun |
| GPIO 15 | CS | Chip Select |
| GPIO 4 | RST/RESET | Reset pantalla |
| GPIO 2 | DC / A0 | Data/Command |
| GPIO 13 | SDA / MOSI | Datos SPI |
| GPIO 14 | SCL / SCK | Reloj SPI |
| 3.3V | LED / BLK | Backlight (siempre ON) |

---

## PASO 3: Configurar Arduino IDE 2.3.7

### 3.1 Agregar URL de ESP32

1. Abre Arduino IDE
2. Ve a **File -> Preferences** (o Ctrl+Comma)
3. En **"Additional boards manager URLs"** agrega:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Click **OK**

### 3.2 Instalar Board ESP32

1. Ve a **Tools -> Board -> Boards Manager** (o click en el icono de placa a la izquierda)
2. Busca **"esp32"**
3. Instala **"esp32 by Espressif Systems"** (version 2.x o 3.x)
4. Espera a que se complete la instalacion

### 3.3 Instalar Librerias

Ve a **Sketch -> Include Library -> Manage Libraries** (o Ctrl+Shift+I):

1. Busca **"TFT_eSPI"** e instala la de **Bodmer**
2. Busca **"JPEGDecoder"** e instala la de **Bodmer**

---

## PASO 4: Configurar la Libreria TFT_eSPI

**CRITICO:** La libreria TFT_eSPI requiere configuracion manual.

### 4.1 Localizar la carpeta de la libreria

La libreria esta en:
```
C:\Users\TU_USUARIO\Documents\Arduino\libraries\TFT_eSPI\
```

### 4.2 Editar User_Setup.h

1. Abre el archivo `User_Setup.h` en la carpeta de TFT_eSPI
2. **Comenta** todas las lineas de configuracion existentes (agrega // al inicio)
3. Agrega al final del archivo:

```cpp
// ============================================
// CONFIGURACION PARA WALLBOT ESP32-CAM + ST7735
// ============================================

// Driver de pantalla
#define ST7735_DRIVER

// Resolucion
#define TFT_WIDTH  128
#define TFT_HEIGHT 160

// Tipo de pantalla (descomenta solo UNA segun tu pantalla):
#define ST7735_GREENTAB      // Tab verde - la mas comun
// #define ST7735_REDTAB      // Tab roja
// #define ST7735_BLACKTAB    // Tab negra

// Pines ESP32-CAM
#define TFT_CS   15
#define TFT_DC    2
#define TFT_RST   4
#define TFT_MOSI 13
#define TFT_SCLK 14
#define TFT_MISO -1

// Frecuencia SPI
#define SPI_FREQUENCY 27000000

// Fuentes
#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF
#define SMOOTH_FONT
```

4. **Guarda** el archivo

### 4.3 Alternativa: Usar archivo incluido

Tambien puedes copiar el archivo `User_Setup.h` de esta carpeta (`esp32/wallbot_display/User_Setup.h`) a la carpeta de la libreria, reemplazando el existente.

---

## PASO 5: Configurar el Sketch

1. Abre `wallbot_display.ino` en Arduino IDE
2. Edita las siguientes lineas con tus datos:

```cpp
// Credenciales WiFi
const char* WIFI_SSID = "TU_WIFI_SSID";         // <-- Tu red WiFi
const char* WIFI_PASSWORD = "TU_WIFI_PASSWORD";  // <-- Tu clave WiFi

// Servidor Wallbot
const char* SERVER_HOST = "192.168.1.100";  // <-- IP de tu servidor/NAS
const int SERVER_PORT = 8000;
```

---

## PASO 6: Seleccionar Placa y Puerto

1. **Tools -> Board -> esp32 -> AI Thinker ESP32-CAM**
2. **Tools -> Port** -> Selecciona el puerto COM de tu USB-TTL (ej: COM3, COM4...)

### Configuracion recomendada en Tools:

| Opcion | Valor |
|--------|-------|
| Board | AI Thinker ESP32-CAM |
| CPU Frequency | 240MHz (WiFi/BT) |
| Flash Frequency | 80MHz |
| Flash Mode | QIO |
| Partition Scheme | Huge APP (3MB No OTA) |
| Upload Speed | 115200 |

---

## PASO 7: Subir el Codigo

### 7.1 Preparar para programacion

1. **Desconecta** el USB-TTL del PC
2. **Conecta el jumper** entre GPIO0 y GND en la ESP32-CAM
3. **Conecta** el USB-TTL al PC
4. Espera a que Windows reconozca el dispositivo

### 7.2 Subir el sketch

1. En Arduino IDE, click en **Upload** (flecha hacia la derecha)
2. Espera a que aparezca **"Connecting........"** en la consola
3. **Presiona el boton RST** (reset) en la ESP32-CAM
4. El codigo deberia empezar a subir

```
Connecting........_____....._____....._____
Chip is ESP32-D0WDQ6 (revision 1)
Features: WiFi, BT, Dual Core, 240MHz
Writing at 0x00010000... (33%)
Writing at 0x00020000... (66%)
Writing at 0x00030000... (100%)
```

### 7.3 Ejecutar el programa

1. **Desconecta** el USB-TTL del PC
2. **Quita el jumper** entre GPIO0 y GND
3. **Reconecta** el USB-TTL al PC (o alimenta con fuente externa 5V)
4. La ESP32-CAM arrancara y ejecutara el programa

---

## PASO 8: Ver logs de depuracion (Serial Monitor)

1. **Tools -> Serial Monitor** (o Ctrl+Shift+M)
2. Configura la velocidad a **115200 baud**
3. Veras mensajes como:

```
=== WallBot ESP32 Display ===
Pantalla inicializada
Buffer JPEG: 25000 bytes
WiFi conectado!
IP: 192.168.1.45
Fetching: http://192.168.1.100:8000/api/v1/screen.jpg
Imagen recibida: 8432 bytes
Decodificando JPEG...
Imagen mostrada correctamente
```

---

## Solucion de Problemas

### "Failed to connect to ESP32"

- Verifica que GPIO0 este conectado a GND
- Presiona RST cuando veas "Connecting..."
- Verifica las conexiones TX/RX (pueden estar cruzadas)
- Prueba con Upload Speed mas bajo (57600)

### Pantalla en blanco o colores incorrectos

- Verifica las conexiones de la pantalla
- Prueba cambiar `ST7735_GREENTAB` por `ST7735_REDTAB` o `ST7735_BLACKTAB`
- Verifica que editaste correctamente el `User_Setup.h`

### "Brownout detector was triggered"

- El USB no proporciona suficiente corriente
- Usa una fuente de 5V externa con al menos 500mA
- No uses hubs USB sin alimentacion

### Error 404 o "Sin datos"

- El servidor no tiene busquedas activas
- Crea una busqueda desde la web UI: http://IP_SERVIDOR:8000

### No conecta a WiFi

- Verifica SSID y password (sensible a mayusculas)
- La ESP32-CAM solo soporta WiFi 2.4GHz (no 5GHz)
- Acerca la ESP32 al router para probar

---

## Pinout ESP32-CAM AI-Thinker (Referencia)

```
                    +------------------+
                    |    ESP32-CAM     |
                    |    AI-Thinker    |
                    |                  |
         5V --------|  5V          GND |-------- GND
        3V3 --------|  3V3        IO16 |
                    |  IO0        IO0  |
        GND --------|  GND        IO2  |-------- TFT DC
        VCC --------|  VCC        IO4  |-------- TFT RST
        U0R --------|  U0R       IO12  |
        U0T --------|  U0T       IO13  |-------- TFT MOSI
       IO15 --------|  IO15      IO14  |-------- TFT SCK
                    |                  |
                    |    [CAMERA]      |
                    +------------------+
                           ||
                         [RST]
```

---

## Referencias

- [Random Nerd Tutorials - Program ESP32-CAM](https://randomnerdtutorials.com/program-upload-code-esp32-cam/)
- [TFT_eSPI Library](https://github.com/Bodmer/TFT_eSPI)
- [ESP32-CAM Pinout Guide](https://randomnerdtutorials.com/esp32-cam-ai-thinker-pinout/)
- [How to configure TFT_eSPI](https://www.makerguides.com/how-to-configure-tft_espi-library-for-tft-display/)
