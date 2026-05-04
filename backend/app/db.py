from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, text
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Submission(Base):
    __tablename__ = "assessment_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def _normalize_database_url(url: str) -> str:
    """
    Normalize connection strings for SQLAlchemy + psycopg2.
    Works with Neon, Render, and other hosts that use postgres:// or postgresql://.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "sqlite:///./assessment_submissions.db",
    )


def create_db_engine():
    url = _normalize_database_url(get_database_url())
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_add_meta_json() -> None:
    """Add meta_json to existing DBs (SQLite/Postgres) without Alembic."""
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            rows = conn.execute(
                text("PRAGMA table_info(assessment_submissions)")
            ).fetchall()
            col_names = {row[1] for row in rows}
            if "meta_json" not in col_names:
                conn.execute(
                    text(
                        "ALTER TABLE assessment_submissions "
                        "ADD COLUMN meta_json TEXT DEFAULT '{}'"
                    )
                )
        else:
            conn.execute(
                text(
                    "ALTER TABLE assessment_submissions "
                    "ADD COLUMN IF NOT EXISTS meta_json TEXT DEFAULT '{}'"
                )
            )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_add_meta_json()


def save_submission(
    *,
    email: str | None,
    answers: dict[str, Any],
    report: dict[str, Any],
    consent: bool,
    meta: dict[str, Any] | None = None,
) -> int:
    meta_clean = meta or {}
    with SessionLocal() as session:
        row = Submission(
            email=email,
            answers_json=json.dumps(answers, ensure_ascii=False),
            report_json=json.dumps(report, ensure_ascii=False),
            consent=consent,
            meta_json=json.dumps(meta_clean, ensure_ascii=False),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return int(row.id)


def list_submissions(*, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        stmt = (
            select(Submission)
            .order_by(Submission.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list(session.scalars(stmt))
        out: list[dict[str, Any]] = []
        for r in rows:
            try:
                raw_m = r.meta_json
                meta = json.loads(raw_m) if raw_m else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            out.append(
                {
                    "id": r.id,
                    "email": r.email,
                    "consent": r.consent,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "meta": meta,
                    "answers": json.loads(r.answers_json),
                    "report": json.loads(r.report_json),
                }
            )
        return out


def admin_summary_rows() -> list[dict[str, Any]]:
    """Lightweight rows for band / email presence counts (admin)."""
    with SessionLocal() as session:
        stmt = select(Submission).order_by(Submission.created_at.desc())
        rows = list(session.scalars(stmt))
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            rep = json.loads(r.report_json)
            band = rep.get("band", "")
            pct = rep.get("score_percent", "")
        except (json.JSONDecodeError, TypeError):
            band, pct = "", ""
        out.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "email": r.email,
                "has_email": bool(r.email),
                "score_percent": pct,
                "band": band,
            }
        )
    return out
