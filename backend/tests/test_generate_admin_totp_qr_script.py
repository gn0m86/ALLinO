import importlib.util
from pathlib import Path

import pyotp


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_admin_totp_qr.py"
    spec = importlib.util.spec_from_file_location("generate_admin_totp_qr", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_otpauth_uri_includes_secret_account_and_issuer() -> None:
    module = _load_module()
    uri = module.build_otpauth_uri("JBSWY3DPEHPK3PXP", account_name="admin", issuer="ALLinO")

    assert uri.startswith("otpauth://totp/")
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "issuer=ALLinO" in uri
    assert "admin" in uri


def test_build_otpauth_uri_is_verifiable_by_pyotp() -> None:
    module = _load_module()
    secret = pyotp.random_base32()
    uri = module.build_otpauth_uri(secret, account_name="admin", issuer="ALLinO")

    totp = pyotp.parse_uri(uri)
    assert totp.verify(totp.now())
