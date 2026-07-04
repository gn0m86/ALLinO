import httpx

from app.core import secrets


def test_get_secret_prefers_env(monkeypatch) -> None:
    monkeypatch.setenv("ALLINO_API_KEY", "env-key")
    monkeypatch.setenv("ALLINO_VAULT_ENABLED", "true")

    value = secrets.get_secret_value("ALLINO_API_KEY")
    assert value == "env-key"


def test_get_secret_from_vault_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("ALLINO_API_KEY", raising=False)
    monkeypatch.setenv("ALLINO_VAULT_ENABLED", "true")
    monkeypatch.setenv("ALLINO_VAULT_ADDR", "http://vault.local:8200")
    monkeypatch.setenv("ALLINO_VAULT_TOKEN", "vault-token")
    monkeypatch.setenv("ALLINO_VAULT_MOUNT", "secret")
    monkeypatch.setenv("ALLINO_VAULT_PATH", "allino")

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"data": {"data": {"ALLINO_API_KEY": "vault-key"}}}

    def fake_get(url, headers, timeout):
        assert url == "http://vault.local:8200/v1/secret/data/allino"
        assert headers["X-Vault-Token"] == "vault-token"
        assert timeout == 2.0
        return DummyResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    value = secrets.get_secret_value("ALLINO_API_KEY")
    assert value == "vault-key"


def test_get_secret_handles_vault_errors(monkeypatch) -> None:
    monkeypatch.delenv("ALLINO_API_KEY", raising=False)
    monkeypatch.setenv("ALLINO_VAULT_ENABLED", "true")
    monkeypatch.setenv("ALLINO_VAULT_ADDR", "http://vault.local:8200")
    monkeypatch.setenv("ALLINO_VAULT_TOKEN", "vault-token")

    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("vault unavailable")

    monkeypatch.setattr(httpx, "get", fake_get)

    value = secrets.get_secret_value("ALLINO_API_KEY")
    assert value is None
