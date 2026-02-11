# database.py
import os
import time
import psycopg2
from psycopg2 import pool
from psycopg2 import OperationalError

# =====================================================
# DATABASE URL (NUNCA HARDCODEAR EN PRODUCCIÓN)
# Se toma de variables de entorno (Railway / local)
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL no está definida en variables de entorno."
    )

# =====================================================
# CONFIGURACIÓN DE REINTENTOS (Railway cold start safe)
# =====================================================

MAX_RETRIES = 5
RETRY_DELAY = 3  # segundos
CONNECT_TIMEOUT = 10

# =====================================================
# CONNECTION POOL (ESTABLE EN PRODUCCIÓN)
# =====================================================

_connection_pool = None


def _initialize_pool():
    global _connection_pool

    if _connection_pool is None:
        _connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL,
            sslmode="require",
            connect_timeout=CONNECT_TIMEOUT
        )


# =====================================================
# OBTENER CONEXIÓN (BLINDADO CON REINTENTOS)
# =====================================================

def get_conn():
    _initialize_pool()

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            conn = _connection_pool.getconn()
            return conn

        except OperationalError as e:
            last_error = e
            print(f"⚠ DB intento {attempt+1}/{MAX_RETRIES} falló. Reintentando...")
            time.sleep(RETRY_DELAY)

    raise last_error


def release_conn(conn):
    if _connection_pool and conn:
        _connection_pool.putconn(conn)


# =====================================================
# CONEXIÓN DIRECTA (uso puntual / legacy)
# =====================================================

def connect():
    for attempt in range(MAX_RETRIES):
        try:
            return psycopg2.connect(
                DATABASE_URL,
                sslmode="require",
                connect_timeout=CONNECT_TIMEOUT
            )
        except OperationalError:
            time.sleep(RETRY_DELAY)

    raise OperationalError("No se pudo conectar a la base de datos.")


# =====================================================
# FUNCIÓN SQL GENÉRICA (LEGACY)
# =====================================================

def sql(query, params=None, fetch=False):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(query, params)

        if fetch:
            data = cur.fetchall()
            conn.commit()
            return data

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ Error SQL:", e)
        raise

    finally:
        if conn:
            release_conn(conn)


# =====================================================
# FASTAPI DEPENDENCY (RECOMENDADO)
# =====================================================

def get_db():
    conn = None
    try:
        conn = get_conn()
        yield conn
    finally:
        if conn:
            release_conn(conn)
