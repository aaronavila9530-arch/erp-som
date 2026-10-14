import email
from email.message import EmailMessage
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import spacemail_fiscal as imap
from services import gmail_fiscal_service as gmail
from routers import gmail_fiscal as router
from fastapi import HTTPException


class SpacemailTests(unittest.TestCase):
    def mailbox(self, folders=None):
        mail = MagicMock()
        mail.list.return_value = ("OK", folders or [b'(\\HasNoChildren) "/" "INBOX/FE recibidas"'])
        mail.select.return_value = ("OK", [b"1"])
        mail.response.return_value = ("UIDVALIDITY", [b"123"])
        return mail

    def test_readonly_folder_selection(self):
        mail = self.mailbox()
        self.assertEqual(imap.select_received(mail), ("INBOX/FE recibidas", "123"))
        mail.select.assert_called_once_with('"INBOX/FE recibidas"', readonly=True)

    def test_dot_delimiter(self):
        mail = self.mailbox([b'(\\HasNoChildren) "." "INBOX.FE recibidas"'])
        self.assertEqual(imap.select_received(mail)[0], "INBOX.FE recibidas")

    def test_missing_and_ambiguous_folders_rejected(self):
        for folders in ([b'() "/" "INBOX"'], [b'() "/" "FE recibidas"', b'() "/" "INBOX/FE recibidas"']):
            with self.assertRaises(ValueError):
                imap.select_received(self.mailbox(folders))

    def test_tls_fixed_host_and_login(self):
        mail = self.mailbox()
        with patch.object(imap.imaplib, "IMAP4_SSL", return_value=mail) as factory:
            imap.connect("secret")
        self.assertEqual(factory.call_args.args, ("mail.spacemail.com", 993))
        self.assertTrue(factory.call_args.kwargs["ssl_context"].check_hostname)
        mail.login.assert_called_once_with(imap.ACCOUNT, "secret")

    def test_fetch_does_not_mark_read(self):
        mail = self.mailbox()
        mail.uid.side_effect = [("OK", [b'1 (RFC822.SIZE 50)']), ("OK", [(b"1", b"Subject: invoice\r\n\r\nbody")])]
        self.assertEqual(imap.fetch_message(mail, b"5")["Subject"], "invoice")
        self.assertEqual(mail.uid.call_args.args, ("fetch", b"5", "(BODY.PEEK[])"))

    def test_oversized_message_not_downloaded(self):
        mail = self.mailbox()
        mail.uid.return_value = ("OK", [b'1 (RFC822.SIZE 999999999)'])
        with self.assertRaises(ValueError):
            imap.fetch_message(mail, b"1")
        self.assertEqual(mail.uid.call_count, 1)

    def test_invoice_precedes_hacienda_response_and_routes_mci(self):
        msg = EmailMessage()
        msg.set_content("Invoice")
        msg.add_attachment(b"<MensajeHacienda/>", maintype="application", subtype="xml", filename="response.xml")
        msg.add_attachment(b"<FacturaElectronica/>", maintype="application", subtype="xml", filename="invoice.xml")
        with patch.object(gmail, "_process_xml", return_value=("IMPORTED", 1)) as process:
            self.assertEqual(imap.import_message(MagicMock(), 7, msg), (2, 2, 0, 0))
        self.assertEqual(process.call_args_list[0].args[2], "invoice.xml")
        self.assertTrue(all(call.args[-1] == "MCI-CR" for call in process.call_args_list))

    def test_password_not_persisted_if_connection_fails(self):
        conn = MagicMock()
        with patch.object(gmail, "ensure_schema"), patch.object(gmail, "encrypt_token", return_value="encrypted"), patch.object(imap, "connect", side_effect=ValueError):
            with self.assertRaises(ValueError):
                imap.configure(conn, "secret", "admin")
        conn.cursor.assert_not_called()

    def test_config_stores_only_encrypted_password(self):
        conn, mail = MagicMock(), MagicMock()
        with patch.object(gmail, "ensure_schema"), patch.object(gmail, "encrypt_token", return_value="encrypted"), patch.object(imap, "connect", return_value=(mail, "INBOX/FE recibidas", "123")):
            imap.configure(conn, "secret", "admin")
        calls = conn.cursor.return_value.__enter__.return_value.execute.call_args_list
        self.assertEqual(calls[0].args[1], ("encrypted", "admin", imap.ACCOUNT))

    def test_msl_cannot_configure_mci(self):
        with self.assertRaises(HTTPException) as ctx:
            router.connect_spacemail(router.SpacemailConnect(password="secret"), {"company": "MSL-CR"}, MagicMock())
        self.assertEqual(ctx.exception.status_code, 403)

    def test_xtravon_cannot_start_google_oauth(self):
        with self.assertRaises(ValueError):
            gmail.create_oauth_url(MagicMock(), "admin", imap.ACCOUNT)

    def test_sync_skips_existing_uid_and_uses_new_validity(self):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect = [{"locked": True}, {"encrypted_imap_password": "cipher"}, {"id": 7}]
        cur.fetchall.return_value = [{"gmail_message_id": "imap:INBOX/FE recibidas:123:1"}]
        mail = self.mailbox()
        mail.uid.return_value = ("OK", [b"1 2"])
        with patch.object(gmail, "ensure_schema"), patch.object(gmail, "decrypt_token", return_value="secret"), patch.object(imap, "connect", return_value=(mail, "INBOX/FE recibidas", "123")), patch.object(imap, "fetch_message", return_value=email.message_from_string("Subject: invoice\n\n")) as fetch, patch.object(imap, "import_message", return_value=(1, 1, 0, 0)):
            result = imap.sync(conn)
        fetch.assert_called_once_with(mail, b"2")
        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["company_code"], "MCI-CR")
        mail.logout.assert_called_once()

    def test_sync_failure_rolls_back_and_records_review(self):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect = [{"locked": True}, {"encrypted_imap_password": "cipher"}, {"id": 7}]
        cur.fetchall.return_value = []
        mail = self.mailbox()
        mail.uid.return_value = ("OK", [b"2"])
        with patch.object(gmail, "ensure_schema"), patch.object(gmail, "decrypt_token", return_value="secret"), patch.object(imap, "connect", return_value=(mail, "INBOX/FE recibidas", "123")), patch.object(imap, "fetch_message", side_effect=ValueError("private error")):
            result = imap.sync(conn)
        self.assertEqual(result["review"], 1)
        conn.rollback.assert_called_once()
        self.assertNotIn("private error", str(cur.execute.call_args_list))

    def test_concurrent_sync_is_not_run(self):
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchone.return_value = {"locked": False}
        with patch.object(gmail, "ensure_schema"), patch.object(imap, "connect") as connect:
            self.assertEqual(imap.sync(conn), {"status": "busy"})
        connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
