# SEH Ventas Sync

Servicio independiente para sincronizar ventas pagadas desde PostgreSQL hacia GoHighLevel.

## Características

- ✅ Lectura de ventas desde `public.orden` y `public.addres` (solo lectura)
- ✅ Endpoint protegido para consultar ventas
- ✅ Sincronización automática con GoHighLevel
- ✅ Normalización de teléfonos colombianos a E.164
- ✅ Idempotencia sin base de datos (búsqueda en GHL)
- ✅ Modo DRY_RUN para pruebas
- ✅ Desplegable en Railway

## Requisitos

- Python 3.11+
- PostgreSQL (solo lectura)
- Cuenta de GoHighLevel con API v2

## Instalación

```bash
# Clonar repositorio
git clone <repo>
cd seh-ventas-sync

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

## Configuración

Edita `.env` con tus valores:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
API_KEY=tu_clave_secreta
GHL_TOKEN=tu_token_ghl
GHL_LOCATION_ID=tu_location_id
GHL_PIPELINE_ID=id_del_pipeline_ventas_exitosas
GHL_STAGE_VENTA_REALIZADA_ID=id_de_etapa_venta_realizada
SYNC_DESDE=2024-01-01
SYNC_INTERVALO_MIN=10
DRY_RUN=true
LOG_LEVEL=INFO
```

## Uso

### Desarrollo

```bash
# Ejecutar servidor Flask
python -m flask --app app.app run --port 8000 --debug

# Abrir en navegador
# http://localhost:8000  (Visualizador web con interfaz)
# http://localhost:8000/health  (Health check)

# O con gunicorn (producción)
gunicorn -w 4 -b 0.0.0.0:8000 app.app:app

# Ejecutar tests
pytest -v
```

### Visualizador Web

Abre `http://localhost:8000` en tu navegador para ver una interfaz visual donde puedes:
- Seleccionar fecha de inicio
- Ver estadísticas de ventas
- Validar teléfonos normalizados
- Ver todas las ventas en tabla

**Importante:** Edita tu API key en el archivo `app/templates/ventas.html` línea 246:
```javascript
const API_KEY = 'tu_api_key_real';
```

### Endpoints

#### GET /health
Health check sin autenticación.

```bash
curl http://localhost:8000/health
```

#### GET /ventas?desde=YYYY-MM-DD
Lista ventas pagadas desde una fecha (requiere `x-api-key`).

```bash
curl -H "x-api-key: tu_clave" \
  "http://localhost:8000/ventas?desde=2024-01-01"
```

#### POST /sync/run
Ejecuta sincronización manual con GHL (requiere `x-api-key`).

```bash
curl -X POST -H "x-api-key: tu_clave" \
  http://localhost:8000/sync/run
```

## Flujo de sincronización

1. Lee ventas con `payment_status = 'PAID'` desde `SYNC_DESDE`
2. Normaliza teléfonos a formato E.164 (+57XXXXXXXXXX)
3. Busca en GHL si ya existe oportunidad "Venta {order_number}"
4. Si no existe:
   - Upsert de contacto por teléfono
   - Crea oportunidad en pipeline "Ventas exitosas"
   - Agrega etiqueta `seh_cliente_compro` (dispara workflow de encuesta)

## Despliegue en Railway

### 1. Conectar repositorio

1. Crea una cuenta en [Railway](https://railway.app)
2. Crea un nuevo proyecto
3. Conecta tu repositorio de GitHub

### 2. Configurar variables de entorno

En Railway, agrega todas las variables del `.env`:

```
DATABASE_URL=postgresql://...
API_KEY=tu_clave_secreta
GHL_TOKEN=tu_token
GHL_LOCATION_ID=tu_location
GHL_PIPELINE_ID=tu_pipeline
GHL_STAGE_VENTA_REALIZADA_ID=tu_stage
SYNC_DESDE=2026-01-01
SYNC_INTERVALO_MIN=10
DRY_RUN=false
LOG_LEVEL=INFO
PORT=8000
```

### 3. Desplegar

Railway detectará automáticamente el `Dockerfile` y desplegará el servicio.

El scheduler se ejecutará automáticamente cada `SYNC_INTERVALO_MIN` minutos.

### 4. Endpoints en producción

```
https://tu-app.railway.app/health
https://tu-app.railway.app/ventas?desde=2026-01-01
https://tu-app.railway.app/sync/run  (POST)
```

## Desarrollo

## ✅ Fase 1: Archivos base
- ✅ Estructura de proyecto
- ✅ Configuración
- ✅ Endpoints /health y /ventas
- ✅ Tests básicos

## ✅ Fase 2: Cliente GHL y sincronización
- ✅ Cliente GHL
- ✅ Sincronización con DRY_RUN
- ✅ Tests de integración

## ✅ Fase 3: Scheduler y despliegue
- ✅ Scheduler automático (APScheduler)
- ✅ Dockerfile para Railway
- ✅ Documentación completa

## Seguridad

- ❌ Nunca commitear `.env`
- ✅ Teléfonos enmascarados en logs
- ✅ Solo lectura en PostgreSQL
- ✅ Autenticación por API key

## Licencia

Propietario - SEH
