# WallBot ESP32-CAM Display

Sistema de visualización de productos de Wallapop en una pantalla TFT ST7735 128x160 conectada a una ESP32-CAM.

La ESP32-CAM se conecta a un servidor que monitoriza búsquedas en Wallapop y muestra los productos encontrados en la pantalla TFT.

---

## Tabla de Contenidos

1. [Hardware Necesario](#hardware-necesario)
2. [Esquema de Conexiones](#esquema-de-conexiones)
3. [Configuración de Arduino IDE](#configuración-de-arduino-ide)
4. [Instalación de Librerías](#instalación-de-librerías)
5. [Configuración del Código](#configuración-del-código)
6. [Programar la ESP32-CAM](#programar-la-esp32-cam)
7. [Configuración del Servidor](#configuración-del-servidor)
8. [Solución de Problemas](#solución-de-problemas)

---

## Hardware Necesario

| Componente | Descripción |
|------------|-------------|
| ESP32-CAM AI-Thinker | Placa con ESP32 y cámara OV2640 |
| Pantalla TFT ST7735 | Display 1.8" 128x160 píxeles (pegatina verde) |
| USB-TTL | Programador serial (FTDI, CP2102, CH340) |
| Cables Dupont | Cables macho-hembra para conexiones |
| Protoboard | Placa de pruebas (opcional pero recomendado) |

---

## Esquema de Conexiones

### Conexiones ESP32-CAM → TFT ST7735

```
ESP32-CAM                    TFT ST7735
─────────                    ──────────
   3.3V   ─────────────────►  VCC
   GND    ─────────────────►  GND
  GPIO15  ─────────────────►  CS
  GPIO2   ─────────────────►  DC (A0)
  GPIO13  ─────────────────►  SDA (MOSI)
  GPIO14  ─────────────────►  SCL (SCK)
  GPIO0   ─────────────────►  LED (BLK)
   3.3V   ─────────────────►  RST
```

### Tabla de Conexiones TFT

| Pin TFT | Nombre Alternativo | ESP32-CAM | Función |
|---------|-------------------|-----------|---------|
| VCC | - | 3.3V | Alimentación |
| GND | - | GND | Tierra |
| CS | SS, CE | GPIO15 | Chip Select SPI |
| DC | A0, RS | GPIO2 | Data/Command |
| SDA | MOSI, DIN, SDI | GPIO13 | Datos SPI |
| SCL | SCK, CLK | GPIO14 | Reloj SPI |
| LED | BLK, LEDA | GPIO0 | Backlight (PWM) |
| RST | RES, RESET | 3.3V | Reset (fijo alto) |

### Conexiones USB-TTL → ESP32-CAM (Solo para Programar)

```
USB-TTL              ESP32-CAM
───────              ─────────
  GND   ───────────►  GND
  5V    ───────────►  5V
  TX    ───────────►  U0R
  RX    ───────────►  U0T
```

**IMPORTANTE:** El jumper GPIO0-GND solo se usa para programar.

---

## Configuración de Arduino IDE

### Paso 1: Agregar soporte para ESP32

1. Abre Arduino IDE
2. Ve a **File → Preferences**
3. En **"Additional boards manager URLs"** añade:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Click **OK**

### Paso 2: Instalar el Board ESP32

1. Ve a **Tools → Board → Boards Manager**
2. Busca **"esp32"**
3. Instala **"esp32 by Espressif Systems"** (versión 2.x o 3.x)

### Paso 3: Seleccionar la Placa

1. **Tools → Board → esp32 → AI Thinker ESP32-CAM**

### Paso 4: Configuración Recomendada

| Opción | Valor |
|--------|-------|
| Board | AI Thinker ESP32-CAM |
| CPU Frequency | 240MHz (WiFi/BT) |
| Flash Frequency | 80MHz |
| Flash Mode | QIO |
| Partition Scheme | Huge APP (3MB No OTA) |
| Upload Speed | 115200 |

---

## Instalación de Librerías

Ve a **Sketch → Include Library → Manage Libraries** e instala:

| Librería | Autor | Descripción |
|----------|-------|-------------|
| Adafruit GFX Library | Adafruit | Gráficos base |
| Adafruit ST7735 and ST7789 Library | Adafruit | Driver pantalla ST7735 |
| JPEGDEC | Larry Bank (bitbank2) | Decodificador JPEG |

---

## Configuración del Código

### Editar wallbot_display.ino

Abre el archivo `wallbot_display/wallbot_display.ino` y modifica estas líneas:

```cpp
// Credenciales WiFi
const char* WIFI_SSID = "TU_WIFI_SSID";
const char* WIFI_PASSWORD = "TU_WIFI_PASSWORD";

// Servidor WallBot (IP de tu PC o NAS)
const char* SERVER_HOST = "192.168.1.XXX";
const int SERVER_PORT = 9500;

// Intervalo de actualización (milisegundos)
const unsigned long POLL_INTERVAL_MS = 30000;  // 30 segundos
```

### Parámetros Configurables

| Parámetro | Descripción | Valor por Defecto |
|-----------|-------------|-------------------|
| WIFI_SSID | Nombre de tu red WiFi | - |
| WIFI_PASSWORD | Contraseña WiFi | - |
| SERVER_HOST | IP del servidor WallBot | 192.168.1.41 |
| SERVER_PORT | Puerto del servidor | 9500 |
| POLL_INTERVAL_MS | Intervalo de actualización | 30000 (30s) |

---

## Programar la ESP32-CAM

La ESP32-CAM no tiene USB integrado, necesitas un programador USB-TTL.

### Modo de Programación (Flash Mode)

Para subir código, la ESP32-CAM debe estar en **modo flash**:

```
┌─────────────────────────────────────────────┐
│                                             │
│   MODO FLASH: GPIO0 conectado a GND         │
│                                             │
│   ESP32-CAM                                 │
│   ┌─────────┐                               │
│   │  GPIO0  │──┐                            │
│   │         │  │◄── Jumper/Cable            │
│   │   GND   │──┘                            │
│   └─────────┘                               │
│                                             │
└─────────────────────────────────────────────┘
```

### Modo de Ejecución Normal

Para ejecutar el programa, **quita el jumper**:

```
┌─────────────────────────────────────────────┐
│                                             │
│   MODO NORMAL: GPIO0 sin conectar           │
│                                             │
│   ESP32-CAM                                 │
│   ┌─────────┐                               │
│   │  GPIO0  │    (sin conexión)             │
│   │         │                               │
│   │   GND   │                               │
│   └─────────┘                               │
│                                             │
└─────────────────────────────────────────────┘
```

### Procedimiento Paso a Paso

#### 1. Preparar para Programar

1. **Desconecta** el USB-TTL del PC
2. **Conecta el jumper** entre GPIO0 y GND
3. **Conecta** el USB-TTL al PC
4. Espera a que Windows reconozca el dispositivo
5. Selecciona el puerto COM en **Tools → Port**

#### 2. Subir el Código

1. Click en **Upload** (flecha →) en Arduino IDE
2. Espera a que aparezca **"Connecting........"**
3. **Presiona el botón RST** en la ESP32-CAM
4. El código empezará a subirse

```
Connecting........_____
Chip is ESP32-D0WDQ6 (revision 1)
Writing at 0x00010000... (33%)
Writing at 0x00020000... (66%)
Writing at 0x00030000... (100%)
Hard resetting via RTS pin...
```

#### 3. Ejecutar el Programa

1. **Desconecta** el USB-TTL
2. **Quita el jumper** GPIO0-GND
3. **Reconecta** el USB-TTL (o usa fuente externa 5V)
4. El programa arrancará automáticamente

#### 4. Ver Logs (Opcional)

1. **Tools → Serial Monitor**
2. Configura velocidad a **115200 baud**
3. Verás mensajes de depuración:

```
=== WallBot ESP32 Display ===
Inicializando TFT...
Buffer: 30000 bytes
WiFi conectado!
IP: 192.168.1.45
GET http://192.168.1.41:9500/api/v1/screen.jpg
Recibido: 5547 bytes
Descarga completa
JPEG: 128x160
```

---

## Configuración del Servidor

### Requisitos del Servidor

El servidor WallBot debe estar ejecutándose en tu PC o NAS.

### Ejecutar el Servidor (Desarrollo)

```bash
# Desde la carpeta raíz del proyecto
cd wallbot

# Activar entorno virtual (si usas uno)
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Ejecutar servidor
python -m uvicorn src.server.app:app --host 0.0.0.0 --port 9500 --reload
```

### Verificar que el Servidor Funciona

Abre en un navegador:
```
http://192.168.1.XXX:9500
```

Deberías ver la interfaz web de WallBot.

### Endpoint de la ESP32

La ESP32 consulta este endpoint:
```
GET http://192.168.1.XXX:9500/api/v1/screen.jpg
```

Devuelve una imagen JPEG de 128x160 píxeles con el producto actual.

### Crear una Búsqueda

1. Abre la web: `http://192.168.1.XXX:9500`
2. Click en **"Nueva Búsqueda"**
3. Introduce los términos de búsqueda
4. La ESP32 mostrará los productos encontrados

---

## Solución de Problemas

### "Failed to connect to ESP32"

| Causa | Solución |
|-------|----------|
| GPIO0 no está a GND | Verifica el jumper GPIO0-GND |
| No presionaste RST | Presiona RST cuando veas "Connecting..." |
| TX/RX cruzados | Intercambia TX↔RX en las conexiones |
| Puerto incorrecto | Selecciona el puerto COM correcto |

### Pantalla Negra / No Muestra Nada

| Causa | Solución |
|-------|----------|
| Conexiones sueltas | Verifica todas las conexiones |
| Librería mal configurada | Reinstala las librerías Adafruit |
| RST mal conectado | Conecta RST a 3.3V |

### WiFi No Conecta

| Causa | Solución |
|-------|----------|
| SSID/Password incorrectos | Verifica mayúsculas/minúsculas |
| WiFi 5GHz | ESP32 solo soporta 2.4GHz |
| Señal débil | Acerca la ESP32 al router |

### "Servidor No Disponible"

| Causa | Solución |
|-------|----------|
| Servidor no ejecutándose | Inicia el servidor WallBot |
| IP incorrecta | Verifica la IP en el código |
| Firewall | Permite el puerto 9500 en el firewall |
| Red diferente | ESP32 y servidor deben estar en la misma red |

### Pantalla con Poco Brillo

- El backlight está en GPIO0 con PWM
- Verifica que LED/BLK esté conectado a GPIO0
- El código configura brillo máximo (255)

### LED Flash de ESP32-CAM Encendido

- No uses GPIO4 para el backlight
- GPIO4 es el LED del flash
- Usa GPIO0 para el backlight

### "Brownout detector was triggered"

- Fuente de alimentación insuficiente
- Usa una fuente de 5V con al menos 500mA
- No uses hubs USB sin alimentación

---

## Estructura de Archivos

```
esp32/
├── README.md                 # Este archivo
├── wallbot_display/
│   └── wallbot_display.ino   # Código principal
├── test_adafruit/
│   └── test_adafruit.ino     # Test básico de pantalla
└── test_brightness/
    └── test_brightness.ino   # Test de brillo PWM
```

---

## Diagrama Completo de Conexiones

```
┌─────────────────────────────────────────────────────────────┐
│                        PROTOBOARD                           │
│                                                             │
│  USB-TTL           ESP32-CAM              TFT ST7735        │
│ ┌───────┐         ┌─────────┐            ┌──────────┐       │
│ │       │         │         │            │          │       │
│ │  GND  ├────────►│ GND     │◄───────────┤ GND      │       │
│ │       │         │         │            │          │       │
│ │  5V   ├────────►│ 5V      │            │          │       │
│ │       │         │         │            │          │       │
│ │  TX   ├────────►│ U0R     │    3.3V───►│ VCC      │       │
│ │       │         │         │            │          │       │
│ │  RX   ├────────►│ U0T     │    3.3V───►│ RST      │       │
│ │       │         │         │            │          │       │
│ └───────┘         │  GPIO15 ├───────────►│ CS       │       │
│                   │         │            │          │       │
│                   │  GPIO2  ├───────────►│ DC/A0    │       │
│                   │         │            │          │       │
│                   │  GPIO13 ├───────────►│ SDA/MOSI │       │
│                   │         │            │          │       │
│                   │  GPIO14 ├───────────►│ SCL/SCK  │       │
│                   │         │            │          │       │
│                   │  GPIO0  ├───────────►│ LED/BLK  │       │
│                   │         │            │          │       │
│  JUMPER           │  GPIO0  │            └──────────┘       │
│  (solo flash)     │    │    │                               │
│                   │   GND◄──┘                               │
│                   │         │                               │
│                   └─────────┘                               │
│                       │                                     │
│                     [RST]                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Especificaciones Técnicas

| Parámetro | Valor |
|-----------|-------|
| Resolución pantalla | 128 x 160 píxeles |
| Formato imagen | JPEG baseline |
| Tamaño imagen | ~5-10 KB |
| Intervalo polling | 30 segundos (configurable) |
| Timeout servidor | 10 segundos |
| WiFi | 2.4 GHz (802.11 b/g/n) |
| Alimentación | 5V / 500mA mínimo |

---

## Licencia

Este proyecto es parte de WallBot.
