import pyotp

from app.modules.two_factor.crypto_utils import (
    decrypt_secret,
    encrypt_secret,
    generate_backup_codes,
    mark_backup_code_used,
    verify_backup_code,
)
from app.modules.two_factor.totp_utils import (
    generate_totp_secret,
    get_totp_provisioning_uri,
    verify_totp_with_window,
)


def test_crypto_encrypt_decrypt_roundtrip():
    plaintext = "super-secret-value"
    ct = encrypt_secret(plaintext)
    assert isinstance(ct, str)
    pt = decrypt_secret(ct)
    assert pt == plaintext


def test_backup_codes_generation_and_verification():
    plain, hashed = generate_backup_codes(count=3)
    assert len(plain) == 3
    assert len(hashed) == 3
    assert all("-" in c for c in plain)

    assert verify_backup_code(plain[0], hashed, []) is True
    used = mark_backup_code_used(plain[0], [])
    assert verify_backup_code(plain[0], hashed, used) is False


def test_totp_generation_and_verification():
    secret = generate_totp_secret()
    totp = pyotp.TOTP(secret)
    code = totp.now()
    assert verify_totp_with_window(secret, code) is True


def test_totp_provisioning_uri_contains_email():
    secret = generate_totp_secret()
    email = "user@example.com"
    uri = get_totp_provisioning_uri(secret, email)
    assert uri.startswith("otpauth://totp/")
    assert email in uri
