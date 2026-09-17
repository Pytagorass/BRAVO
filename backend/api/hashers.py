import bcrypt
from django.contrib.auth.hashers import BasePasswordHasher, mask_hash
from django.utils.crypto import constant_time_compare


class LegacyBCryptPasswordHasher(BasePasswordHasher):
    algorithm = 'legacy_bcrypt'

    def salt(self):
        return ''

    def encode(self, password, salt):
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return f'{self.algorithm}${hashed.decode("utf-8")}'

    def verify(self, password, encoded):
        algorithm, bcrypt_hash = encoded.split('$', 1)
        if algorithm != self.algorithm:
            return False

        candidate = bcrypt.hashpw(password.encode('utf-8'), bcrypt_hash.encode('utf-8'))
        return constant_time_compare(candidate.decode('utf-8'), bcrypt_hash)

    def safe_summary(self, encoded):
        algorithm, bcrypt_hash = encoded.split('$', 1)
        return {
            'algorithm': algorithm,
            'hash': mask_hash(bcrypt_hash),
        }

    def must_update(self, encoded):
        return True

    def harden_runtime(self, password, encoded):
        pass
