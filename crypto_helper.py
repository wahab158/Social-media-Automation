import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# This key must be 32 url-safe base64 bytes
# Generate once with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Then add ENCRYPTION_KEY=<value> to your .env
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Auto-generate for first run, but warn
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"WARNING: No ENCRYPTION_KEY in .env. Auto-generated: {ENCRYPTION_KEY}")
    print("Add this to your .env file immediately to avoid data loss on restart.")

_fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt_value(plaintext: str) -> str:
    """Encrypts a string. Returns base64 encoded encrypted string."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypts an encrypted string. Returns original plaintext."""
    return _fernet.decrypt(ciphertext.encode()).decode()


def mask_key(plaintext: str) -> str:
    """Returns a masked version safe to show in UI: sk-...abc123"""
    if len(plaintext) <= 8:
        return "****"
    return plaintext[:4] + "..." + plaintext[-6:]
