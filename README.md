<div align="center">

# 🟢 Universia Control

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

## Así se ve

<p align="center">
  <img src="docs/screenshots/chat.png" alt="Bandeja de chat con todos los números" width="100%">
</p>

Cada número tiene su propio color, que se repite en el avatar, la etiqueta y el pipeline para saber de un vistazo por cuál escribió cada cliente.

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/pipeline.png" alt="Pipeline de ventas"><br><sub>Pipeline de ventas</sub></td>
    <td width="50%"><img src="docs/screenshots/numeros.png" alt="Gestión de números"><br><sub>Gestión de números</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/screenshots/login.png" alt="Pantalla de ingreso"><br><sub>Ingreso</sub></td>
    <td width="50%" align="center"><img src="docs/screenshots/celular.png" alt="Chat en celular" width="45%"><br><sub>En el celular</sub></td>
  </tr>
</table>

> Las capturas usan datos de ejemplo.

## ¿Qué es?

Si atendés clientes por WhatsApp con varios teléfonos, terminás saltando de celular en celular. **Universia Control** conecta todos esos números a un solo panel web donde tu equipo ve, responde y organiza todas las conversaciones, con los datos en **tu propio servidor**.

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
git clone https://github.com/lorenzo00005/universia-control.git
cd universia-control
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

## Publicarlo en internet (un dominio, CRM + WAHA)

