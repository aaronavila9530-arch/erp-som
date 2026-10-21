# =====================================================
# DATABASE — ERP-SOM DESKTOP
# Compatible con:
# ✔ Desarrollo local
# ✔ PyInstaller EXE
# ✔ Railway PostgreSQL (SSL)
# ✔ FastAPI (get_db dependency)
# =====================================================

import os
import time
import threading
import psycopg2
from psycopg2 import pool
from psycopg2 import OperationalError

# =====================================================
# DATABASE URL
# Configuracion obligatoria mediante variable de entorno.
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL")

def _database_url():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL debe configurarse en el entorno del servidor")
    return DATABASE_URL

# =====================================================
# CONFIGURACIÓN
# =====================================================

MAX_RETRIES = 5
RETRY_DELAY = 3
CONNECT_TIMEOUT = 10

_connection_pool = None
_pool_init_lock = threading.Lock()
POOL_WAIT_TIMEOUT = 5.0


# =====================================================
# INICIALIZAR POOL
# =====================================================

def _initialize_pool():
    global _connection_pool

    with _pool_init_lock:
        if _connection_pool is None:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=_database_url(),
                connect_timeout=CONNECT_TIMEOUT,
                sslmode="require"
            )


# =====================================================
# OBTENER CONEXIÓN (CON REINTENTOS)
# =====================================================

def get_conn():
    _initialize_pool()

    last_error = None
    deadline = time.monotonic() + POOL_WAIT_TIMEOUT

    for attempt in range(MAX_RETRIES):
        try:
            while True:
                try:
                    return _connection_pool.getconn()
                except pool.PoolError as exc:
                    if str(exc) != "connection pool exhausted" or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)

        except OperationalError as e:
            last_error = e
            print(f"⚠ DB intento {attempt+1}/{MAX_RETRIES} falló...")
            time.sleep(RETRY_DELAY)

    raise last_error


def release_conn(conn):
    if _connection_pool and conn:
        discard = bool(conn.closed)
        if not discard:
            try:
                conn.rollback()
            except psycopg2.Error:
                discard = True
        _connection_pool.putconn(conn, close=discard)


def probe_database():
    """Probe the application's pool, not a separate healthy-looking connection.

    No retry/wait on pool exhaustion; the monitor can switch away immediately.
    The connect timeout still applies when opening a new connection.
    """
    conn = None
    ready = False
    try:
        _initialize_pool()
        conn = _connection_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '1500ms'")
            cur.execute("SELECT NOT pg_is_in_recovery(), current_setting('transaction_read_only') = 'off'")
            row = cur.fetchone()
            ready = bool(row and row[0] and row[1])
    except Exception:
        ready = False
    finally:
        if conn is not None:
            try:
                release_conn(conn)
            except Exception:
                ready = False
    return ready


# =====================================================
# CONEXIÓN DIRECTA (legacy)
# =====================================================

def connect():
    for attempt in range(MAX_RETRIES):
        try:
            return psycopg2.connect(
                _database_url(),
                connect_timeout=CONNECT_TIMEOUT,
                sslmode="require"
            )
        except OperationalError:
            time.sleep(RETRY_DELAY)

    raise OperationalError("No se pudo conectar a la base de datos.")


# =====================================================
# FUNCIÓN SQL GENÉRICA
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
# FASTAPI DEPENDENCY (IMPORTANTE)
# =====================================================

def get_db():
    conn = None
    try:
        conn = get_conn()
        yield conn
    finally:
        if conn:
            release_conn(conn)
