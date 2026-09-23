from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from credentials import load_env_file, write_env_file
from auto_login_headless import rc4_hex


class CredentialTests(unittest.TestCase):
    def test_round_trip_special_characters(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            for password in [' secret ', '"quoted"', "'quoted'", 'a=b#c', r'a\b\t', '中文密码', '\tpassword\t']:
                with self.subTest(password=password):
                    write_env_file(path, 'user', password)
                    self.assertEqual(load_env_file(path)['WLAN_PWD'], password)

    def test_legacy_backslashes_are_not_unescaped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('WLAN_PWD="a\\t"\n')
            self.assertEqual(load_env_file(path)['WLAN_PWD'], r'a\t')

    def test_rc4_preserves_spaces(self):
        self.assertNotEqual(rc4_hex(' secret ', 'Key'), rc4_hex('secret', 'Key'))

    def test_newline_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            with self.assertRaises(ValueError):
                write_env_file(path, 'user', 'pass\nword')
            self.assertFalse(path.exists())
