# =====================================================
# DATABASE — ERP-SOM (BLINDADO FRONTEND DIRECTO RAILWAY)
# Compatible con:
# • Tkinter Desktop
# • Railway Public TCP Proxy
# • SSL obligatorio
# • Cold start
# • Reconexión automática
# =====================================================

import os
import time
import psycopg2
from psycopg2 import pool, OperationalError

# =====================================================
# DATABASE URL
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL no está definida.")

# Forzar SSL si no viene en la URL
if "sslmode=" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

# =====================================================
# CONFIGURACIÓN
# =====================================================

MAX_RETRIES = 5
RETRY_DELAY = 3
CONNECT_TIMEOUT = 10

_connection_pool = None


# =====================================================
# CREAR / RECREAR POOL
# =====================================================

def _create_pool():
    return pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DATABASE_URL,
        connect_timeout=CONNECT_TIMEOUT
    )


def _initialize_pool():
    global _connection_pool

    if _connection_pool is None:
        _connection_pool = _create_pool()


def _reset_pool():
    global _connection_pool
    try:
        if _connection_pool:
            _connection_pool.closeall()
    except Exception:
        pass
    _connection_pool = _create_pool()


# =====================================================
# OBTENER CONEXIÓN (CON VALIDACIÓN REAL)
# =====================================================

def get_conn():
    global _connection_pool

    _initialize_pool()
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            conn = _connection_pool.getconn()

            # Validar que conexión sigue viva
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

            return conn

        except Exception as e:
            last_error = e
            print(f"⚠ DB intento {attempt+1}/{MAX_RETRIES} falló: {e}")

            time.sleep(RETRY_DELAY)
            _reset_pool()

    raise OperationalError(f"No se pudo conectar a la base de datos: {last_error}")


def release_conn(conn):
    global _connection_pool
    if _connection_pool and conn:
        try:
            _connection_pool.putconn(conn)
        except Exception:
            pass


# =====================================================
# CONEXIÓN DIRECTA (SIN POOL)
# =====================================================

def connect():
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            conn = psycopg2.connect(
                DATABASE_URL,
                connect_timeout=CONNECT_TIMEOUT
            )

            with conn.cursor() as cur:
                cur.execute("SELECT 1")

            return conn

        except Exception as e:
            last_error = e
            print(f"⚠ Connect intento {attempt+1}/{MAX_RETRIES} falló: {e}")
            time.sleep(RETRY_DELAY)

    raise OperationalError(f"No se pudo conectar: {last_error}")


# =====================================================
# SQL LEGACY
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
# DEPENDENCY GENERATOR (SI ALGÚN DÍA USAS FASTAPI)
# =====================================================

def get_db():
    conn = None
    try:
        conn = get_conn()
        yield conn
    finally:
        if conn:
            release_conn(conn)
