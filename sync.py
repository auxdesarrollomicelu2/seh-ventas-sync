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
    logger.info("🔄 Iniciando sincronización...")
    
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
        
        logger.info(f"📊 {total} ventas encontradas desde {settings.sync_desde}")
        
        # 🧪 MODO PRUEBA: Procesar hasta encontrar 1 venta nueva (que no exista en GHL)
        max_ventas_a_revisar = min(10, total)  # Revisar máximo 10 ventas para encontrar 1 nueva
        ventas_a_procesar = ventas[:max_ventas_a_revisar]
        
        for venta in ventas_a_procesar:
            order_id = venta['order_id']
            order_number = venta['order_number']
            telefono_crudo = venta.get('phone_number', '')
            valor = float(venta.get('total_amount', 0))
            nombre_cliente = venta.get('first_name')  # Puede ser None
            
            logger.info(f"📦 {order_number} | {nombre_cliente or 'Sin nombre'} | ${valor:,.0f}")
            
            # Validar teléfono
            if not telefono_crudo:
                logger.warning(f"   ⏭️  Sin teléfono")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "sin_telefono"
                })
                continue
            
            # Normalizar teléfono
            try:
                telefono_normalizado = normalizar_telefono_colombiano(telefono_crudo)
            except ValueError as e:
                logger.warning(f"   ❌ Teléfono inválido")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": f"telefono_invalido"
                })
                continue
            
            # Verificar idempotencia: buscar si ya existe la oportunidad
            nombre_oportunidad = f"Venta {order_number}"
            
            opp_existente = ghl_client.buscar_oportunidad_por_nombre(nombre_oportunidad)
            
            if opp_existente:
                logger.info(f"   ⏭️  Ya existe en GHL")
                omitidas += 1
                continue
            
            # Upsert contacto
            contacto_id = ghl_client.upsert_contacto(
                telefono=telefono_normalizado,
                nombre=nombre_cliente  # Ahora incluye el nombre
            )
            
            if not contacto_id:
                logger.error(f"   ❌ Error crear contacto")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "fallo_upsert_contacto"
                })
                continue
            
            # Verificar si el contacto ya tiene una oportunidad abierta en este pipeline
            tiene_opp_abierta = ghl_client.contacto_tiene_oportunidad_abierta(
                contacto_id=contacto_id,
                pipeline_id=settings.ghl_pipeline_id
            )
            
            if tiene_opp_abierta:
                logger.info(f"   ⏭️  Cliente ya tiene oportunidad abierta")
                omitidas += 1
                continue
            
            # Crear oportunidad
            oportunidad_id = ghl_client.crear_oportunidad(
                contacto_id=contacto_id,
                nombre_oportunidad=nombre_oportunidad,
                valor=valor
            )
            
            if not oportunidad_id:
                logger.error(f"   ❌ Error crear oportunidad")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "fallo_crear_oportunidad"
                })
                continue
            
            # Agregar tag seh_cliente_compro
            tag_agregado = ghl_client.agregar_tag_contacto(contacto_id, "seh_cliente_compro")
            
            # Éxito
            logger.info(f"   ✅ Sincronizada → Contacto: {contacto_id[:8]}... | Opp: {oportunidad_id[:8]}... | Tag: {'✅' if tag_agregado else '⚠️'}")
            procesadas += 1
            
            # 🧪 MODO PRUEBA: Detener después de procesar 3 ventas exitosas
            if procesadas >= 3:
                logger.info(f"🛑 Límite alcanzado ({procesadas} ventas procesadas)")
                break
        
        logger.info(f"📊 Resumen: Total:{total} | ✅ {procesadas} | ⏭️ {omitidas} | ❌ {errores}")
        
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
