# FORK PLAN: Wallbot → API HTTP + Web UI para ESP32

> **Versión:** 1.0
> **Fecha:** 2026-01-25
> **Objetivo:** Eliminar Telegram y crear un sistema HTTP con renderizado de imágenes para ESP32

---

## Tabla de Contenidos

1. [Resumen del Repositorio Original](#1-resumen-del-repositorio-original)
2. [Arquitectura Objetivo del Fork](#2-arquitectura-objetivo-del-fork)
3. [Modelo de Datos](#3-modelo-de-datos)
4. [Especificación de la API HTTP](#4-especificación-de-la-api-http)
5. [Especificación de Renderizado de Imagen (ESP32)](#5-especificación-de-renderizado-de-imagen-esp32)
6. [Configuración y Variables de Entorno](#6-configuración-y-variables-de-entorno)
7. [Guía de Ejecución Paso a Paso](#7-guía-de-ejecución-paso-a-paso)

---

## 1. Resumen del Repositorio Original

### 1.1 Descripción General

El proyecto original es un bot de Telegram (`wallbot`) que monitoriza búsquedas en Wallapop y notifica al usuario cuando aparecen nuevos productos o bajan los precios.

**Versión actual:** 2.0.3
**Stack:** Python 3.8, SQLite, PyTelegramBotAPI

### 1.2 Estructura de Módulos Original

```
src/wallbot/
├── config/
│   ├── settings.py      # Variables de entorno (BOT_TOKEN, paths)
│   └── constants.py     # Intervalos, emojis, timeouts
├── database/
│   ├── models.py        # ChatSearch, Item (dataclasses)
│   └── db_helper.py     # Operaciones SQLite
├── telegram/            # ⚠️ ELIMINAR COMPLETAMENTE
│   ├── bot.py           # Creación del bot, polling
│   ├── handlers.py      # Comandos /add, /del, /lis
│   └── notifications.py # Envío de mensajes
├── wallapop/
│   ├── api_client.py    # Cliente HTTP para API Wallapop
│   └── monitor.py       # Scheduler + deduplicación
└── utils/
    ├── logger.py        # Configuración de logging
    └── version.py       # Lectura de VERSION
```

### 1.3 Partes Acopladas a Telegram (A ELIMINAR)

| Archivo | Función | Dependencia |
|---------|---------|-------------|
| `telegram/bot.py` | Crea instancia de TeleBot | `PyTelegramBotAPI`, `BOT_TOKEN` |
| `telegram/handlers.py` | Comandos `/add`, `/del`, `/lis` | `telebot.types.Message` |
| `telegram/notifications.py` | Envía alertas via Telegram API | `requests` a `api.telegram.org` |
| `main.py` | Bootstrap completo | `create_bot()`, `recovery()` |
| `config/settings.py` | `BOT_TOKEN` obligatorio | Variable de entorno |
| `config/constants.py` | Emojis para mensajes | Solo usado en notificaciones |

### 1.4 Partes Reutilizables (A CONSERVAR)

| Módulo | Descripción | Estado |
|--------|-------------|--------|
| `wallapop/api_client.py` | Cliente HTTP para buscar en Wallapop | ✅ Reutilizable 100% |
| `wallapop/monitor.py` | Lógica de monitorización y deduplicación | ✅ Adaptar (quitar notificaciones Telegram) |
| `database/db_helper.py` | Operaciones CRUD SQLite | ✅ Reutilizable, ampliar |
| `database/models.py` | Modelos `ChatSearch`, `Item` | ✅ Adaptar nombres (search_id vs chat_id) |
| `utils/logger.py` | Configuración de logging | ✅ Reutilizable 100% |
| `utils/version.py` | Lectura de versión | ✅ Reutilizable 100% |

### 1.5 Flujo de Datos Original

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Usuario    │ ──── │   Telegram   │ ──── │   Wallbot    │
│  (Telegram)  │      │   Bot API    │      │   (Python)   │
└──────────────┘      └──────────────┘      └──────────────┘
                                                   │
                                                   ▼
                            ┌──────────────────────────────────┐
                            │         Monitor Thread           │
                            │   (cada 5 min busca en Wallapop) │
                            └──────────────────────────────────┘
                                           │
                      ┌────────────────────┼────────────────────┐
                      ▼                    ▼                    ▼
               ┌───────────┐        ┌───────────┐        ┌───────────┐
               │  SQLite   │        │ Wallapop  │        │ Telegram  │
               │    DB     │        │   API     │        │   API     │
               └───────────┘        └───────────┘        └───────────┘
```

---

## 2. Arquitectura Objetivo del Fork

### 2.1 Visión General

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NAS Synology (Docker)                        │
│                                                                     │
│  ┌───────────────┐     ┌───────────────┐     ┌───────────────┐     │
│  │   FastAPI     │     │   Watcher     │     │   Renderer    │     │
│  │   (HTTP)      │     │   (Scheduler) │     │   (Pillow)    │     │
│  │   :8000       │     │   cada 5 min  │     │   128x160 JPG │     │
│  └───────┬───────┘     └───────┬───────┘     └───────┬───────┘     │
│          │                     │                     │             │
│          └─────────────────────┼─────────────────────┘             │
│                                │                                    │
│                         ┌──────┴──────┐                            │
│                         │   SQLite    │                            │
│                         │   /data/    │                            │
│                         └─────────────┘                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
         │                        │
         │ HTTP                   │ HTTP
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│    Navegador    │      │     ESP32       │
│    Web UI       │      │   TFT 128x160   │
│  (Jinja2 HTML)  │      │  polling /jpg   │
└─────────────────┘      └─────────────────┘
```

### 2.2 Módulos del Fork

| Módulo | Responsabilidad | Tecnología |
|--------|-----------------|------------|
| **server** | Servidor HTTP, API REST, Web UI | FastAPI + Uvicorn + Jinja2 |
| **watcher** | Ejecutar búsquedas periódicas | APScheduler / threading |
| **renderer** | Generar imágenes 128x160 JPG | Pillow |
| **database** | Persistencia SQLite | sqlite3 (existente) |
| **wallapop** | Cliente API Wallapop | requests (existente) |

### 2.3 Estructura de Directorios Propuesta

```
src/
├── __init__.py
├── server/
│   ├── __init__.py
│   ├── app.py              # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py       # Endpoints API REST
│   ├── web/
│   │   ├── __init__.py
│   │   └── views.py        # Rutas Web UI
│   └── templates/          # Jinja2 templates
│       ├── base.html
│       ├── index.html
│       ├── search_form.html
│       └── search_preview.html
├── watcher/
│   ├── __init__.py
│   └── scheduler.py        # Monitorización periódica
├── renderer/
│   ├── __init__.py
│   ├── image_generator.py  # Renderizado 128x160
│   └── fonts/              # Fuentes TTF
│       └── DejaVuSans.ttf
├── database/               # (modificado del original)
│   ├── __init__.py
│   ├── models.py           # Search, Item
│   └── db_helper.py        # CRUD SQLite
├── wallapop/               # (sin cambios)
│   ├── __init__.py
│   ├── api_client.py
│   └── monitor.py          # Adaptar sin Telegram
├── config/
│   ├── __init__.py
│   └── settings.py         # Variables de entorno
└── utils/
    ├── __init__.py
    ├── logger.py
    └── version.py

data/                       # Volumen persistente
├── db.sqlite               # Base de datos
├── cache/                  # Cache de imágenes Wallapop
│   └── {item_id}.jpg
└── renders/                # Imágenes renderizadas ESP32
    └── {search_id}.jpg
```

### 2.4 Flujo de Datos Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FLUJO DE DATOS                                 │
└─────────────────────────────────────────────────────────────────────────────┘

1. CONFIGURACIÓN (Usuario via Web UI)
   ─────────────────────────────────────────────────────────────────────────
   Navegador ──POST /api/v1/searches──► FastAPI ──INSERT──► SQLite
                                            │
                                            └──► Trigger: Generar render inicial

2. MONITORIZACIÓN (Watcher automático cada N minutos)
   ─────────────────────────────────────────────────────────────────────────
   Scheduler ──cada 5 min──► Para cada búsqueda activa:
       │
       ├──► WallapopClient.search_items(search)
       │         │
       │         └──► GET api.wallapop.com/api/v3/search?keywords=...
       │
       ├──► Para cada ítem nuevo (no duplicado):
       │         │
       │         ├──► INSERT en SQLite (item)
       │         ├──► Descargar imagen del producto a cache/
       │         └──► Actualizar last_item_id en búsqueda
       │
       └──► Trigger: Re-renderizar imagen si hay nuevo ítem

3. RENDERIZADO (Cuando hay nuevo ítem)
   ─────────────────────────────────────────────────────────────────────────
   Renderer ──► Lee último ítem de la búsqueda
       │
       ├──► Carga imagen del cache/ (o descarga si no existe)
       ├──► Recorta/escala a zona superior (128x~100 px)
       ├──► Dibuja texto en zona inferior:
       │         • Precio (grande, negrita)
       │         • Título (truncado)
       │         • Ciudad / Tiempo relativo
       │
       └──► Guarda en renders/{search_id}.jpg (128x160 JPG baseline)

4. CONSUMO ESP32 (Polling cada X segundos)
   ─────────────────────────────────────────────────────────────────────────
   ESP32 ──GET /api/v1/searches/{id}/screen.jpg──► FastAPI
       │                                               │
       │                                               └──► Lee renders/{id}.jpg
       │
       └──► Muestra en pantalla TFT SPI

```

---

## 3. Modelo de Datos

### 3.1 Diagrama Entidad-Relación

```
┌─────────────────────────────────────┐
│              search                 │
├─────────────────────────────────────┤
│ id            INTEGER PRIMARY KEY   │
│ name          TEXT NOT NULL         │  ← Nombre descriptivo
│ keywords      TEXT NOT NULL         │  ← Términos de búsqueda
│ min_price     INTEGER               │  ← Precio mínimo (cents)
│ max_price     INTEGER               │  ← Precio máximo (cents)
│ category_ids  TEXT                  │  ← IDs separados por coma
│ distance      INTEGER DEFAULT 400   │  ← Radio en km
│ order_by      TEXT DEFAULT 'newest' │  ← Ordenación
│ active        INTEGER DEFAULT 1     │  ← 1=activo, 0=pausado
│ last_item_id  TEXT                  │  ← ID del último ítem visto
│ created_at    TEXT                  │  ← ISO 8601 timestamp
│ updated_at    TEXT                  │  ← ISO 8601 timestamp
└─────────────────────────────────────┘
                 │
                 │ 1:N
                 ▼
┌─────────────────────────────────────┐
│               item                  │
├─────────────────────────────────────┤
│ id            INTEGER PRIMARY KEY   │  ← Auto-increment interno
│ wallapop_id   TEXT NOT NULL         │  ← ID de Wallapop
│ search_id     INTEGER NOT NULL      │  ← FK → search.id
│ title         TEXT                  │
│ price         INTEGER               │  ← Precio en cents
│ price_history TEXT                  │  ← "8000 < 10000 < 12000"
│ web_slug      TEXT                  │  ← Para construir URL
│ image_url     TEXT                  │  ← URL imagen original
│ location      TEXT                  │  ← Ciudad/zona
│ seller_id     TEXT                  │  ← ID vendedor Wallapop
│ first_seen    TEXT                  │  ← ISO 8601
│ last_updated  TEXT                  │  ← ISO 8601
│ notified      INTEGER DEFAULT 0     │  ← 1=ya procesado
├─────────────────────────────────────┤
│ UNIQUE(wallapop_id, search_id)      │  ← Evita duplicados
│ FOREIGN KEY(search_id) → search(id) │
└─────────────────────────────────────┘
```

### 3.2 Script de Creación de Tablas

```sql
-- Tabla de búsquedas
CREATE TABLE IF NOT EXISTS search (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    keywords      TEXT NOT NULL,
    min_price     INTEGER,
    max_price     INTEGER,
    category_ids  TEXT,
    distance      INTEGER DEFAULT 400,
    order_by      TEXT DEFAULT 'newest',
    active        INTEGER DEFAULT 1,
    last_item_id  TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

-- Tabla de ítems encontrados
CREATE TABLE IF NOT EXISTS item (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    wallapop_id   TEXT NOT NULL,
    search_id     INTEGER NOT NULL,
    title         TEXT,
    price         INTEGER,
    price_history TEXT,
    web_slug      TEXT,
    image_url     TEXT,
    location      TEXT,
    seller_id     TEXT,
    first_seen    TEXT DEFAULT (datetime('now')),
    last_updated  TEXT DEFAULT (datetime('now')),
    notified      INTEGER DEFAULT 0,
    UNIQUE(wallapop_id, search_id),
    FOREIGN KEY(search_id) REFERENCES search(id) ON DELETE CASCADE
);

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_item_search ON item(search_id);
CREATE INDEX IF NOT EXISTS idx_item_wallapop ON item(wallapop_id);
CREATE INDEX IF NOT EXISTS idx_search_active ON search(active);
```

### 3.3 Gestión de "Último Visto"

El campo `search.last_item_id` almacena el `wallapop_id` del último ítem procesado.

**Flujo de actualización:**

1. El watcher obtiene resultados de Wallapop (ordenados por `newest`)
2. Para cada ítem en la respuesta:
   - Si `wallapop_id` ya existe en `item` para este `search_id` → skip
   - Si es nuevo → INSERT en `item`
3. Si hubo al menos un ítem nuevo:
   - Actualizar `search.last_item_id` con el primer ítem (más reciente)
   - Trigger de re-renderizado

**Nota:** La deduplicación se hace por `(wallapop_id, search_id)`, permitiendo que el mismo producto aparezca en múltiples búsquedas.

---

## 4. Especificación de la API HTTP

### 4.1 Endpoints Base

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/searches` | Listar búsquedas |
| POST | `/api/v1/searches` | Crear búsqueda |
| GET | `/api/v1/searches/{id}` | Obtener búsqueda |
| PUT | `/api/v1/searches/{id}` | Actualizar búsqueda |
| DELETE | `/api/v1/searches/{id}` | Eliminar búsqueda |
| GET | `/api/v1/searches/{id}/items` | Ítems de una búsqueda |
| GET | `/api/v1/searches/{id}/latest` | Último ítem encontrado |
| GET | `/api/v1/searches/{id}/screen.jpg` | Imagen renderizada |

### 4.2 Detalle de Endpoints

#### GET /api/v1/health

Health check para monitorización.

**Response 200:**
```json
{
  "status": "ok",
  "version": "3.0.0",
  "uptime_seconds": 3600,
  "database": "connected",
  "watcher": "running"
}
```

---

#### GET /api/v1/searches

Listar todas las búsquedas.

**Query Parameters:**
- `active` (optional): `true` | `false` - Filtrar por estado

**Response 200:**
```json
{
  "searches": [
    {
      "id": 1,
      "name": "Raspberry Pi 4",
      "keywords": "raspberry pi 4",
      "min_price": 3000,
      "max_price": 8000,
      "category_ids": null,
      "distance": 400,
      "order_by": "newest",
      "active": true,
      "last_item_id": "abc123",
      "items_count": 15,
      "created_at": "2026-01-20T10:30:00Z",
      "updated_at": "2026-01-25T14:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### POST /api/v1/searches

Crear nueva búsqueda.

**Request Body:**
```json
{
  "name": "Nintendo Switch",
  "keywords": "nintendo switch",
  "min_price": 15000,
  "max_price": 25000,
  "category_ids": "12900",
  "distance": 200,
  "active": true
}
```

**Validaciones:**
- `name`: requerido, 1-100 caracteres
- `keywords`: requerido, 1-200 caracteres
- `min_price`: opcional, >= 0 (en céntimos)
- `max_price`: opcional, >= min_price (en céntimos)
- `category_ids`: opcional, string de IDs separados por coma
- `distance`: opcional, 1-500 km, default 400
- `active`: opcional, default true

**Response 201:**
```json
{
  "id": 2,
  "name": "Nintendo Switch",
  "keywords": "nintendo switch",
  "min_price": 15000,
  "max_price": 25000,
  "category_ids": "12900",
  "distance": 200,
  "order_by": "newest",
  "active": true,
  "last_item_id": null,
  "created_at": "2026-01-25T15:00:00Z",
  "updated_at": "2026-01-25T15:00:00Z"
}
```

**Response 400 (validación):**
```json
{
  "error": "validation_error",
  "message": "min_price must be less than or equal to max_price",
  "field": "min_price"
}
```

---

#### GET /api/v1/searches/{id}

Obtener detalles de una búsqueda.

**Response 200:**
```json
{
  "id": 1,
  "name": "Raspberry Pi 4",
  "keywords": "raspberry pi 4",
  "min_price": 3000,
  "max_price": 8000,
  "category_ids": null,
  "distance": 400,
  "order_by": "newest",
  "active": true,
  "last_item_id": "abc123",
  "items_count": 15,
  "latest_item": {
    "wallapop_id": "abc123",
    "title": "Raspberry Pi 4 8GB nuevo",
    "price": 6500,
    "location": "Madrid",
    "first_seen": "2026-01-25T12:30:00Z"
  },
  "created_at": "2026-01-20T10:30:00Z",
  "updated_at": "2026-01-25T14:00:00Z"
}
```

**Response 404:**
```json
{
  "error": "not_found",
  "message": "Search with id 99 not found"
}
```

---

#### PUT /api/v1/searches/{id}

Actualizar búsqueda existente.

**Request Body:** (campos opcionales)
```json
{
  "name": "Raspberry Pi 4 8GB",
  "active": false
}
```

**Response 200:** Objeto search actualizado

---

#### DELETE /api/v1/searches/{id}

Eliminar búsqueda y sus ítems asociados.

**Response 204:** Sin contenido

**Response 404:** Si no existe

---

#### GET /api/v1/searches/{id}/items

Listar ítems encontrados para una búsqueda.

**Query Parameters:**
- `limit` (optional): default 50, max 200
- `offset` (optional): default 0

**Response 200:**
```json
{
  "items": [
    {
      "id": 42,
      "wallapop_id": "abc123",
      "title": "Raspberry Pi 4 8GB nuevo",
      "price": 6500,
      "price_history": null,
      "web_slug": "raspberry-pi-4-8gb-nuevo-123456",
      "image_url": "https://cdn.wallapop.com/images/...",
      "location": "Madrid",
      "first_seen": "2026-01-25T12:30:00Z",
      "wallapop_url": "https://es.wallapop.com/item/raspberry-pi-4-8gb-nuevo-123456"
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

---

#### GET /api/v1/searches/{id}/latest

Obtener el último ítem encontrado.

**Response 200:**
```json
{
  "wallapop_id": "abc123",
  "title": "Raspberry Pi 4 8GB nuevo",
  "price": 6500,
  "price_formatted": "65,00 €",
  "price_history": null,
  "web_slug": "raspberry-pi-4-8gb-nuevo-123456",
  "image_url": "https://cdn.wallapop.com/images/...",
  "location": "Madrid",
  "first_seen": "2026-01-25T12:30:00Z",
  "time_ago": "hace 2 horas",
  "wallapop_url": "https://es.wallapop.com/item/raspberry-pi-4-8gb-nuevo-123456"
}
```

**Response 404:** Si no hay ítems

---

#### GET /api/v1/searches/{id}/screen.jpg

Imagen renderizada lista para ESP32.

**Response 200:**
- Content-Type: `image/jpeg`
- Content-Length: tamaño en bytes
- Cache-Control: `no-cache` (siempre última versión)
- Body: imagen binaria 128x160 JPG

**Response 404:** Si búsqueda no existe o no hay ítems (devuelve imagen "SIN DATOS")

---

## 5. Especificación de Renderizado de Imagen (ESP32)

### 5.1 Requisitos Técnicos

| Parámetro | Valor |
|-----------|-------|
| **Resolución** | 128 x 160 píxeles (exactos) |
| **Formato** | JPEG baseline (no progresivo) |
| **Calidad** | 85% (balance tamaño/calidad) |
| **Tamaño máximo** | ~15 KB |
| **Color** | RGB 24-bit |

### 5.2 Layout de la Imagen

```
┌──────────────────────────┐
│                          │  ▲
│                          │  │
│    IMAGEN PRODUCTO       │  │ ~100 px
│    (cover/crop)          │  │
│                          │  │
│                          │  ▼
├──────────────────────────┤
│  65,00 €                 │  ▲
│  Raspberry Pi 4 8GB...   │  │ ~60 px
│  Madrid · hace 2h        │  ▼
└──────────────────────────┘
   ◄────── 128 px ───────►
```

### 5.3 Especificación de Zonas

#### Zona Superior: Imagen del Producto

| Parámetro | Valor |
|-----------|-------|
| Posición Y | 0 |
| Altura | 100 px |
| Ancho | 128 px |
| Modo | Cover (recortar para llenar) |
| Fallback | Gris #CCCCCC con icono "?" |

**Algoritmo de recorte (cover):**
1. Calcular ratio de aspecto de la imagen original
2. Escalar manteniendo ratio para que el lado menor = dimensión objetivo
3. Centrar y recortar el exceso

#### Zona Inferior: Información de Texto

| Línea | Contenido | Fuente | Tamaño | Color | Y |
|-------|-----------|--------|--------|-------|---|
| 1 | Precio | DejaVu Sans Bold | 18 px | #000000 | 104 |
| 2 | Título | DejaVu Sans | 12 px | #333333 | 126 |
| 3 | Ubicación · Tiempo | DejaVu Sans | 10 px | #666666 | 144 |

**Márgenes:**
- Margen izquierdo: 4 px
- Margen derecho: 4 px
- Ancho útil texto: 120 px

**Truncado de texto:**
- Título: máximo ~18 caracteres + "..."
- Ubicación: máximo ~10 caracteres

### 5.4 Formato del Precio

```python
# Precio viene en céntimos (integer)
price_cents = 6500
price_formatted = f"{price_cents / 100:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
# Resultado: "65,00 €"
```

### 5.5 Formato del Tiempo Relativo

| Diferencia | Formato |
|------------|---------|
| < 1 minuto | "ahora" |
| < 60 minutos | "hace Xm" |
| < 24 horas | "hace Xh" |
| < 7 días | "hace Xd" |
| >= 7 días | "hace X sem" |

### 5.6 Imagen de Error "SIN DATOS"

Cuando no hay ítems o hay un error:

```
┌──────────────────────────┐
│                          │
│         ┌───┐            │
│         │ ? │            │
│         └───┘            │
│                          │
├──────────────────────────┤
│  SIN DATOS               │
│  No hay productos        │
│  Esperando...            │
└──────────────────────────┘
```

- Fondo: #F0F0F0
- Texto: #666666
- Icono: simple signo de interrogación

### 5.7 Implementación con Pillow

```python
from PIL import Image, ImageDraw, ImageFont
import io

def render_screen_image(item: dict, search_name: str) -> bytes:
    """
    Renderiza imagen 128x160 para ESP32.

    Args:
        item: Diccionario con datos del ítem
        search_name: Nombre de la búsqueda

    Returns:
        bytes: Imagen JPEG en memoria
    """
    # Crear canvas
    img = Image.new('RGB', (128, 160), color='#FFFFFF')
    draw = ImageDraw.Draw(img)

    # Cargar fuentes
    font_price = ImageFont.truetype('fonts/DejaVuSans-Bold.ttf', 18)
    font_title = ImageFont.truetype('fonts/DejaVuSans.ttf', 12)
    font_meta = ImageFont.truetype('fonts/DejaVuSans.ttf', 10)

    # 1. Zona superior: imagen del producto
    product_img = load_and_crop_image(item['image_url'], 128, 100)
    img.paste(product_img, (0, 0))

    # 2. Línea separadora
    draw.line([(0, 100), (128, 100)], fill='#DDDDDD', width=1)

    # 3. Precio
    price_text = format_price(item['price'])
    draw.text((4, 104), price_text, font=font_price, fill='#000000')

    # 4. Título (truncado)
    title_text = truncate_text(item['title'], 18)
    draw.text((4, 126), title_text, font=font_title, fill='#333333')

    # 5. Ubicación y tiempo
    meta_text = f"{item['location'][:10]} · {format_time_ago(item['first_seen'])}"
    draw.text((4, 144), meta_text, font=font_meta, fill='#666666')

    # Exportar a JPEG
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85, optimize=True)
    buffer.seek(0)
    return buffer.getvalue()
```

---

## 6. Configuración y Variables de Entorno

### 6.1 Variables de Entorno

| Variable | Requerido | Default | Descripción |
|----------|-----------|---------|-------------|
| `WALLBOT_ENV` | No | `production` | Entorno: `development` o `production` |
| `WALLBOT_HOST` | No | `0.0.0.0` | Host del servidor HTTP |
| `WALLBOT_PORT` | No | `8000` | Puerto del servidor HTTP |
| `WALLBOT_DATA_DIR` | No | `/data` | Directorio de datos persistentes |
| `WALLBOT_LOG_LEVEL` | No | `INFO` | Nivel de logging |
| `WALLBOT_SEARCH_INTERVAL` | No | `300` | Intervalo de búsqueda en segundos |
| `WALLBOT_WALLAPOP_TIMEOUT` | No | `30` | Timeout para API Wallapop |

### 6.2 Rutas Derivadas

```python
# En settings.py
DATA_DIR = os.getenv('WALLBOT_DATA_DIR', '/data')

DATABASE_PATH = os.path.join(DATA_DIR, 'db.sqlite')
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
RENDERS_DIR = os.path.join(DATA_DIR, 'renders')
LOG_PATH = os.path.join(DATA_DIR, 'logs', 'wallbot.log')
```

### 6.3 Configuración por Entorno

**Desarrollo (`WALLBOT_ENV=development`):**
```
WALLBOT_DATA_DIR=./data
WALLBOT_LOG_LEVEL=DEBUG
WALLBOT_SEARCH_INTERVAL=60  # 1 minuto para pruebas
```

**Producción (`WALLBOT_ENV=production`):**
```
WALLBOT_DATA_DIR=/data
WALLBOT_LOG_LEVEL=INFO
WALLBOT_SEARCH_INTERVAL=300  # 5 minutos
```

### 6.4 Archivo .env de Ejemplo

```env
# .env.example - Copiar a .env y ajustar

# Entorno
WALLBOT_ENV=development

# Servidor
WALLBOT_HOST=0.0.0.0
WALLBOT_PORT=8000

# Datos
WALLBOT_DATA_DIR=./data

# Logging
WALLBOT_LOG_LEVEL=DEBUG

# Watcher
WALLBOT_SEARCH_INTERVAL=60

# Wallapop
WALLBOT_WALLAPOP_TIMEOUT=30
```

---

## 7. Guía de Ejecución Paso a Paso

### 7.1 Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes)
- Docker (opcional, para producción)

### 7.2 Modo Desarrollo (Terminal)

#### Paso 1: Clonar y Preparar

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/wallbot.git
cd wallbot

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

#### Paso 2: Instalar Dependencias

```bash
pip install -r requirements.txt
```

#### Paso 3: Configurar Entorno

```bash
# Copiar configuración de ejemplo
cp .env.example .env

# Editar .env con tus preferencias
# Asegurar que WALLBOT_ENV=development
```

#### Paso 4: Crear Directorios de Datos

```bash
mkdir -p data/cache data/renders data/logs
```

#### Paso 5: Ejecutar

```bash
# Opción A: Módulo Python
python -m server.app

# Opción B: Uvicorn directamente
uvicorn src.server.app:app --host 0.0.0.0 --port 8000 --reload
```

#### Paso 6: Verificar

```bash
# En otra terminal
curl http://localhost:8000/api/v1/health

# O abrir navegador en http://localhost:8000
```

### 7.3 Modo Docker

#### Paso 1: Construir Imagen

```bash
docker build -t wallbot:latest .
```

#### Paso 2: Ejecutar Contenedor

```bash
docker run -d \
  --name wallbot \
  -p 8000:8000 \
  -v $(pwd)/data:/data \
  -e WALLBOT_ENV=production \
  -e WALLBOT_LOG_LEVEL=INFO \
  --restart unless-stopped \
  wallbot:latest
```

#### Paso 3: Verificar

```bash
# Logs
docker logs -f wallbot

# Health check
curl http://localhost:8000/api/v1/health
```

### 7.4 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  wallbot:
    build: .
    container_name: wallbot
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
    environment:
      - WALLBOT_ENV=production
      - WALLBOT_LOG_LEVEL=INFO
      - WALLBOT_SEARCH_INTERVAL=300
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Comandos:**

```bash
# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down

# Reconstruir
docker-compose up -d --build
```

### 7.5 Notas Específicas para Synology NAS

#### Requisitos

- DSM 7.0 o superior
- Container Manager (Docker) instalado
- Carpeta compartida para datos (ej: `/volume1/docker/wallbot`)

#### Configuración Recomendada

1. **Crear carpeta de datos:**
   - File Station → `/volume1/docker/wallbot/data`

2. **Permisos:**
   - Usuario: `root` o usuario Docker con UID/GID conocido
   - Permisos: lectura/escritura en carpeta data

3. **Configuración de contenedor en Container Manager:**

   ```
   Nombre: wallbot
   Imagen: wallbot:latest (o desde Docker Hub)

   Puerto local: 8000
   Puerto contenedor: 8000

   Volumen:
     /volume1/docker/wallbot/data -> /data

   Variables de entorno:
     WALLBOT_ENV=production
     WALLBOT_LOG_LEVEL=INFO
     TZ=Europe/Madrid

   Red: bridge

   Reinicio automático: Sí
   ```

4. **Acceso desde red local:**
   - URL: `http://IP_NAS:8000`
   - Ejemplo: `http://192.168.1.50:8000`

5. **Firewall (si está activado):**
   - Permitir puerto 8000 TCP desde red local

#### Diagnóstico de Problemas

```bash
# SSH al NAS
ssh admin@IP_NAS

# Ver logs del contenedor
docker logs wallbot

# Verificar permisos
ls -la /volume1/docker/wallbot/data

# Verificar conectividad
curl http://localhost:8000/api/v1/health
```

---

## Apéndice A: Categorías de Wallapop

Algunas categorías útiles:

| ID | Categoría |
|----|-----------|
| 12900 | Videojuegos y Consolas |
| 15245 | Informática y Electrónica |
| 16000 | Móviles y Telefonía |
| 17000 | Imagen, Sonido y Fotografía |
| 24200 | Deporte y Ocio |

---

## Apéndice B: Checklist de Fases

- [ ] **FASE 0:** Documentación (este archivo)
- [ ] **FASE 1:** Servidor HTTP básico sin Telegram
- [ ] **FASE 2:** CRUD de búsquedas + Web UI
- [ ] **FASE 3:** Integración Wallapop + Deduplicación
- [ ] **FASE 4:** Renderizado de imagen 128x160
- [ ] **FASE 5:** Dockerización final

---

## Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-01-25 | Versión inicial del plan |
