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
        
        logger.info(f"📊 Ventas encontradas en BD: {total}")
        
        # 🧪 MODO PRUEBA: Procesar hasta encontrar 1 venta nueva (que no exista en GHL)
        max_ventas_a_revisar = min(10, total)  # Revisar máximo 10 ventas para encontrar 1 nueva
        ventas_a_procesar = ventas[:max_ventas_a_revisar]
        logger.warning(f"🧪 MODO PRUEBA: Revisando hasta {max_ventas_a_revisar} ventas para encontrar 1 nueva")
        
        for venta in ventas_a_procesar:
            order_id = venta['order_id']
            order_number = venta['order_number']
            telefono_crudo = venta.get('phone_number', '')
            valor = float(venta.get('total_amount', 0))
            nombre_cliente = venta.get('first_name')  # Puede ser None
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📦 Procesando venta #{procesadas + omitidas + errores + 1}/{len(ventas)}")
            logger.info(f"   Order: {order_number} (ID: {order_id})")
            logger.info(f"   Cliente: {nombre_cliente or 'Sin nombre'}")
            logger.info(f"   Valor: ${valor:,.0f}")
            logger.info(f"   Teléfono crudo: {enmascarar_telefono(telefono_crudo)}")
            
            # Validar teléfono
            if not telefono_crudo:
                logger.warning(f"❌ Venta {order_number}: sin teléfono, omitida")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "sin_telefono"
                })
                continue
            
            # Normalizar teléfono
            try:
                telefono_normalizado = normalizar_telefono_colombiano(telefono_crudo)
                logger.info(f"✅ Teléfono normalizado: {enmascarar_telefono(telefono_normalizado)}")
            except ValueError as e:
                logger.error(f"❌ Venta {order_number}: teléfono inválido - {e}")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": f"telefono_invalido: {str(e)}"
                })
                continue
            
            # Verificar idempotencia: buscar si ya existe la oportunidad
            nombre_oportunidad = f"Venta {order_number}"
            logger.info(f"🔍 Buscando en GHL: '{nombre_oportunidad}'...")
            
            opp_existente = ghl_client.buscar_oportunidad_por_nombre(nombre_oportunidad)
            
            if opp_existente:
                logger.info(f"⏭️  Ya existe oportunidad {opp_existente}, omitida")
                omitidas += 1
                continue
            
            logger.info(f"🆕 No existe en GHL, procediendo a crear...")
            
            # Upsert contacto
            logger.info(f"👤 Creando/actualizando contacto...")
            contacto_id = ghl_client.upsert_contacto(
                telefono=telefono_normalizado,
                nombre=nombre_cliente  # Ahora incluye el nombre
            )
            
            if not contacto_id:
                logger.error(f"❌ Venta {order_number}: fallo al crear/actualizar contacto")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "fallo_upsert_contacto"
                })
                continue
            
            logger.info(f"✅ Contacto: {contacto_id}")
            
            # Verificar si el contacto ya tiene una oportunidad abierta en este pipeline
            logger.info(f"🔎 Verificando si el contacto ya tiene oportunidad abierta...")
            tiene_opp_abierta = ghl_client.contacto_tiene_oportunidad_abierta(
                contacto_id=contacto_id,
                pipeline_id=settings.ghl_pipeline_id
            )
            
            if tiene_opp_abierta:
                logger.info(f"⏭️  Contacto ya tiene oportunidad abierta en este pipeline, omitida")
                omitidas += 1
                continue
            
            logger.info(f"✅ Contacto libre para crear nueva oportunidad")
            
            # Crear oportunidad
            logger.info(f"💼 Creando oportunidad con valor ${valor:,.0f}...")
            oportunidad_id = ghl_client.crear_oportunidad(
                contacto_id=contacto_id,
                nombre_oportunidad=nombre_oportunidad,
                valor=valor
            )
            
            if not oportunidad_id:
                logger.error(f"❌ Venta {order_number}: fallo al crear oportunidad")
                errores += 1
                errores_detalle.append({
                    "order_number": order_number,
                    "error": "fallo_crear_oportunidad"
                })
                continue
            
            logger.info(f"✅ Oportunidad creada: {oportunidad_id}")
            
            # Agregar tag seh_cliente_compro
            logger.info(f"🏷️  Agregando tag 'seh_cliente_compro'...")
            tag_agregado = ghl_client.agregar_tag_contacto(contacto_id, "seh_cliente_compro")
            
            if tag_agregado:
                logger.info(f"✅ Tag agregado correctamente")
            else:
                logger.warning(f"⚠️  No se pudo agregar el tag (no crítico)")
            
            # Éxito
            logger.info(f"✅ ÉXITO: Venta {order_number} sincronizada")
            logger.info(f"   └─ Contacto: {contacto_id}")
            logger.info(f"   └─ Oportunidad: {oportunidad_id}")
            logger.info(f"   └─ Tag: {'✅' if tag_agregado else '⚠️'}")
            procesadas += 1
            
            # 🧪 MODO PRUEBA: Detener después de procesar 1 venta exitosa
            if procesadas >= 1:
                logger.warning(f"🧪 MODO PRUEBA: Se procesó 1 venta exitosamente, deteniendo...")
                break
        
        logger.info(f"\n{'='*60}")
        logger.info("=== Sincronización completada ===")
        logger.info(f"📊 Resumen:")
        logger.info(f"   Total encontradas: {total}")
        logger.info(f"   ✅ Procesadas: {procesadas}")
        logger.info(f"   ⏭️  Omitidas: {omitidas}")
        logger.info(f"   ❌ Errores: {errores}")
        logger.info(f"   🧪 DRY_RUN: {settings.dry_run}")
        logger.info(f"{'='*60}\n")
        
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
