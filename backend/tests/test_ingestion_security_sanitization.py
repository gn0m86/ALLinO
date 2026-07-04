from app.services.ingestion_processor import redact_secrets


def test_redact_secrets_masks_known_secret_keys() -> None:
    payload = {
        "token": "abc",
        "nested": {
            "Authorization": "Bearer 123",
            "items": [
                {"api_key": "k1", "safe": "value"},
                {"secret": "s1"},
            ],
        },
        "safe": "ok",
    }

    redacted = redact_secrets(payload)
    assert redacted["token"] == "***"
    assert redacted["nested"]["Authorization"] == "***"
    assert redacted["nested"]["items"][0]["api_key"] == "***"
    assert redacted["nested"]["items"][0]["safe"] == "value"
    assert redacted["nested"]["items"][1]["secret"] == "***"
    assert redacted["safe"] == "ok"
