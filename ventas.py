"""
Consulta de ventas desde PostgreSQL (solo lectura)
Tablas: public.orden y public.addres
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from db import db
from config import settings

logger = logging.getLogger(__name__)


def obtener_ventas(desde: str, limite: int = 500) -> List[Dict[str, Any]]:
    """
    Obtiene ventas pagadas desde una fecha específica
    
    Args:
        desde: Fecha en formato YYYY-MM-DD
        limite: Número máximo de filas a retornar
        
    Returns:
        Lista de ventas con datos combinados de orden y addres
    """
    query = """
        SELECT 
            o.order_id,
            o.order_number,
            o.user_id,
            o.created_at,
            o.payment_status,
            o.status,
            o.total_amount,
            o.customer_document,
            a.phone_number,
            a.city
        FROM public.orders o
        LEFT JOIN public.addresses a ON o.address_id = a.address_id
        WHERE o.payment_status = 'PAID'
          AND o.created_at >= %s
        ORDER BY o.created_at DESC
        LIMIT %s
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (desde, limite))
            rows = cur.fetchall()
            
            logger.info(f"Obtenidas {len(rows)} ventas desde {desde}")
            return rows


def obtener_ventas_para_sincronizar(desde: str) -> List[Dict[str, Any]]:
    """
    Obtiene ventas PAID para sincronizar con GHL
    
    Args:
        desde: Fecha mínima en formato YYYY-MM-DD (SYNC_DESDE)
        
    Returns:
        Lista de ventas válidas para sincronización
    """
    query = """
        SELECT 
            o.order_id,
            o.order_number,
            o.user_id,
            o.created_at,
            o.total_amount,
            o.customer_document,
            a.phone_number,
            a.city
        FROM public.orders o
        LEFT JOIN public.addresses a ON o.address_id = a.address_id
        WHERE o.payment_status = 'PAID'
          AND o.created_at >= %s
        ORDER BY o.created_at ASC
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (desde,))
            rows = cur.fetchall()
            
            logger.info(f"Ventas para sincronizar: {len(rows)}")
            return rows


def obtener_nombre_cliente(row: Dict[str, Any]) -> Optional[str]:
    """
    Obtiene el nombre del cliente si está configurado
    
    Args:
        row: Fila con datos de la venta
        
    Returns:
        Nombre del cliente o None
    """
    # Por ahora retorna None, se implementará cuando esté disponible
    if settings.nombre_tabla and settings.nombre_columna:
        # TODO: Implementar join con tabla de nombre cuando esté disponible
        pass
    return None
