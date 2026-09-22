"""
Normalización de números telefónicos a formato E.164 colombiano
"""
import re
import logging

logger = logging.getLogger(__name__)


def normalizar_telefono_colombiano(telefono: str) -> str:
    """
    Normaliza un número telefónico colombiano a formato E.164: +57XXXXXXXXXX
    
    Args:
        telefono: Número de teléfono en cualquier formato
        
    Returns:
        Número en formato E.164 (+57 seguido de 10 dígitos)
        
    Raises:
        ValueError: Si el número no es válido para Colombia
    """
    if not telefono:
        raise ValueError("Teléfono vacío")
    
    # Remover todos los caracteres no numéricos excepto el +
    limpio = re.sub(r'[^\d+]', '', telefono)
    
    # Si ya tiene +57, validar que tenga 10 dígitos después
    if limpio.startswith('+57'):
        digitos = limpio[3:]
        if len(digitos) == 10 and digitos.isdigit():
            return limpio
        raise ValueError(f"Número con +57 no tiene 10 dígitos: {len(digitos)}")
    
    # Si empieza con 57, agregar el +
    if limpio.startswith('57') and len(limpio) == 12:
        return f"+{limpio}"
    
    # Si son 10 dígitos, agregar +57
    if len(limpio) == 10 and limpio.isdigit():
        return f"+57{limpio}"
    
    # Cualquier otro caso es inválido
    raise ValueError(f"Formato de teléfono no válido para Colombia: {len(limpio)} dígitos")


def enmascarar_telefono(telefono: str) -> str:
    """
    Enmascara un teléfono para logs (muestra solo últimos 4 dígitos)
    
    Args:
        telefono: Número de teléfono
        
    Returns:
        Teléfono enmascarado (ej: +57******1234)
    """
    if not telefono or len(telefono) < 4:
        return "***"
    
    return f"{telefono[:-4]}****{telefono[-4:]}"
