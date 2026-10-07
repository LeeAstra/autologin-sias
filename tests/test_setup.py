"""Saved credential validation must never authenticate stale environment values."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import auto_login_headless as app


class SetupTests(unittest.TestCase):
    def test_setup_verifies_saved_pair_even_when_online_and_environment_conflicts(self):
        for old in ({'WLAN_USER':'old-user','WLAN_PWD':'old-password'},
                    {'WLAN_PWD':'old-password'}):
            for body, code in ((b'{"success":true}',0),(b'{"success":false}',5),
                               (b'{"message":"login success: false"}',8)):
                with self.subTest(old=old,body=body), tempfile.TemporaryDirectory() as folder:
                    target=Path(folder)
                    with patch.object(app,'BASE_DIR',target), patch.object(app,'ENV_PATH',target/'.env'), \
                         patch.dict(os.environ,old,clear=True), patch('builtins.input',return_value='new-user'), \
                         patch.object(app.cli.getpass,'getpass',return_value=' new-password '), \
                         patch.object(app,'query_authentication_state',return_value=('authenticated','fixture')), \
                         patch.object(app,'request',side_effect=[(200,b''),(200,body),(200,b'0')]) as request:
                        self.assertEqual(app.setup_env(),code)
                        self.assertEqual(request.call_count,3)
                        data=request.call_args_list[1].kwargs['data']
                        self.assertEqual(data['userName'],'new-user')
                        self.assertEqual(data['pwd'],app.rc4_hex(' new-password ',data['auth_tag']))
                        for key,value in old.items(): self.assertEqual(os.environ[key],value)
                    self.assertEqual(app.load_env_file(target/'.env'),
                                     {'WLAN_USER':'new-user','WLAN_PWD':' new-password '})

    def test_saved_validation_does_not_fall_back_to_environment(self):
        with patch.dict(os.environ,{'WLAN_USER':'old','WLAN_PWD':'old'}), \
             patch.object(app,'load_env_file',return_value={}), patch.object(app,'request') as request:
            self.assertEqual(app.run_login(validate_credentials=True),2)
            request.assert_not_called()

    def test_regular_run_keeps_existing_environment_override(self):
        with patch.dict(os.environ,{'WLAN_USER':'override','WLAN_PWD':'override'}), \
             patch.object(app,'load_env_file',return_value={'WLAN_USER':'saved','WLAN_PWD':'saved'}), \
             patch.object(app,'query_authentication_state',side_effect=[('auth_required','fixture'),('authenticated','fixture')]), \
             patch.object(app,'request',side_effect=[(200,b''),(200,b'{"success":true}'),(200,b'0')]) as request:
            self.assertEqual(app.run_login(),0)
            self.assertEqual(request.call_args_list[1].kwargs['data']['userName'],'override')

    def test_invalid_new_config_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder); (target/'.env').write_bytes(b'previous')
            with patch.object(app,'BASE_DIR',target), patch('builtins.input',side_effect=['y','new-user']), \
                 patch.object(app.cli.getpass,'getpass',return_value='bad\npassword'), \
                 patch.object(app,'run_login') as login:
                self.assertEqual(app.setup_env(),2)
                login.assert_not_called()
            self.assertEqual((target/'.env').read_bytes(),b'previous')

if __name__ == '__main__': unittest.main()
