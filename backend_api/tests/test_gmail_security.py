import base64
import hashlib
import json
import io
import os
from pathlib import Path
import sys
import time
import shutil
import subprocess
import re
import unittest
import zipfile
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bcrypt
import pyotp
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from database import get_db
from routers import gmail_fiscal, user_admin
from security import gmail_access as access
from services import gmail_fiscal_service as service


class GmailSecurityTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "CREDENTIAL_ENCRYPTION_KEY": Fernet.generate_key().decode(),
            "GOOGLE_CLIENT_ID": "test-client", "GOOGLE_CLIENT_SECRET": "test-secret",
            "GOOGLE_REDIRECT_URI": "https://example.test/callback",
            "GMAIL_ACCOUNT_PROFILES": json.dumps([
                {"account_email": "gastos@example.test", "company_code": "MSL-CR"},
                {"account_email": "operations@example.test", "company_code": "MCI-CR"}]),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.user = {"usuario": "admin", "rol": "master", "activo": True,
                     "totp_enabled": True, "totp_secret": pyotp.random_base32(),
                     "pass_hash": bcrypt.hashpw(b"test-password", bcrypt.gensalt(rounds=4)).decode()}
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        app = FastAPI()
        app.include_router(gmail_fiscal.router)
        app.include_router(user_admin.router)
        app.dependency_overrides[get_db] = lambda: self.conn
        self.client = TestClient(app)

    def token(self, company="MSL-CR", age=0):
        claims = {"purpose": "gmail-admin", "user": "admin", "company": company,
                  "stamp": access._stamp(self.user)}
        return access._cipher().encrypt_at_time(json.dumps(claims).encode(), int(time.time()) - age).decode()

    def test_all_mailbox_routes_reject_anonymous_and_forged_headers(self):
        paths = [("GET", "/status"), ("GET", "/messages"), ("GET", "/messages/1/attachments"),
                 ("POST", "/sync"), ("POST", "/oauth/start"), ("PUT", "/automation"), ("DELETE", "/connection")]
        for method, path in paths:
            with self.subTest(path=path):
                response = self.client.request(method, "/accounting/tax/gmail" + path,
                    headers={"X-User": "admin", "X-Role": "master", "X-User-Role": "master"},
                    json={"enabled": True})
                self.assertEqual(response.status_code, 401)
        self.cur.execute.assert_not_called()

    def test_user_creation_cannot_bypass_mailbox_security(self):
        response = self.client.post("/admin/users", headers={"X-User": "admin", "X-User-Role": "master"}, json={})
        self.assertEqual(response.status_code, 401)

    def test_invalid_expired_and_legacy_tokens_rejected(self):
        for token in ("LOCAL_SESSION", "garbage", self.token(age=901)):
            with self.assertRaises(HTTPException) as ctx:
                access.require_gmail_admin("Bearer " + token, "MSL-CR", self.conn)
            self.assertEqual(ctx.exception.status_code, 401)

    def test_role_password_and_company_revalidated(self):
        token = self.token()
        with patch.object(access, "_user", return_value=self.user):
            self.assertEqual(access.require_gmail_admin("Bearer " + token, "MSL-CR", self.conn)["user"], "admin")
            with self.assertRaises(HTTPException) as ctx:
                access.require_gmail_admin("Bearer " + token, "MCI-CR", self.conn)
            self.assertEqual(ctx.exception.status_code, 403)
            self.user["rol"] = "user"
            with self.assertRaises(HTTPException):
                access.require_gmail_admin("Bearer " + token, "MSL-CR", self.conn)
            self.user["rol"] = "master"
            self.user["pass_hash"] = "changed"
            with self.assertRaises(HTTPException):
                access.require_gmail_admin("Bearer " + token, "MSL-CR", self.conn)

    def test_company_mailbox_allowlist(self):
        principal = {"company": "MSL-CR"}
        self.assertEqual(gmail_fiscal._account(None, principal), "gastos@example.test")
        for email in ("attacker@example.test", "operations@example.test"):
            with self.assertRaises(HTTPException):
                gmail_fiscal._account(email, principal)
        with self.assertRaises(ValueError):
            service._account_profile("attacker@example.test")

    def test_status_and_attachments_are_tenant_scoped(self):
        with patch.object(access, "_user", return_value=self.user), patch.object(gmail_fiscal, "ensure_schema"):
            self.cur.fetchall.return_value = []
            headers = {"Authorization": "Bearer " + self.token(), "X-Company-Code": "MSL-CR"}
            response = self.client.get("/accounting/tax/gmail/status", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertIn("account_email=ANY", self.cur.execute.call_args.args[0])
            self.assertEqual(self.cur.execute.call_args.args[1], (["gastos@example.test"],))
            response = self.client.get("/accounting/tax/gmail/messages/1/attachments", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("account_email=ANY", self.cur.execute.call_args.args[0])

    def test_step_up_requires_password_and_totp(self):
        with patch.object(access, "ensure_security_schema"), patch.object(access, "_user", return_value=self.user):
            self.cur.fetchone.return_value = (1,)
            with self.assertRaises(HTTPException):
                access.issue_session(self.conn, "admin", "wrong", "000000", "MSL-CR", "127.0.0.1")
            code = pyotp.TOTP(self.user["totp_secret"]).now()
            data = access.issue_session(self.conn, "admin", "test-password", code, "MSL-CR", "127.0.0.1")
            self.assertEqual(data["expires_in"], 900)
            self.assertEqual(access.require_gmail_admin("Bearer " + data["access_token"], "MSL-CR", self.conn)["user"], "admin")

    def test_attempt_limit_and_totp_replay(self):
        with patch.object(access, "ensure_security_schema"), patch.object(access, "_user", return_value=self.user):
            self.cur.fetchone.return_value = (99,)
            with self.assertRaises(HTTPException) as ctx:
                access.issue_session(self.conn, "admin", "test-password", "000000", "MSL-CR", "127.0.0.1")
            self.assertEqual(ctx.exception.status_code, 429)
            self.cur.fetchone.side_effect = [(1,), (1,), None]
            with self.assertRaises(HTTPException) as ctx:
                access.issue_session(self.conn, "admin", "test-password", pyotp.TOTP(self.user["totp_secret"]).now(), "MSL-CR", "127.0.0.1")
            self.assertEqual(ctx.exception.status_code, 401)

    def test_oauth_pkce_and_hashed_state(self):
        with patch.object(service, "ensure_schema"):
            url = service.create_oauth_url(self.conn, "admin", "gastos@example.test")
        params = parse_qs(urlparse(url).query)
        values = self.cur.execute.call_args.args[1]
        self.assertEqual(values[0], hashlib.sha256(params["state"][0].encode()).hexdigest())
        verifier = service.decrypt_token(values[3])
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        self.assertEqual(params["code_challenge"], [challenge])
        self.assertEqual(params["code_challenge_method"], ["S256"])

    def test_callback_replay_does_not_exchange_token(self):
        self.cur.fetchone.return_value = None
        with patch.object(service, "ensure_schema"), patch.object(service.requests, "post") as post:
            with self.assertRaises(RuntimeError):
                service.complete_oauth(self.conn, "already-used", "secret-code")
            post.assert_not_called()

    def test_callback_exchanges_pkce_and_encrypts_refresh_token(self):
        self.cur.fetchone.return_value = {"account_email": "gastos@example.test", "requested_by": "admin",
                                          "encrypted_verifier": service.encrypt_token("test-verifier")}
        with patch.object(service, "ensure_schema"), patch.object(access, "_user", return_value=self.user), \
             patch.object(service.requests, "post") as post, patch.object(service, "_api", return_value={"emailAddress": "gastos@example.test"}):
            post.return_value.json.return_value = {"refresh_token": "test-refresh", "access_token": "test-access"}
            self.assertEqual(service.complete_oauth(self.conn, "state", "code"), "gastos@example.test")
            self.assertEqual(post.call_args.kwargs["data"]["code_verifier"], "test-verifier")
        updates = [call.args[1] for call in self.cur.execute.call_args_list if "SET encrypted_refresh_token=" in call.args[0]]
        self.assertEqual(service.decrypt_token(updates[0][0]), "test-refresh")

    def test_callback_rejects_disabled_administrator(self):
        self.cur.fetchone.return_value = {"account_email": "gastos@example.test", "requested_by": "admin",
                                          "encrypted_verifier": service.encrypt_token("test-verifier")}
        with patch.object(service, "ensure_schema"), patch.object(access, "_user", return_value=None), \
             patch.object(service.requests, "post") as post:
            with self.assertRaises(ValueError):
                service.complete_oauth(self.conn, "state", "code")
            post.assert_not_called()

    def test_oversized_attachment_rejected_before_download(self):
        with patch.object(service, "_api") as api:
            with self.assertRaises(ValueError):
                service._attachment_bytes("token", "message", {"body": {"size": service.MAX_ATTACHMENT_BYTES + 1, "attachmentId": "id"}})
            api.assert_not_called()

    def test_zip_total_uncompressed_budget(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
            out.writestr("one.xml", b"x" * 600)
            out.writestr("two.xml", b"x" * 600)
        with patch.object(service, "MAX_ATTACHMENT_BYTES", 1000):
            with self.assertRaises(ValueError):
                service._xml_members("invoices.zip", archive.getvalue())

    def test_missing_security_key_and_database_configuration_fail_closed(self):
        import database
        with patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": ""}):
            with self.assertRaises(HTTPException):
                access._cipher()
        with patch.object(database, "DATABASE_URL", None):
            with self.assertRaises(RuntimeError):
                database._database_url()

    def test_callback_does_not_disclose_provider_errors(self):
        with patch.object(gmail_fiscal, "complete_oauth", side_effect=RuntimeError("secret-provider-detail")):
            response = self.client.get("/accounting/tax/gmail/oauth/callback?state=x&code=y")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("secret-provider-detail", response.text)
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")

    def test_browser_script_syntax(self):
        from routers.som_web import som_web_home
        node = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
        if not Path(node).exists():
            self.skipTest("Node is not available")
        html = som_web_home().body.decode()
        js = re.findall(r"<script>(.*?)</script>", html, re.S)[0]
        result = subprocess.run([node, "-e", "new (require('vm').Script)(require('fs').readFileSync(0,'utf8'));"],
                                input=js, text=True, encoding="utf-8", capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
