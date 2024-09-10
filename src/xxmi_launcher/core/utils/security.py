import base64

from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


class Security:
    def __init__(self, private_key=None, public_key=None):
        self.private_key = None
        self.public_key = None

        if private_key is not None:
            self.load_private_key(private_key)

        if public_key is not None:
            self.load_public_key(public_key)

    def sign(self, data, encoding='utf-8'):
        return self.encode(self.private_key.sign(
            self.to_bytearray(data, encoding),
            ec.ECDSA(hashes.SHA256())
        ))

    def verify(self, base64_signature, data, encoding='utf-8'):
        try:
            self.public_key.verify(self.decode(base64_signature), self.to_bytearray(data, encoding), ec.ECDSA(hashes.SHA256()))
            return True
        except Exception as e:
            return False

    def load_private_key(self, private_key):
        if Path(private_key).is_file():
            with open(Path(private_key), 'r') as f:
                private_key = f.read()
        der_bytes = self.decode(private_key)
        self.private_key = serialization.load_der_private_key(der_bytes, password=None)

    def load_public_key(self, public_key):
        if Path(public_key).is_file():
            with open(Path(public_key), 'r') as f:
                public_key = f.read()
        der_bytes = self.decode(public_key)
        self.public_key = serialization.load_der_public_key(der_bytes)

    def serialize_private_key(self):
        return self.private_key.private_bytes(encoding=serialization.Encoding.DER,
                                              format=serialization.PrivateFormat.PKCS8,
                                              encryption_algorithm=serialization.NoEncryption())

    def serialize_public_key(self):
        return self.public_key.public_bytes(encoding=serialization.Encoding.DER,
                                            format=serialization.PublicFormat.SubjectPublicKeyInfo)

    def generate_key_pair(self):
        self.private_key = ec.generate_private_key(
            ec.SECP384R1()
        )
        self.public_key = self.private_key.public_key()

    def write_key_pair(self, keys_path: Path):
        with open(keys_path / 'private_key.der', 'w') as f:
            f.write(self.encode(self.serialize_private_key()))
        with open(keys_path / 'public_key.der', 'w') as f:
            f.write(self.encode(self.serialize_public_key()))

    def read_key_pair(self, keys_path: Path):
        self.load_private_key(keys_path / 'private_key.der')
        self.load_public_key(keys_path / 'public_key.der')

    def encode(self, data, encoding='utf-8'):
        return base64.b64encode(data).decode(encoding)

    def decode(self, data):
        return base64.b64decode(data)

    def to_bytearray(self, data, encoding):
        if isinstance(data, str):
            return bytearray(data, encoding)
        else:
            return bytearray(data)
