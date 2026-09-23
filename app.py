"""
Flask application - seh-ventas-sync
Endpoints: /health, /ventas, /sync/run
"""
from flask import Flask, jsonify, request, render_template
from typing import Dict, Any
from datetime import datetime, timedelta
from functools import wraps
import logging
import atexit

from config import settings
from db import db
from ventas import obtener_ventas
from phone import normalizar_telefono_colombiano, enmascarar_telefono
from scheduler import iniciar_scheduler

# Configurar logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear app Flask
app = Flask(__name__)

# Inicializar scheduler (solo si no está en modo debug reloader)
scheduler = None


def require_api_key(f):
    """Decorator para verificar el API key en headers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if not api_key or api_key != settings.api_key:
            return jsonify({"error": "API key inválido o faltante"}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_first_request():
    """Inicialización antes de la primera petición"""
    global scheduler
    
    if not hasattr(app, 'initialized'):
        logger.info("Iniciando seh-ventas-sync...")
        db.connect()
        logger.info(f"DRY_RUN: {settings.dry_run}")
        logger.info(f"SYNC_DESDE: {settings.sync_desde}")
        
        # Iniciar scheduler (evitar en modo debug reloader)
        import os
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            scheduler = iniciar_scheduler()
            atexit.register(lambda: scheduler.shutdown() if scheduler else None)
        
        app.initialized = True


@app.route("/", methods=["GET"])
def index() -> str:
    """
    Página principal con visualizador de ventas
    """
    # Fecha por defecto: primer día del mes actual
    hoy = datetime.now()
    fecha_default = hoy.replace(day=1).strftime('%Y-%m-%d')
    fecha_hoy = hoy.strftime('%Y-%m-%d')
    return render_template('ventas.html', fecha_default=fecha_default, fecha_hoy=fecha_hoy)


@app.route("/health", methods=["GET"])
def health_check() -> tuple[Dict[str, Any], int]:
    """
    Endpoint de health check (sin autenticación)
    """
    return jsonify({
        "status": "ok",
        "service": "seh-ventas-sync",
        "version": "1.0.0",
        "dry_run": settings.dry_run
    }), 200


@app.route("/ventas", methods=["GET"])
@require_api_key
def listar_ventas() -> tuple[Dict[str, Any], int]:
    """
    Lista ventas pagadas desde una fecha
    Requiere header: x-api-key
    Query param: desde (YYYY-MM-DD)
    
    Returns:
        JSON con ventas (máximo 500)
    """
    desde = request.args.get('desde')
    
    if not desde:
        return jsonify({"error": "Parámetro 'desde' es requerido"}), 400
    
    try:
        # Validar formato de fecha
        datetime.strptime(desde, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400
    
    try:
        ventas_raw = obtener_ventas(desde, limite=500)
        
        # Formatear respuesta
        ventas = []
        for v in ventas_raw:
            telefono_crudo = v.get('phone_number', '')
            telefono_normalizado = None
            error_telefono = None
            
            # Intentar normalizar teléfono
            if telefono_crudo:
                try:
                    telefono_normalizado = normalizar_telefono_colombiano(telefono_crudo)
                except ValueError as e:
                    error_telefono = str(e)
                    logger.warning(
                        f"Teléfono inválido en orden {v['order_number']}: "
                        f"{enmascarar_telefono(telefono_crudo)} - {error_telefono}"
                    )
            
            venta = {
                "id_venta": v['order_id'],
                "order_number": v['order_number'],
                "user_id": v['user_id'],
                "nombre_cliente": v.get('first_name'),
                "telefono_crudo": telefono_crudo,
                "telefono_normalizado": telefono_normalizado,
                "error_telefono": error_telefono,
                "ciudad": v.get('city'),
                "valor": float(v['total_amount']) if v.get('total_amount') else 0.0,
                "fecha_venta": v['created_at'].isoformat() if v.get('created_at') else None,
                "estado_pedido": v.get('status'),
                "payment_status": v.get('payment_status')
            }
            ventas.append(venta)
        
        return jsonify({
            "total": len(ventas),
            "desde": desde,
            "ventas": ventas
        }), 200
        
    except Exception as e:
        logger.error(f"Error al obtener ventas: {e}", exc_info=True)
        return jsonify({"error": "Error al obtener ventas"}), 500


@app.route("/sync/run", methods=["POST"])
@require_api_key
def ejecutar_sincronizacion() -> tuple[Dict[str, Any], int]:
    """
    Ejecuta sincronización manual con GHL
    Requiere header: x-api-key
    
    Returns:
        Resumen de la sincronización
    """
    from sync import sincronizar_ventas
    
    try:
        resumen = sincronizar_ventas()
        return jsonify(resumen), 200
    except Exception as e:
        logger.error(f"Error en sincronización: {e}", exc_info=True)
        return jsonify({
            "error": "Error al ejecutar sincronización",
            "detalle": str(e)
        }), 500


@app.route("/sync/scheduler/status", methods=["GET"])
@require_api_key
def scheduler_status() -> tuple[Dict[str, Any], int]:
    """
    Obtiene el estado del scheduler
    Requiere header: x-api-key
    
    Returns:
        Estado del scheduler
    """
    global scheduler
    
    if scheduler is None:
        return jsonify({
            "running": False,
            "message": "Scheduler no inicializado"
        }), 200
    
    is_running = scheduler.running
    
    return jsonify({
        "running": is_running,
        "interval_minutes": settings.sync_intervalo_min,
        "message": "Scheduler activo" if is_running else "Scheduler pausado"
    }), 200


@app.route("/sync/scheduler/pause", methods=["POST"])
@require_api_key
def pause_scheduler() -> tuple[Dict[str, Any], int]:
    """
    Pausa el scheduler automático
    Requiere header: x-api-key
    
    Returns:
        Confirmación
    """
    global scheduler
    
    if scheduler is None:
        return jsonify({
            "success": False,
            "message": "Scheduler no inicializado"
        }), 400
    
    if not scheduler.running:
        return jsonify({
            "success": False,
            "message": "Scheduler ya está pausado"
        }), 400
    
    try:
        scheduler.pause()
        logger.warning("⏸️  SCHEDULER PAUSADO MANUALMENTE")
        return jsonify({
            "success": True,
            "message": "Scheduler pausado correctamente"
        }), 200
    except Exception as e:
        logger.error(f"Error al pausar scheduler: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/sync/scheduler/resume", methods=["POST"])
@require_api_key
def resume_scheduler() -> tuple[Dict[str, Any], int]:
    """
    Reanuda el scheduler automático
    Requiere header: x-api-key
    
    Returns:
        Confirmación
    """
    global scheduler
    
    if scheduler is None:
        return jsonify({
            "success": False,
            "message": "Scheduler no inicializado"
        }), 400
    
    if scheduler.running:
        return jsonify({
            "success": False,
            "message": "Scheduler ya está activo"
        }), 400
    
    try:
        scheduler.resume()
        logger.warning("▶️  SCHEDULER REANUDADO MANUALMENTE")
        return jsonify({
            "success": True,
            "message": "Scheduler reanudado correctamente"
        }), 200
    except Exception as e:
        logger.error(f"Error al reanudar scheduler: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', settings.port))
    app.run(host="0.0.0.0", port=port, debug=False)
