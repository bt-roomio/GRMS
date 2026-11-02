from cryptography.fernet import Fernet
from django.test import SimpleTestCase, override_settings

from core.utils.secrets import SecretDecryptionError, decrypt, encrypt


@override_settings(SECRET_KEY="first", SECRETS_ENCRYPTION_KEY="")
class SecretsTest(SimpleTestCase):
    def test_round_trip(self):
        ciphertext = encrypt("EAAtoken")

        self.assertNotIn("EAAtoken", ciphertext)
        self.assertEqual(decrypt(ciphertext), "EAAtoken")

    def test_another_secret_key_cannot_decrypt(self):
        ciphertext = encrypt("EAAtoken")

        with override_settings(SECRET_KEY="second"), self.assertRaises(SecretDecryptionError):
            decrypt(ciphertext)

    def test_a_dedicated_key_survives_secret_key_rotation(self):
        key = Fernet.generate_key().decode()
        with override_settings(SECRETS_ENCRYPTION_KEY=key):
            ciphertext = encrypt("EAAtoken")

        with override_settings(SECRETS_ENCRYPTION_KEY=key, SECRET_KEY="second"):
            self.assertEqual(decrypt(ciphertext), "EAAtoken")

    def test_garbage_is_a_decryption_error(self):
        with self.assertRaises(SecretDecryptionError):
            decrypt("not-a-token")
