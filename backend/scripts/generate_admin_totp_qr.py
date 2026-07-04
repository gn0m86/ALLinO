from __future__ import annotations

import argparse
import sys

import pyotp
import qrcode


def build_otpauth_uri(secret: str, *, account_name: str, issuer: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Local-only helper for enrolling ALLINO_ADMIN_TOTP_SECRET in an authenticator "
            "app via QR code instead of typing the base32 secret by hand. Never talks to "
            "the running backend or any network -- run it on your own machine, then set "
            "the printed secret as ALLINO_ADMIN_TOTP_SECRET (env or Vault) before restarting "
            "the backend. There is deliberately no server endpoint for this: any endpoint "
            "that could hand back the raw TOTP seed would let a caller self-enroll a device "
            "and permanently bypass the second factor it's supposed to provide."
        )
    )
    parser.add_argument(
        "--secret",
        help="Existing base32 TOTP secret to re-render as a QR code. If omitted, a new random one is generated.",
    )
    parser.add_argument("--account-name", default="admin", help="Label shown in the authenticator app.")
    parser.add_argument("--issuer", default="ALLinO", help="Issuer name shown in the authenticator app.")
    parser.add_argument("--output", help="Save the QR code as a PNG at this path instead of printing ASCII art.")
    args = parser.parse_args()

    secret = args.secret or pyotp.random_base32()
    uri = build_otpauth_uri(secret, account_name=args.account_name, issuer=args.issuer)

    print(f"Secret (set this as ALLINO_ADMIN_TOTP_SECRET): {secret}")
    print(f"otpauth URI: {uri}")

    if args.output:
        qrcode.make(uri).save(args.output)
        print(f"QR code saved to {args.output}")
    else:
        # Windows terminals often default to a non-UTF-8 codepage that can't render
        # the block characters qrcode's ASCII output uses -- force UTF-8 so this
        # works the same on Windows/macOS/Linux without a separate code path.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        qr = qrcode.QRCode()
        qr.add_data(uri)
        qr.print_ascii(invert=True)


if __name__ == "__main__":
    main()
