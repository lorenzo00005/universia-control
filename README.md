<div align="center">

# 🟢 Control Total WSP Web

**Todos tus números de WhatsApp en una sola bandeja.**
CRM autoalojado con equipo de operadores, pipeline de ventas y mensajes en tiempo real.

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![WAHA](https://img.shields.io/badge/WhatsApp-WAHA-25D366?logo=whatsapp&logoColor=white)
![Estado](https://img.shields.io/badge/estado-en%20desarrollo-orange)

</div>

> ⚠️ Proyecto en desarrollo, no afiliado a WhatsApp ni a Meta. Se conecta por QR mediante [WAHA](https://waha.devlike.pro), una vía **no oficial**: leé [Limitaciones](#limitaciones-conocidas) antes de usarlo con números importantes.

## ¿Qué es?

Si atendés clientes por WhatsApp con varios teléfonos, terminás saltando de celular en celular. **Control Total WSP Web** conecta todos esos números a un solo panel web donde tu equipo ve, responde y organiza todas las conversaciones, con los datos en **tu propio servidor**.

## Funciones

| | Función | Detalle |
|---|---|---|
| 💬 | **Chat unificado** | Conversaciones de todos los números juntas; filtro por número y "solo mías"; respuesta desde el panel; tildes de enviado / entregado / leído |
| ⚡ | **Tiempo real** | Los mensajes aparecen al instante (WebSocket con reconexión automática) |
| 📱 | **Gestión de números** | Crear instancias, escanear el QR desde el panel, ver el estado (conectado / esperando QR / caído), reiniciar y eliminar. Importa solo las sesiones ya existentes en WAHA |
| 🧲 | **Pipeline de ventas** | Tablero kanban (Nuevo → Contactado → Calificado → Propuesta → Ganado / Perdido); se mueve con arrastrar y soltar |
| 👥 | **Equipo** | Login con JWT, roles administrador / operador y asignación de conversaciones |
| 📊 | **Datos para reportes y Meta Ads** | Se guardan la hora del primer mensaje y de la primera respuesta, el `ctwa_clid` de anuncios Click-to-WhatsApp (si llega) y el historial de estados de cada sesión |
| 🩺 | **Diagnóstico** | `GET /webhooks/recent` muestra los últimos webhooks recibidos y los errores de procesamiento |

## Cómo funciona

```mermaid
flowchart LR
    T1[📱 Número 1] -- QR --> W
    T2[📱 Número 2] -- QR --> W
    T3[📱 Número 3] -- QR --> W
    TN[📱 ... Número 10, 20, N] -- QR --> W
    W["WAHA<br/>(motor GOWS)"] -- webhook --> B["Backend<br/>FastAPI"]
    B -- envío de mensajes --> W
    B <--> DB[("PostgreSQL")]
    B -- WebSocket --> F["Panel web<br/>React + nginx"]
    F -- REST --> B
```

**Sin límite de números:** podés conectar tantos como aguante tu servidor (cada sesión de WAHA consume memoria). Ejemplo con 10 números:

| Sesión | Etiqueta | Uso |
|---|---|---|
| `ventas1` – `ventas4` | Ventas 1 a 4 | Atención comercial |
| `soporte1` – `soporte3` | Soporte 1 a 3 | Postventa y reclamos |
| `campana1` – `campana3` | Campaña 1 a 3 | Anuncios Click-to-WhatsApp |

Todos aparecen juntos en el Chat; se filtran por número desde el panel.

**Mensaje entrante:** el cliente escribe → WAHA lo recibe → llama al webhook del backend → se guarda en Postgres → el backend lo emite por WebSocket → aparece en el panel de todos los operadores.

**Mensaje saliente:** el operador escribe en el panel → el backend lo envía por WAHA → se guarda y se emite → WAHA confirma la entrega y los tildes se actualizan.

El backend no habla con WhatsApp directamente sino a través de una **capa de proveedor** (`backend/app/services/providers.py`). Hoy el único proveedor es WAHA; la idea es sumar la Cloud API oficial de Meta para los números críticos sin tocar el resto.

| Servicio | Tecnología | Puerto |
|---|---|---|
| `frontend` | React + Vite + TypeScript, servido por nginx | 5173 |
| `backend` | FastAPI + SQLAlchemy | 8000 |
| `waha` | WAHA (WhatsApp HTTP API), motor GOWS | 3000 (solo local) |
| `postgres` | PostgreSQL 16 | interno |

## Puesta en marcha

**Requisitos:** Docker con Docker Compose y un teléfono con WhatsApp por cada número a vincular.

```bash
git clone https://github.com/lorenzo00005/control-total-wsp-web.git
cd control-total-wsp-web
cp .env.example .env        # cambiar TODAS las claves "cambiar-esto"
docker compose up -d --build
```

| URL | Qué es |
|---|---|
| http://localhost:5173 | **Panel** (usuario y contraseña: `ADMIN_EMAIL` / `ADMIN_PASSWORD` del `.env`) |
| http://localhost:8000/docs | Documentación interactiva de la API |
| http://localhost:3000/dashboard | Dashboard de WAHA |

> El administrador se crea solo la primera vez que arranca la base. Si cambiás `ADMIN_EMAIL` o `ADMIN_PASSWORD` después, hay que borrar los datos: `docker compose down -v`.

**Dashboard de WAHA:** al abrirlo por primera vez, en el panel *Workers* tocá el lápiz y pegá `WAHA_API_KEY` del `.env` para que pueda administrar las sesiones.

### Variables de entorno

| Variable | Para qué |
|---|---|
| `POSTGRES_USER` · `POSTGRES_PASSWORD` · `POSTGRES_DB` | Base de datos |
| `WAHA_API_KEY` | Clave de la API de WAHA |
| `WAHA_DASHBOARD_USERNAME` · `WAHA_DASHBOARD_PASSWORD` | Acceso al dashboard de WAHA |
| `WEBHOOK_SECRET` | Secreto en la URL del webhook que WAHA llama |
| `JWT_SECRET` | Firma de los tokens de sesión |
| `ADMIN_EMAIL` · `ADMIN_PASSWORD` | Primer usuario administrador |
| `CORS_ORIGINS` | Orígenes permitidos (solo desarrollo del frontend) |

## Conectar tu primer número

1. Abrí la pestaña **Números** → escribí un nombre de sesión (ej. `ventas1`) y una etiqueta → **Crear instancia**.
2. En el celular: WhatsApp → *Dispositivos vinculados* → *Vincular un dispositivo* → escaneá el QR.
3. El estado pasa a **Conectado** solo. Mandale un mensaje a ese número desde otro teléfono y aparece en **Chat**.
4. Repetí los pasos 1–3 por cada número extra (`ventas2`, `ventas3`, … `ventas10`): no hay límite en el software.

WAHA avisa al backend de cada sesión mediante un webhook global (`WHATSAPP_HOOK_URL` en `docker-compose.yml`), por eso también funcionan las sesiones creadas desde el dashboard de WAHA. Solo se capturan mensajes **nuevos**: no se importa el historial.

## API

Documentación completa en `/docs`. Lo principal:

| Endpoint | Función |
|---|---|
| `POST /auth/login` · `GET /auth/me` | Autenticación |
| `GET/POST /numbers` · `POST /numbers/sync` · `GET /numbers/{id}/qr` · `/status` · `POST /numbers/{id}/restart` · `DELETE /numbers/{id}` | Números de WhatsApp |
| `GET /conversations` · `GET/POST /conversations/{id}/messages` · `PATCH /conversations/{id}` · `POST /conversations/{id}/read` | Bandeja |
| `GET/POST /stages` | Etapas del pipeline |
| `GET /users` | Operadores |
| `POST /webhooks/waha/{secret}` · `GET /webhooks/recent` | Entrada de eventos de WAHA y diagnóstico |
| `WS /ws?token=` | Eventos en tiempo real |

## Estructura del proyecto

```
├── docker-compose.yml        # postgres + waha + backend + frontend
├── .env.example              # plantilla de configuración
├── backend/
│   ├── app/
│   │   ├── routers/          # un archivo por recurso
│   │   ├── services/         # proveedor de mensajería, ingesta de webhooks, hub de tiempo real
│   │   └── models.py · schemas.py · security.py · deps.py · main.py
│   └── tests/                # pytest
└── frontend/
    └── src/
        ├── pages/            # Chat, Pipeline, Numbers, Login
        └── hooks/            # useRealtime (WebSocket con reconexión)
```

## Desarrollo

```bash
# Backend (los tests usan SQLite en memoria)
cd backend
pip install -r requirements.txt
python -m pytest -q

# Frontend (proxy al backend en :8000)
cd frontend
npm install
npm run dev          # http://localhost:5173
npm test             # pruebas del chat (vitest)
npm run build
```

## Preguntas frecuentes

**¿Por qué WAHA y no la API oficial de WhatsApp?**
WAHA permite usar los teléfonos que ya tenés, sin aprobación de Meta ni costo por conversación. La contra: es una conexión no oficial, con los riesgos de abajo.

**¿Me pueden bloquear el número?**
Sí, es posible con cualquier herramienta no oficial. Depende más del número y del uso (número nuevo, mensajes a desconocidos, volumen, IP de datacenter) que del software. Para números críticos conviene la Cloud API oficial.

**¿Se pierden mis datos si reinicio?**
No: la base vive en un volumen de Docker y las sesiones de WhatsApp en `data/waha/sessions`. `docker compose down -v` sí borra la base.

## Limitaciones conocidas

- **Vía no oficial:** las sesiones pueden caerse y los números pueden ser bloqueados por WhatsApp.
- Las tablas se crean con `create_all`; falta migrar a **Alembic** antes de producción.
- El tiempo real usa un hub en memoria; con más de un worker hay que pasarlo a Redis pub/sub.
- Todavía no se envían ni se muestran **archivos multimedia**; los grupos y los estados se ignoran.
- Fijar la versión de la imagen de WAHA (`devlikeapro/waha:latest` en el compose) antes de producción.

## Hoja de ruta

- [ ] Reportes: tiempos de respuesta, volumen por número y conversiones por campaña
- [ ] Meta Conversions API (eventos al mover etapas del pipeline)
- [ ] Monitoreo de sesiones caídas con alertas y reconexión automática
- [ ] Backups automáticos de la base y de las sesiones
- [ ] Imágenes, audios y documentos
- [ ] Alta de operadores desde el panel
- [ ] Migración a AWS
- [ ] Cloud API oficial como proveedor alternativo
