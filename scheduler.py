"""
Scheduler automático para sincronización de ventas
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from sync import sincronizar_ventas

logger = logging.getLogger(__name__)


def job_sincronizar():
    """Job que ejecuta la sincronización"""
    try:
        logger.info("=== Scheduler: Iniciando sincronización automática ===")
        resultado = sincronizar_ventas()
        logger.info(f"Scheduler: Completado - {resultado}")
    except Exception as e:
        logger.error(f"Scheduler: Error en sincronización - {e}", exc_info=True)


def iniciar_scheduler():
    """
    Inicializa y arranca el scheduler en background
    """
    scheduler = BackgroundScheduler()
    
    # Agregar job con intervalo configurable
    scheduler.add_job(
        func=job_sincronizar,
        trigger=IntervalTrigger(minutes=settings.sync_intervalo_min),
        id='sync_ventas',
        name='Sincronización de ventas con GHL',
        replace_existing=True
    )
    
    scheduler.start()
    
    logger.info(
        f"Scheduler iniciado: sincronización cada {settings.sync_intervalo_min} minutos"
    )
    
    return scheduler
