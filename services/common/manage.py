"""Versioned SQL setup using the Supabase-compatible migration ledger."""

import argparse
import hashlib
import secrets
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import psycopg
from dotenv import set_key
from psycopg import sql
from psycopg.rows import dict_row

from services.common.settings import ROOT, Settings, require_database_url


def migrate(connection: psycopg.Connection[dict[str, object]]) -> int:
    count = 0
    with connection.transaction():
        connection.execute("select pg_advisory_xact_lock(867431902)")
        connection.execute("create schema if not exists supabase_migrations")
        connection.execute("""create table if not exists supabase_migrations.schema_migrations
            (version text primary key, statements text[], name text)""")
        for path in sorted((ROOT / "supabase/migrations").glob("*.sql")):
            version, name = path.stem.split("_", 1)
            existing = connection.execute(
                "select statements from supabase_migrations.schema_migrations where version=%s",
                (version,),
            ).fetchone()
            statement = path.read_text()
            if existing:
                statements = existing["statements"]
                if isinstance(statements, list) and len(statements) == 1:
                    if (
                        hashlib.sha256(str(statements[0]).encode()).digest()
                        != hashlib.sha256(statement.encode()).digest()
                    ):
                        raise ValueError(
                            "An applied migration changed; add a new migration instead."
                        )
                continue
            connection.execute(statement, prepare=False)
            connection.execute(
                """insert into supabase_migrations.schema_migrations(version, name, statements)
                values (%s,%s,%s)""",
                (version, name, [statement]),
            )
            count += 1
    return count


def seed(connection: psycopg.Connection[dict[str, object]], environment: str) -> None:
    if environment != "development":
        raise ValueError("Synthetic seeding is available only in development.")
    with connection.transaction():
        observed = connection.execute(
            "select 1 from vantage.job_sources where not is_synthetic limit 1"
        ).fetchone()
        if observed:
            raise ValueError(
                "Use an isolated development database; observed sources already exist."
            )
        connection.execute((ROOT / "database/seed/demo.sql").read_text(), prepare=False)


def provision_roles(connection: psycopg.Connection[dict[str, object]], admin_url: str) -> None:
    parsed = urlsplit(admin_url)
    original_username = unquote(parsed.username or "postgres")
    suffix = (
        "." + original_username.split(".", 1)[1]
        if ".pooler.supabase.com" in (parsed.hostname or "") and "." in original_username
        else ""
    )
    environment = ROOT / ".env"
    existing_settings = Settings()
    updates: dict[str, str] = {}
    with connection.transaction():
        for login, group, key, configured in [
            ("vantage_api", "vantage_reader", "DATABASE_URL", existing_settings.database_url),
            (
                "vantage_ingestion",
                "vantage_writer",
                "INGESTION_DATABASE_URL",
                existing_settings.ingestion_database_url,
            ),
        ]:
            exists = connection.execute(
                "select 1 from pg_roles where rolname=%s", (login,)
            ).fetchone()
            if exists:
                if not configured.get_secret_value():
                    raise ValueError("Login already exists. Configure its existing URL locally.")
                continue
            password = secrets.token_urlsafe(32)
            connection.execute(
                sql.SQL("create role {} login password {}").format(
                    sql.Identifier(login), sql.Literal(password)
                )
            )
            connection.execute(
                sql.SQL("grant {} to {}").format(sql.Identifier(group), sql.Identifier(login))
            )
            host = parsed.netloc.split("@", 1)[-1]
            authority = f"{quote(login + suffix, safe='')}:{quote(password, safe='')}@{host}"
            updates[key] = urlunsplit((parsed.scheme, authority, parsed.path, parsed.query, ""))
        # Save while transaction remains open so an I/O error rolls back role creation.
        environment.touch(mode=0o600, exist_ok=True)
        environment.chmod(0o600)
        for key, value in updates.items():
            set_key(str(environment), key, value, quote_mode="always")


def main() -> None:
    parser = argparse.ArgumentParser(description="Vantage database setup")
    parser.add_argument("command", choices=["migrate", "seed", "roles"])
    command = parser.parse_args().command
    configuration = Settings()
    try:
        url = require_database_url(configuration.migration_database_url)
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=10) as connection:
            if command == "migrate":
                print(f"Applied {migrate(connection)} migration(s).")
            elif command == "seed":
                seed(connection, configuration.app_env)
                print("Synthetic development seed applied.")
            else:
                provision_roles(connection, url)
                print("Database logins configured. Credentials saved only to root .env.")
    except ValueError as error:
        raise SystemExit(str(error)) from None
    except (psycopg.Error, OSError):
        raise SystemExit(
            "Database setup failed. Check the URL, permissions, and migration state."
        ) from None


if __name__ == "__main__":
    main()
