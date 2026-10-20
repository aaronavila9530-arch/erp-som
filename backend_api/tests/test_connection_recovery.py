import importlib.util
import ast
import queue
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("recovery_database", ROOT / "backend_api/database.py")
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)


class PoolTests(unittest.TestCase):
    def tearDown(self):
        db._connection_pool = None

    def test_initialization_is_thread_safe(self):
        db._connection_pool = None
        with patch.object(db, "DATABASE_URL", "test"), patch.object(db.pool, "ThreadedConnectionPool") as factory:
            threads = [threading.Thread(target=db._initialize_pool) for _ in range(40)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            factory.assert_called_once()

    def test_hundreds_of_releases_rollback_and_return(self):
        db._connection_pool = Mock()
        conn = Mock(closed=0)
        for _ in range(500):
            db.release_conn(conn)
        self.assertEqual(conn.rollback.call_count, 500)
        self.assertEqual(db._connection_pool.putconn.call_count, 500)
        db._connection_pool.putconn.assert_called_with(conn, close=False)

    def test_closed_and_broken_connections_are_discarded(self):
        db._connection_pool = Mock()
        conn = Mock(closed=1)
        db.release_conn(conn)
        conn.rollback.assert_not_called()
        db._connection_pool.putconn.assert_called_with(conn, close=True)
        conn = Mock(closed=0)
        conn.rollback.side_effect = db.OperationalError("lost connection")
        db.release_conn(conn)
        db._connection_pool.putconn.assert_called_with(conn, close=True)

    def test_temporary_exhaustion_waits_for_release(self):
        conn = Mock()
        db._connection_pool = Mock()
        db._connection_pool.getconn.side_effect = [db.pool.PoolError("connection pool exhausted"), conn]
        with patch.object(db.time, "sleep"):
            self.assertIs(db.get_conn(), conn)

    def test_exhaustion_has_deadline(self):
        db._connection_pool = Mock()
        db._connection_pool.getconn.side_effect = db.pool.PoolError("connection pool exhausted")
        with patch.object(db, "POOL_WAIT_TIMEOUT", 0):
            with self.assertRaises(db.pool.PoolError):
                db.get_conn()

    def test_dependency_returns_connection_on_error(self):
        conn = Mock()
        with patch.object(db, "get_conn", return_value=conn), patch.object(db, "release_conn") as release:
            gen = db.get_db()
            self.assertIs(next(gen), conn)
            with self.assertRaises(ValueError):
                gen.throw(ValueError("request failed"))
            release.assert_called_once_with(conn)

    def test_home_preview_returns_lease_not_close(self):
        tree = ast.parse((ROOT / "backend_api/services/home_payables.py").read_text(encoding="utf-8"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_biweekly_home_rows")
        cleanup = next(n for n in fn.body if isinstance(n, ast.Try)).finalbody
        self.assertIn("database.release_conn(conn)", ast.unparse(ast.Module(body=cleanup, type_ignores=[])))


class DesktopSaveTests(unittest.TestCase):
    def test_network_wait_keeps_main_thread_available(self):
        tree = ast.parse((ROOT / "Modulos/Servicios/popup_servicio.py").read_text(encoding="utf-8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_advance_save")
        namespace = {"queue": queue, "threading": threading, "messagebox": Mock()}
        exec(compile(ast.Module(body=[method], type_ignores=[]), "<save-test>", "exec"), namespace)
        ui = Mock()
        ui._advance_save = lambda value=None, error=None: namespace["_advance_save"](ui, value, error)
        callbacks = []
        ui.after.side_effect = lambda delay, fn: callbacks.append(fn)
        ui.winfo_exists.return_value = True
        ui._save_widget_states = []
        started, finish, completed = threading.Event(), threading.Event(), threading.Event()
        ids = []

        def operation():
            ids.append(threading.get_ident())
            started.set()
            finish.wait(2)
            completed.set()
            return "saved"

        def flow():
            result = yield operation
            ids.append(threading.get_ident())
            self.assertEqual(result, "saved")

        ui._save_flow = flow()
        main_id = threading.get_ident()
        try:
            ui._advance_save()
            self.assertTrue(started.wait(1))
            self.assertFalse(completed.is_set())
            self.assertTrue(callbacks)
            callbacks.pop(0)()
            self.assertTrue(callbacks)  # Poll reschedules rather than blocking.
        finally:
            finish.set()
        self.assertTrue(completed.wait(1))
        for _ in range(1000):
            if ui._saving is False:
                break
            callbacks.pop(0)()
        self.assertNotEqual(ids[0], main_id)
        self.assertEqual(ids[1], main_id)
        self.assertFalse(ui._saving)


if __name__ == "__main__":
    unittest.main()
