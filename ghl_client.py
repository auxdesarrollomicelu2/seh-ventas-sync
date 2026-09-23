"""
Cliente para GoHighLevel API v2
https://services.leadconnectorhq.com
"""
import httpx
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

from config import settings

logger = logging.getLogger(__name__)


class GHLContacto(BaseModel):
    """Modelo para crear/actualizar contacto en GHL"""
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    locationId: str


class GHLOportunidad(BaseModel):
    """Modelo para crear oportunidad en GHL"""
    pipelineId: str
    locationId: str
    name: str
    status: str = "open"
    monetaryValue: Optional[float] = None
    pipelineStageId: str
    contactId: str


class GHLClient:
    """Cliente HTTP para GHL API v2"""
    
    def __init__(self):
        self.base_url = "https://services.leadconnectorhq.com"
        self.token = settings.ghl_token
        self.location_id = settings.ghl_location_id
        self.pipeline_id = settings.ghl_pipeline_id
        self.stage_id = settings.ghl_stage_venta_realizada_id
        self.timeout = 30.0
        
    def _get_headers(self) -> Dict[str, str]:
        """Headers para peticiones a GHL"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Version": "v3",  # API v3 según documentación oficial
            "Content-Type": "application/json"
        }
    
    def agregar_tag_contacto(self, contacto_id: str, tag: str) -> bool:
        """
        Agrega un tag a un contacto en GHL
        
        Args:
            contacto_id: ID del contacto en GHL
            tag: Nombre del tag a agregar
            
        Returns:
            True si se agregó correctamente, False si falló
        """
        if settings.dry_run:
            logger.info(f"[DRY_RUN] Agregar tag '{tag}' al contacto {contacto_id}")
            return True
        
        url = f"{self.base_url}/contacts/{contacto_id}/tags"
        
        payload = {
            "tags": [tag]
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Tag '{tag}' agregado al contacto {contacto_id}")
                    return True
                else:
                    logger.error(f"Error agregar tag: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Excepción agregar tag: {e}", exc_info=True)
            return False
    
    def upsert_contacto(self, telefono: str, nombre: Optional[str] = None) -> Optional[str]:
        """
        Crea o actualiza contacto en GHL por teléfono
        
        Args:
            telefono: Teléfono en formato E.164
            nombre: Nombre opcional del contacto
            
        Returns:
            ID del contacto o None si falla
        """
        if settings.dry_run:
            logger.info(f"[DRY_RUN] Upsert contacto: {telefono}, nombre: {nombre}")
            return "dry_run_contact_id"
        
        url = f"{self.base_url}/contacts/upsert"
        
        contacto = GHLContacto(
            phone=telefono,
            name=nombre,
            locationId=self.location_id
        )
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    headers=self._get_headers(),
                    json=contacto.model_dump(exclude_none=True)
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    contact_id = data.get("contact", {}).get("id")
                    logger.info(f"Contacto upsert exitoso: {contact_id}")
                    return contact_id
                else:
                    logger.error(f"Error upsert contacto: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Excepción upsert contacto: {e}", exc_info=True)
            return None
    
    def buscar_oportunidad_por_nombre(self, nombre_oportunidad: str) -> Optional[str]:
        """
        Busca oportunidad por nombre en el pipeline
        
        Args:
            nombre_oportunidad: Nombre de la oportunidad (ej: "Venta ORD-001")
            
        Returns:
            ID de la oportunidad si existe, None si no existe
        """
        if settings.dry_run:
            logger.info(f"[DRY_RUN] Buscar oportunidad: {nombre_oportunidad}")
            return None  # En DRY_RUN siempre retorna None para simular que no existe
        
        url = f"{self.base_url}/opportunities/search"
        
        params = {
            "locationId": self.location_id,  # camelCase según API GHL
            "pipelineId": self.pipeline_id,
            "q": nombre_oportunidad
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    opportunities = data.get("opportunities", [])
                    
                    # Buscar coincidencia exacta por nombre
                    for opp in opportunities:
                        if opp.get("name") == nombre_oportunidad:
                            opp_id = opp.get("id")
                            logger.info(f"Oportunidad encontrada: {opp_id}")
                            return opp_id
                    
                    logger.info(f"Oportunidad '{nombre_oportunidad}' no encontrada")
                    return None
                else:
                    logger.warning(f"Error buscar oportunidad: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Excepción buscar oportunidad: {e}", exc_info=True)
            return None
    
    def crear_oportunidad(
        self, 
        contacto_id: str, 
        nombre_oportunidad: str,
        valor: float
    ) -> Optional[str]:
        """
        Crea oportunidad en GHL
        
        Args:
            contacto_id: ID del contacto en GHL
            nombre_oportunidad: Nombre de la oportunidad (ej: "Venta ORD-001")
            valor: Valor monetario de la venta
            
        Returns:
            ID de la oportunidad creada o None si falla
        """
        if settings.dry_run:
            logger.info(
                f"[DRY_RUN] Crear oportunidad: {nombre_oportunidad}, "
                f"contacto: {contacto_id}, valor: {valor}"
            )
            return "dry_run_opportunity_id"
        
        url = f"{self.base_url}/opportunities/"
        
        oportunidad = GHLOportunidad(
            pipelineId=self.pipeline_id,
            locationId=self.location_id,
            name=nombre_oportunidad,
            status="open",
            monetaryValue=valor,
            pipelineStageId=self.stage_id,
            contactId=contacto_id
        )
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    headers=self._get_headers(),
                    json=oportunidad.model_dump(exclude_none=True)
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    opp_id = data.get("opportunity", {}).get("id") or data.get("id")
                    logger.info(f"Oportunidad creada: {opp_id}")
                    return opp_id
                else:
                    logger.error(f"Error crear oportunidad: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Excepción crear oportunidad: {e}", exc_info=True)
            return None


# Instancia global
ghl_client = GHLClient()
