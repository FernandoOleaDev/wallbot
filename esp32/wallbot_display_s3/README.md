# WallBot ESP32-S3 Display (Freenove FNK0104)

Visor de WallBot para la placa **Freenove ESP32-S3 Display 2.8"** (ES3C28P/ES3N28P).

## Especificaciones

| Componente | Valor |
|------------|-------|
| Display | ILI9341V 2.8" IPS |
| Resolucion | 240x320 pixels |
| MCU | ESP32-S3 |
| Memoria | 8MB PSRAM + 16MB Flash |

## Paso a Paso - Instalacion

### 1. Instalar Arduino IDE

Si no lo tienes, descarga Arduino IDE desde: https://www.arduino.cc/en/software

### 2. Agregar soporte para ESP32-S3

1. Abre Arduino IDE
2. Ve a **Archivo > Preferencias**
3. En "URLs adicionales de gestor de tarjetas" agrega:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Ve a **Herramientas > Placa > Gestor de tarjetas**
5. Busca "esp32" e instala **esp32 by Espressif Systems** (version 2.0.11 o superior)

### 3. Instalar las librerias de Freenove

Las librerias estan en: `docs/Freenove_ESP32_S3_Display-main/Libraries/`

Instala estas 3 librerias EN ESTE ORDEN:

1. **TFT_eSPI_v2.5.43.zip**
   - Arduino IDE > Programa > Incluir Libreria > Añadir biblioteca .ZIP
   - Selecciona: `docs/Freenove_ESP32_S3_Display-main/Libraries/TFT_eSPI_v2.5.43.zip`

2. **TFT_eSPI_Setups_v1.2.zip** (IMPORTANTE - Configuracion Freenove)
   - Arduino IDE > Programa > Incluir Libreria > Añadir biblioteca .ZIP
   - Selecciona: `docs/Freenove_ESP32_S3_Display-main/Libraries/TFT_eSPI_Setups_v1.2.zip`

3. **TJpg_Decoder_v1.1.0.zip**
   - Arduino IDE > Programa > Incluir Libreria > Añadir biblioteca .ZIP
   - Selecciona: `docs/Freenove_ESP32_S3_Display-main/Libraries/TJpg_Decoder_v1.1.0.zip`

### 4. Configurar TFT_eSPI para Freenove

1. Ve a la carpeta de librerias de Arduino:
   - Windows: `C:\Users\TU_USUARIO\Documents\Arduino\libraries\TFT_eSPI\`
   - Mac: `~/Documents/Arduino/libraries/TFT_eSPI/`

2. Abre el archivo `User_Setup_Select.h`

3. Busca las lineas de configuracion FNK0104 (lineas 36-37 aprox) y asegurate de que:
   - **Solo UNA este descomentada** (sin `//` al inicio)
   - Las demas esten comentadas (con `//`)

   **Si tu pantalla muestra colores normales:**
   ```cpp
   #define FNK0104A_2P8_240x320_ILI9341
   //#define FNK0104B_2P8_240x320_ILI9341
   ```

   **Si tu pantalla muestra colores invertidos:**
   ```cpp
   //#define FNK0104A_2P8_240x320_ILI9341
   #define FNK0104B_2P8_240x320_ILI9341
   ```

4. Asegurate de que `User_Setup.h` este comentado (linea 26):
   ```cpp
   //#include <User_Setup.h>
   ```

5. Guarda el archivo

### 5. Configurar tu WiFi y Servidor

Abre `wallbot_display_s3.ino` y modifica estas lineas con tus datos:

```cpp
const char* WIFI_SSID = "TU_WIFI";           // Nombre de tu red WiFi
const char* WIFI_PASSWORD = "TU_PASSWORD";    // Contrasena WiFi

const char* SERVER_HOST = "192.168.1.124";    // IP del servidor WallBot
const int SERVER_PORT = 9500;                 // Puerto del servidor
```

### 6. Configurar la Placa en Arduino IDE

Ve a **Herramientas** y configura:

| Opcion | Valor |
|--------|-------|
| Board | ESP32S3 Dev Module |
| USB CDC On Boot | Enabled |
| CPU Frequency | 240MHz (WiFi) |
| Core Debug Level | None |
| USB DFU On Boot | Disabled |
| Erase All Flash | Disabled |
| Events Run On | Core 1 |
| Flash Mode | QIO 80MHz |
| Flash Size | 16MB (128Mb) |
| JTAG Adapter | Disabled |
| Arduino Runs On | Core 1 |
| USB Firmware MSC | Disabled |
| Partition Scheme | Default 4MB with spiffs |
| PSRAM | OPI PSRAM |
| Upload Mode | UART0 / Hardware CDC |
| Upload Speed | 921600 |
| USB Mode | Hardware CDC and JTAG |

### 7. Subir el Programa

1. Conecta tu Freenove ESP32-S3 Display al PC con cable USB-C
2. Selecciona el puerto COM correcto en **Herramientas > Puerto**
3. Haz clic en **Subir** (flecha hacia la derecha)

**Si falla la subida:**
- Mantén pulsado el boton **BOOT**
- Pulsa y suelta **RESET**
- Suelta **BOOT**
- Intenta subir de nuevo

### 8. Iniciar el Servidor WallBot

Asegurate de que el servidor WallBot esta corriendo en tu PC:

```bash
cd wallbot
python -m uvicorn src.server.app:app --host 0.0.0.0 --port 9500
```

O con Docker:
```bash
docker-compose up -d
```

## Funcionamiento

Una vez programado:

1. La pantalla mostrara "WallBot ESP32-S3"
2. Se conectara a tu WiFi
3. Mostrara la IP asignada
4. Comenzara a mostrar productos de tus busquedas de Wallapop
5. Se actualiza automaticamente cada 30 segundos

## Solucion de Problemas

### Pantalla en blanco
- Verifica que instalaste `TFT_eSPI_Setups_v1.2.zip`
- Verifica la configuracion en `User_Setup_Select.h`

### Colores invertidos
- Usa `Freenove_ESP32S3_ILI9341_Invert.h` en lugar de la configuracion normal

### No conecta WiFi
- Verifica SSID y password
- Asegurate de que tu red es 2.4GHz (no 5GHz)

### No muestra imagenes
- Verifica que el servidor esta corriendo
- Verifica la IP del servidor
- Abre el monitor serie (115200 baudios) para ver errores

## Pines del Display (Referencia)

| GPIO | Funcion |
|------|---------|
| 10 | TFT_CS |
| 46 | TFT_DC |
| 12 | TFT_SCLK |
| 11 | TFT_MOSI |
| 45 | TFT_BL (Backlight) |
| 42 | RGB LED |
