import argparse
import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Source, SourcePolicy, User
from app.services.security import hash_password

SOURCES = [
    ("commons.wikimedia.org", "Wikimedia Commons", SourcePolicy.download_allowed, True),
    ("upload.wikimedia.org", "Wikimedia file CDN", SourcePolicy.download_allowed, True),
    ("archive.org", "Internet Archive", SourcePolicy.download_allowed, True),
    ("pexels.com", "Pexels", SourcePolicy.download_allowed, True),
    ("pixabay.com", "Pixabay", SourcePolicy.download_allowed, True),
    ("nasa.gov", "NASA", SourcePolicy.download_allowed, True),
    ("youtube.com", "YouTube", SourcePolicy.embed_only, True),
    ("youtu.be", "YouTube short links", SourcePolicy.embed_only, False),
    ("vimeo.com", "Vimeo", SourcePolicy.embed_only, True),
    ("netflix.com", "Netflix", SourcePolicy.blocked, True),
]

DEMO_EMAIL = "demo@uvh.app"
DEMO_PASSWORD = "demo-password-2026"


async def seed_demo() -> None:
    async with SessionLocal() as db:
        for host, display_name, policy, subdomains in SOURCES:
            existing = await db.scalar(select(Source).where(Source.host == host))
            if existing is None:
                db.add(
                    Source(
                        host=host,
                        display_name=display_name,
                        policy=policy,
                        include_subdomains=subdomains,
                        max_file_bytes=2 * 1024**3,
                        reviewed_at=datetime.now(UTC)
                        if policy != SourcePolicy.pending_review
                        else None,
                        notes="Seed Phase 1; review ToS before production.",
                    )
                )

        user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            db.add(
                User(
                    email=DEMO_EMAIL,
                    password_hash=hash_password(DEMO_PASSWORD),
                    display_name="Demo",
                )
            )
        await db.commit()

    print(f"seed selesai. Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")


async def approve_source(host: str, policy: str, note: str, max_bytes: int) -> None:
    try:
        value = SourcePolicy(policy)
    except ValueError as exc:
        raise SystemExit(f"policy tidak dikenal: {policy}") from exc

    async with SessionLocal() as db:
        source = await db.scalar(select(Source).where(Source.host == host.lower()))
        if source is None:
            source = Source(
                host=host.lower(),
                display_name=host,
                policy=value,
                include_subdomains=True,
                max_file_bytes=max_bytes,
            )
            db.add(source)
        else:
            source.policy = value
            source.max_file_bytes = max_bytes
        source.notes = note
        source.reviewed_at = datetime.now(UTC)
        await db.commit()
    print(f"sumber {host} disetujui dengan policy {policy}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed-demo", help="buat user demo dan registry sumber")

    approve = sub.add_parser("approve-source", help="set policy sumber")
    approve.add_argument("--host", required=True)
    approve.add_argument(
        "--policy",
        required=True,
        choices=[item.value for item in SourcePolicy],
    )
    approve.add_argument("--note", default="")
    approve.add_argument("--max-bytes", type=int, default=2 * 1024**3)

    args = parser.parse_args()
    if args.command == "seed-demo":
        asyncio.run(seed_demo())
    elif args.command == "approve-source":
        asyncio.run(approve_source(args.host, args.policy, args.note, args.max_bytes))


if __name__ == "__main__":
    main()
