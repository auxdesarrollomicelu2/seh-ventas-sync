"""
Scheduler automático para sincronización de ventas
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone

from config import settings
from sync import sincronizar_ventas

logger = logging.getLogger(__name__)

# Timezone Colombia
TIMEZONE_COLOMBIA = timezone('America/Bogota')


def job_sincronizar():
    """Job que ejecuta la sincronización"""
    try:
        logger.info("⏰ Scheduler ejecutando...")
        resultado = sincronizar_ventas()
    except Exception as e:
        logger.error(f"❌ Scheduler error: {e}")



def iniciar_scheduler():
    """
    Inicializa y arranca el scheduler en background con timezone Colombia
    """
    scheduler = BackgroundScheduler(timezone=TIMEZONE_COLOMBIA)
    
    # Agregar job con intervalo configurable en timezone Colombia
    scheduler.add_job(
        func=job_sincronizar,
        trigger=IntervalTrigger(minutes=settings.sync_intervalo_min, timezone=TIMEZONE_COLOMBIA),
        id='sync_ventas',
        name='Sincronización de ventas con GHL',
        replace_existing=True
    )
    
    scheduler.start()
    
    logger.info(
        f"Scheduler iniciado: sincronización cada {settings.sync_intervalo_min} minutos (Timezone: America/Bogota UTC-5)"
    )
    
    return scheduler
