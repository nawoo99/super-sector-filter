#!/usr/bin/env python3
"""Local-only tests for the c40 Gmail terminal notifier; sends no email."""
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

import scenario7_v14_email_notify as notify


class EmailNotifyTest(unittest.TestCase):
    def test_app_password_normalization_and_rejection(self):
        self.assertEqual(notify.normalize_password('abcd efgh ijkl mnop'),
                         'abcdefghijklmnop')
        for value in ('short', 'abcdefghijklmnopq', 'abcdefghijklmn!p'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                notify.normalize_password(value)

    def test_private_credential_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / 'config'
            with patch.object(notify, 'SECRET_DIRECTORY', directory), \
                    patch.object(notify, 'SECRET_PATH', directory / 'password'):
                notify.save_password('abcd efgh ijkl mnop')
                self.assertEqual(notify.read_password(), 'abcdefghijklmnop')
                self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((directory / 'password').stat().st_mode),
                                 0o600)

    def test_terminal_message_distinguishes_outcomes(self):
        complete, body = notify.terminal_message(
            {'state': 'COMPLETE', 'completed': [{}] * 46})
        stopped, stop_body = notify.terminal_message(
            {'state': 'STOPPED_FOR_DIAGNOSIS', 'completed': [{}] * 4})
        self.assertIn('complete', complete)
        self.assertIn('46/46', body)
        self.assertIn('stopped', stopped)
        self.assertIn('4/46', stop_body)
        self.assertIn('Do not treat it as complete', stop_body)

    def test_smtp_uses_tls_and_self_address(self):
        with patch.object(notify.smtplib, 'SMTP_SSL') as constructor:
            server = constructor.return_value.__enter__.return_value
            server.send_message.return_value = {}
            notify.send('subject', 'body', 'abcdefghijklmnop')
            args, kwargs = constructor.call_args
            self.assertEqual(args[:2], ('smtp.gmail.com', 465))
            self.assertIsNotNone(kwargs['context'])
            server.login.assert_called_once_with(notify.ADDRESS, 'abcdefghijklmnop')
            message = server.send_message.call_args.args[0]
            self.assertEqual(message['To'], notify.ADDRESS)
            self.assertEqual(message['From'], notify.ADDRESS)


if __name__ == '__main__':
    unittest.main()
