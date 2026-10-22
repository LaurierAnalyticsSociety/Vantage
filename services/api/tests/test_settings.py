import pytest
from pydantic import SecretStr

from services.common.settings import require_database_url


@pytest.mark.parametrize("url", ["", "https://example.org", "postgresql://db.example.org/app"])
def test_connection_configuration_rejects_missing_or_unencrypted_hosted_urls(url: str) -> None:
    with pytest.raises(ValueError):
        require_database_url(SecretStr(url))


def test_hosted_connection_accepts_explicit_tls() -> None:
    url = "postgresql://api:password@db.example.org/postgres?sslmode=require"
    assert require_database_url(SecretStr(url)) == url
