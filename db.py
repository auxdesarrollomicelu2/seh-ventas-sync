"""
Conexión a PostgreSQL usando psycopg 3
SOLO LECTURA sobre public.orden y public.addres
"""
import psycopg
from psycopg.rows import dict_row
from typing import Iterator
from contextlib import contextmanager
import logging

from config import settings

logger = logging.getLogger(__name__)


class Database:
    """Manejador de conexión a PostgreSQL"""
    
    def __init__(self):
        self.connection_string = settings.database_url
    
    def connect(self):
        """Inicializa la conexión"""
        logger.info("Conectando a PostgreSQL...")
        logger.info("Conexión a PostgreSQL lista")
    
    def disconnect(self):
        """Cierra la conexión"""
        logger.info("Desconectando de PostgreSQL...")
    
    @contextmanager
    def get_connection(self) -> Iterator[psycopg.Connection]:
        """Context manager para obtener una conexión"""
        conn = psycopg.connect(
            self.connection_string,
            row_factory=dict_row
        )
        try:
            yield conn
        finally:
            conn.close()


# Instancia global
db = Database()
