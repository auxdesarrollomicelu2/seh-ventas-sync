"""
Lógica de sincronización de ventas con GHL
"""
from typing import Dict, Any
import logging

from config import settings
from ventas import obtener_ventas_para_sincronizar
from phone import normalizar_telefono_colombiano, enmascarar_telefono
from ghl_client import ghl_client

logger = logging.getLogger(__name__)


def sincronizar_ventas() -> Dict[str, Any]:
    """
    Sincroniza ventas pagadas con GHL
    
    Returns:
        Resumen de la sincronización con contadores
    """
    logger.info("=== Iniciando sincronización ===")
    logger.info(f"DRY_RUN: {settings.dry_run}")
    logger.info(f"SYNC_DESDE: {settings.sync_desde}")
    
    # Contadores
    total = 0
    procesadas = 0
    omitidas = 0
    errores = 0
    errores_detalle = []
    
    try:
        # Obtener ventas para sincronizar
        ventas = obtener_ventas_para_sincronizar(settings.sync_desde)
        total = len(ventas)
        
        logger.info(f"Ventas a procesar: {total}")
        
        for venta in ventas:
            order_id = venta['order_id']
            order_number = venta['order_number']
            telefono_crudo = venta.get('phone_number', '')
            valor = float(venta.get('total_amount', 0))
            
            logger.info(f"\n--- Procesando venta {order_number} (ID: {order_id}) ---")
            
            # Validar teléfono
            if not telefono_crudo:
                logger.warning(f"Venta {order_number}: sin teléfono, omitida")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "sin_telefono"
                })
                continue
            
            # Normalizar teléfono
            try:
                telefono_normalizado = normalizar_telefono_colombiano(telefono_crudo)
                logger.info(f"Teléfono normalizado: {enmascarar_telefono(telefono_normalizado)}")
            except ValueError as e:
                logger.error(f"Venta {order_number}: teléfono inválido - {e}")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": f"telefono_invalido: {str(e)}"
                })
                continue
            
            # Verificar idempotencia: buscar si ya existe la oportunidad
            nombre_oportunidad = f"Venta {order_number}"
            opp_existente = ghl_client.buscar_oportunidad_por_nombre(nombre_oportunidad)
            
            if opp_existente:
                logger.info(f"Venta {order_number}: ya existe oportunidad {opp_existente}, omitida")
                omitidas += 1
                continue
            
            # Upsert contacto
            contacto_id = ghl_client.upsert_contacto(
                telefono=telefono_normalizado,
                nombre=None  # Por ahora sin nombre
            )
            
            if not contacto_id:
                logger.error(f"Venta {order_number}: fallo al crear/actualizar contacto")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "fallo_upsert_contacto"
                })
                continue
            
            # Crear oportunidad
            oportunidad_id = ghl_client.crear_oportunidad(
                contacto_id=contacto_id,
                nombre_oportunidad=nombre_oportunidad,
                valor=valor
            )
            
            if not oportunidad_id:
                logger.error(f"Venta {order_number}: fallo al crear oportunidad")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "fallo_crear_oportunidad"
                })
                continue
            
            # Éxito
            logger.info(
                f"✓ Venta {order_number} sincronizada: "
                f"contacto={contacto_id}, oportunidad={oportunidad_id}"
            )
            procesadas += 1
        
        logger.info("=== Sincronización completada ===")
        
        resumen = {
            "total": total,
            "procesadas": procesadas,
            "omitidas": omitidas,
            "errores": errores,
            "dry_run": settings.dry_run
        }
        
        if errores_detalle:
            resumen["errores_detalle"] = errores_detalle
        
        return resumen
        
    except Exception as e:
        logger.error(f"Error en sincronización: {e}", exc_info=True)
        return {
            "total": total,
            "procesadas": procesadas,
            "omitidas": omitidas,
            "errores": errores,
            "error_general": str(e),
            "dry_run": settings.dry_run
        }
