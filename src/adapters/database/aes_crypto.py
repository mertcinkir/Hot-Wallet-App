import os
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class AESCipher:
    """
    AES-256 encryption/decryption utility for wallet private keys.
    Key is loaded from environment variable WALLET_AES_KEY (must be 32 bytes for AES-256).
    """
    def __init__(self, key: bytes = None):
        key = key or os.getenv("WALLET_AES_KEY")
        if not key:
            raise ValueError("WALLET_AES_KEY environment variable not set.")
        if isinstance(key, str):
            key = key.encode()
        if len(key) != 32:
            raise ValueError("AES-256 key must be 32 bytes.")
        self.key = key

    def encrypt(self, raw: str) -> str:
        raw_bytes = raw.encode()
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CFB, iv=iv)
        encrypted = cipher.encrypt(raw_bytes)
        return b64encode(iv + encrypted).decode()

    def decrypt(self, enc: str) -> str:
        enc_bytes = b64decode(enc)
        iv = enc_bytes[:16]
        cipher = AES.new(self.key, AES.MODE_CFB, iv=iv)
        decrypted = cipher.decrypt(enc_bytes[16:])
        return decrypted.decode()

# Example usage:
# cipher = AESCipher()
# encrypted = cipher.encrypt('my_private_key')
# decrypted = cipher.decrypt(encrypted) 