from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
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


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def save_submission(
    *,
    email: str | None,
    answers: dict[str, Any],
    report: dict[str, Any],
    consent: bool,
) -> int:
    with SessionLocal() as session:
        row = Submission(
            email=email,
            answers_json=json.dumps(answers, ensure_ascii=False),
            report_json=json.dumps(report, ensure_ascii=False),
            consent=consent,
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
            out.append(
                {
                    "id": r.id,
                    "email": r.email,
                    "consent": r.consent,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "answers": json.loads(r.answers_json),
                    "report": json.loads(r.report_json),
                }
            )
        return out