Con `docker-compose.prod.yml` queda todo detrás de **Caddy** con HTTPS automático (Let's Encrypt):

| URL | Qué es |
|---|---|
| `https://crm.tudominio.com` | Panel del CRM |
| `https://waha.tudominio.com` | Dashboard de WAHA (con usuario/clave extra de Caddy, además del login de WAHA) |

1. Creá dos registros DNS tipo **A** (`crm` y `waha`) apuntando a la IP del servidor.
2. En el servidor, completá el `.env` con claves propias y las variables de producción (`CRM_DOMAIN`, `WAHA_DOMAIN`, `WAHA_BASIC_HASH`).
3. Abrí solo los puertos **80 y 443** (y SSH) en el firewall.
4. Levantá:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

En producción Postgres, el backend, WAHA y el frontend **no publican puertos**: todo entra por Caddy. Los WebSockets del panel funcionan por `wss://` sin configuración extra.

## Conexión con el Pixel de Meta (venta → Purchase)

Pensado para el flujo **anuncio → landing → WhatsApp**. Cuando marcás un chat como venta, el CRM manda un evento `Purchase` a la **API de conversiones** de Meta atribuido al anuncio.

```mermaid
sequenceDiagram
    participant C as Cliente
    participant L as Landing (Pixel + tracker.js)
    participant R as CRM
    participant M as Meta
    C->>L: clic en el anuncio (fbclid)
    L->>R: POST /track/click (fbclid, _fbc, _fbp, utm, URL)
    R-->>L: código corto, ej. K7X2QM
    C->>R: WhatsApp: "Hola, quiero info [K7X2QM]"
    R->>R: une el chat con el clic
    R->>M: Marcar como venta → Purchase (fbc, fbp, IP, teléfono hasheado, monto)
```

**Configuración**

1. En el Administrador de eventos de Meta: copiá el **ID del Pixel** y generá un **token** de la API de conversiones. Ponelos en `.env` (`META_PIXEL_ID`, `META_ACCESS_TOKEN`) y agregá el dominio de tu landing en `LANDING_ORIGINS`.
2. En tu landing, después del código del Pixel, pegá el script (ver [`landing/ejemplo.html`](landing/ejemplo.html)):

```html
<script src="tracker.js" data-crm="https://crm.tudominio.com"></script>
<a href="#" data-wa-number="5491100000000" data-wa-text="Hola, quiero información">Escribinos</a>
```

3. Para probar sin afectar campañas, cargá `META_TEST_EVENT_CODE` (sección *Probar eventos* de Meta) y mirá que los eventos aparezcan ahí.
4. En el chat, panel derecho: **Marcar como venta** (con monto opcional). El chat pasa a *Ganado* y el evento se envía en segundo plano. Podés ver el estado de cada envío en `GET /conversions` y reintentar los fallidos con `POST /conversions/{id}/retry`.

**Qué se envía:** `fbc` y `fbp` del clic, IP y navegador del clic, URL de la landing, teléfono normalizado y hasheado con SHA-256 (nunca en claro), monto y un `event_id`.

**Límites a tener en cuenta**
- Si el cliente borra el código `[XXXXXX]` del mensaje, ese chat queda sin atribución al anuncio (el evento igual se envía con teléfono hasheado, con peor coincidencia).
- Los contactos que WhatsApp entrega como `@lid` no traen teléfono: el evento sale sin `ph`.
- Si el código llega al primer mensaje pero el cliente escribe desde otro número que el que usó en la landing, la atribución sigue funcionando porque se basa en el código, no en el teléfono.
- Meta atribuye dentro de su ventana (hasta 7 días desde el clic, según la configuración de tu cuenta).

## API

Documentación completa en `/docs`. Lo principal:

| Endpoint | Función |
|---|---|
| `POST /auth/login` · `GET /auth/me` | Autenticación |
| `POST /track/click` (público) · `POST /conversations/{id}/sale` · `GET /conversions` · `POST /conversions/{id}/retry` | Seguimiento de clics y envío de ventas a Meta |
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

- **Vía no oficial:** las sesiones pueden caerse y los números pueden ser bloqueados por WhatsApp. Leé la [guía para cuidar tus números](#cómo-cuidar-tus-números-guía-anti-bloqueo).
- Las tablas se crean con `create_all`; falta migrar a **Alembic** antes de producción.
- El tiempo real usa un hub en memoria; con más de un worker hay que pasarlo a Redis pub/sub.
- Todavía no se envían ni se muestran **archivos multimedia**; los grupos y los estados se ignoran.
- Fijar la versión de la imagen de WAHA (`devlikeapro/waha:latest` en el compose) antes de producción.

### Cómo cuidar tus números (guía anti-bloqueo)

WAHA se conecta por QR como un dispositivo vinculado, algo que WhatsApp no permite oficialmente: sus [normas de mensajería](https://www.whatsapp.com/legal/messaging-guidelines) prohíben los clientes no oficiales, el envío masivo y la automatización. **No existe una práctica que garantice 0 % de riesgo**; el objetivo es parecerse a una persona real atendiendo clientes y mantener las denuncias en cero. Meta no publica los umbrales exactos: las cifras de abajo son referencias de la documentación de WAHA y de proveedores del rubro (Green API, Whapi, Z-API, Periskope), no reglas oficiales.

#### 1. La regla que más pesa: que el cliente escriba primero

La propia guía de WAHA lo pone primero: el bot no debería iniciar conversaciones, sino responder. Este CRM está pensado para eso (anuncio → landing → el cliente toca el botón de WhatsApp y te escribe). Iniciar chats con desconocidos es lo que más bloqueos causa, porque cada "Bloquear y reportar" resta confianza al número. Un puñado de reportes seguidos alcanza para que lo limiten.

#### 2. Antes de conectar un número

- Usá **números calientes**: con historia real de uso (meses de chats, contactos que lo tienen guardado), no un chip recién comprado.
- Si el número es nuevo, **no escanees el QR el mismo día** del registro: esperá al menos un día y usalo antes como una persona (chats con conocidos, fotos, audios, algún grupo chico).
- Nunca conectes un chip que **nunca recibió un mensaje de WhatsApp**: un número sin historial que de golpe manda mensajes es el perfil típico de una granja de spam.
- Completá el perfil: **foto, nombre y estado**.
- Seguí **abriendo la app en el celular** de vez en cuando y respondiendo algo a mano. Un número usado solo por automatización es más sospechoso.
- Pedí a los clientes que **guarden tu número** en sus contactos: baja mucho las denuncias por "remitente desconocido".
- Mantené un número de **tu país** y, si podés, un servidor con IP del mismo país o cercana; los desajustes (número argentino conectado siempre desde otro continente) suman señales negativas.

#### 3. Calentamiento y ritmo

Referencia habitual de los proveedores para un número nuevo (adaptala, no la tomes como regla):

| Momento | Qué hacer |
|---|---|
| Día 1 | Chats manuales con 3–6 contactos que respondan. Texto, alguna imagen o sticker. Sin automatizar. |
| Día 2 | Subir a 10–15 conversaciones. Mensajes variados, ~1 por minuto como máximo. |
| Días 3–6 | Sumar contactos y mensajes de a poco; participar en 1–2 grupos chicos (3–5 personas). |
| Día 7 en adelante | Entre ~12 y ~100 mensajes por día, según respuestas. Después del día 10 el número es bastante más resistente. |
| Semanas siguientes | Escalar por **semana**, no por día. Subir 10–20 % por vez, nunca saltar de 50 a 5.000. |

Límites prudentes que se repiten en las guías: un número nuevo no debería pasar de unos **50 mensajes por día**, ni de ~30 por hora, y conviene mantener que **por lo menos 3 de cada 10 mensajes enviados reciban respuesta**. Un número con 10 días de calentamiento aguanta solo un par de decenas de conversaciones **nuevas** por día. Como en este CRM la mayoría son respuestas a clientes que escribieron primero, esos límites rara vez se rozan; sí importan si vas a escribirles a contactos.

#### 4. Cómo responder sin parecer un bot

Estas son las recomendaciones de la guía oficial de WAHA para el flujo de respuesta:

1. **Marcar como leído** antes de contestar (`POST /api/sendSeen`).
2. **Mostrar "escribiendo…"** (`startTyping`), esperar un tiempo aleatorio proporcional al largo del mensaje y **recién ahí enviar** (`stopTyping` + `sendText`).
3. **Evitar tiempos fijos**: enviar, esperar entre 30 y 60 segundos al azar y recién entonces el siguiente.
4. **Variar el texto** y personalizar (por ejemplo con el nombre). No mandar el mismo bloque a muchas personas en pocos minutos.
5. Si le escribís a alguien por primera vez: **un solo mensaje corto**, sin links ni textos largos.
6. **Enviar en tandas**: por ejemplo, como máximo 4 mensajes por hora a un mismo contacto que ya respondió, y pausar antes de la siguiente tanda.
7. Usar solo links **HTTPS** y evitar los que ya fueron marcados como spam.
8. Cuidar el contenido: los temas con palabras de estafas financieras ("PIX", "boleto", "tarjeta" y similares) se vigilan más.

> Hoy el CRM envía el mensaje directo por `sendText`. Los pasos 1 y 2 (visto y "escribiendo…" con pausa aleatoria) están en la hoja de ruta.

#### 5. Qué evitar

- Escribirle en masa a desconocidos, usar **listas compradas** o contactar a quien nunca te respondió.
- Mensajes idénticos a muchos contactos, o a intervalos exactos (cada 10 s).
- **Ignorar un pedido de baja**: si alguien dice "no me escribas más", dejá de escribirle de inmediato.
- Agregar mucha gente a grupos de golpe (como mucho 15–20 contactos por día).
- Usar **varias herramientas no oficiales** a la vez sobre el mismo número, o apps modificadas (GBWhatsApp y similares).
- Instalar forks dudosos de librerías de WhatsApp: ya hubo un paquete de npm que robaba sesiones. Usá solo la imagen oficial de WAHA y fijá su versión.

#### 6. Repartí la carga y aislá el riesgo

El CRM acepta tantos números como quieras: aprovechalo. Repartir los contactos entre varios números baja el volumen de cada uno, y separar roles (por ejemplo, **ventas**, **soporte** y **campañas**) evita que el problema de un número arrastre al resto.

#### 7. Señales de alerta y qué hacer

| Señal | Qué significa | Qué hacer |
|---|---|---|
| Error `463` al escribir a un contacto nuevo, pero la sesión sigue en `WORKING` | Restricción temporal para contactar gente nueva | **No reinicies, no cierres sesión ni vuelvas a vincular.** Pausá los contactos nuevos: se levanta sola. |
| Error `475` / estado `CAPPED` | Cupo de contactos nuevos agotado en el ciclo | Igual que arriba: no reiniciar, esperar el reinicio del ciclo. |
| Avisos `FIRST_WARNING` / `SECOND_WARNING` | WhatsApp avisa que el ritmo es excesivo | Bajar el ritmo ya. |
| Mensaje "tu cuenta está restringida" en el celular | Actividad con aspecto de spam o automatización | Frenar todo envío, volver a usar el número a mano unos días. |
| La sesión se cae seguido | Puede ser inestabilidad o un castigo previo | Revisar el panel de Números; si se repite, reducir actividad y no reconectar en bucle. |

Desde 2025 varios proveedores reportan que las suspensiones llegan **sin advertencia previa**, así que el monitoreo y los backups de sesión importan.

#### 8. Si el número igual se bloquea

- Pedí la revisión desde la propia app de WhatsApp.
- **No lo reconectes igual**: tras un bloqueo el calentamiento se reinicia de cero y el segundo bloqueo llega más rápido.
- Si tenés que usar un número nuevo, calentalo desde el día 1 y **no lo configures idéntico** al anterior (mismo nombre, foto, descripción y mensajes): WhatsApp puede asociarlos.

#### 9. Cuándo conviene la API oficial

Para **campañas de envío masivo**, para números críticos del negocio o si no podés arriesgar el número, la vía correcta es la **Cloud API oficial de Meta**. Está en la hoja de ruta como proveedor alternativo y, además, es la que entrega el `ctwa_clid` de los anuncios Click-to-WhatsApp.

#### Checklist rápido

- [ ] El cliente escribe primero (landing, anuncio o botón de WhatsApp).
- [ ] Número con historia real, perfil completo y contactos que lo tienen guardado.
- [ ] Calentado antes de conectarlo y escalado por semana.
- [ ] Respuestas variadas, con pausas, y sin mensajes idénticos en tandas.
- [ ] Pedidos de baja respetados al instante.
- [ ] Carga repartida entre varios números por rol.
- [ ] Versión de WAHA fija y backup de las sesiones.
- [ ] Si aparece 463 o 475: no reiniciar, esperar y bajar el ritmo.

## Hoja de ruta

- [ ] Reportes: tiempos de respuesta, volumen por número y conversiones por campaña
- [x] Meta Conversions API: venta → Purchase desde la landing (pendiente: otros eventos al mover etapas, Cloud API con ctwa_clid)
- [ ] Monitoreo de sesiones caídas con alertas y reconexión automática
- [ ] Backups automáticos de la base y de las sesiones
- [ ] Envío más humano: marcar como leído y "escribiendo…" con pausa aleatoria antes de cada respuesta
- [ ] Alertas de errores 463/475 y avisos de WhatsApp en el panel de Números
- [ ] Imágenes, audios y documentos
- [ ] Alta de operadores desde el panel
- [ ] Migración a AWS
- [ ] Cloud API oficial como proveedor alternativo
