"""
Configuración del servicio usando pydantic-settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Configuración de la aplicación desde variables de entorno"""
    
    # Base de datos
    database_url: str
    
    # Autenticación API
    api_key: str
    
    # GHL API v2
    ghl_token: str
    ghl_location_id: str
    ghl_pipeline_id: str
    ghl_stage_venta_realizada_id: str
    
    # Sincronización
    sync_desde: str  # Formato: YYYY-MM-DD
    sync_intervalo_min: int = 10
    dry_run: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    # Campos opcionales
    nombre_tabla: Optional[str] = None
    nombre_columna: Optional[str] = None
    
    # Puerto para Railway
    port: int = 8000
    
    model_config = SettingsConfigDict(
        env_file=".env" if os.path.exists(".env") else None,
        case_sensitive=False,
        extra="ignore",
        env_file_encoding="utf-8"
    )


# Instancia global de configuración
settings = Settings()
