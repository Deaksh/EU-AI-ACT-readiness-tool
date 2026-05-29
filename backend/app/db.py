from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class RegulationsCatalog(Base):
    __tablename__ = "regulations_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    questions: Mapped[list[RegulationQuestion]] = relationship(
        "RegulationQuestion", back_populates="regulation", cascade="all, delete-orphan"
    )


class RegulationQuestion(Base):
    __tablename__ = "regulation_questions"
    __table_args__ = (UniqueConstraint("regulation_id", "question_id", name="uq_reg_qid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    regulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regulations_catalog.id"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(String(20), nullable=False)
    section: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(10), nullable=False)
    options_json: Mapped[str] = mapped_column(Text, nullable=False)
    article_tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    show_if_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    regulation: Mapped[RegulationsCatalog] = relationship(
        "RegulationsCatalog", back_populates="questions"
    )


class Submission(Base):
    __tablename__ = "assessment_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    regulation_codes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///./assessment_submissions.db")


def create_db_engine():
    url = _normalize_database_url(get_database_url())
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ──────────────────────────────────────────────
# Migrations (inline, no Alembic)
# ──────────────────────────────────────────────

def _migrate_add_meta_json() -> None:
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


def _migrate_add_regulation_codes() -> None:
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            rows = conn.execute(
                text("PRAGMA table_info(assessment_submissions)")
            ).fetchall()
            col_names = {row[1] for row in rows}
            if "regulation_codes" not in col_names:
                conn.execute(
                    text(
                        "ALTER TABLE assessment_submissions "
                        "ADD COLUMN regulation_codes TEXT"
                    )
                )
        else:
            conn.execute(
                text(
                    "ALTER TABLE assessment_submissions "
                    "ADD COLUMN IF NOT EXISTS regulation_codes TEXT"
                )
            )


# ──────────────────────────────────────────────
# Seeding
# ──────────────────────────────────────────────

def _seed_regulations_catalog() -> None:
    from app.seed_data import REGULATIONS_SEED

    with SessionLocal() as session:
        for reg in REGULATIONS_SEED:
            exists = session.execute(
                select(RegulationsCatalog).where(RegulationsCatalog.code == reg["code"])
            ).scalar_one_or_none()
            if not exists:
                session.add(RegulationsCatalog(**reg))
        session.commit()


def _seed_euaiact_questions() -> None:
    """Migrate QUESTIONS_INTERNAL into regulation_questions for eu_ai_act (once)."""
    from app.seed_data import EUAIACT_ARTICLE_TAGS

    with SessionLocal() as session:
        reg = session.execute(
            select(RegulationsCatalog).where(RegulationsCatalog.code == "eu_ai_act")
        ).scalar_one_or_none()
        if reg is None:
            return

        # Skip if already seeded
        existing_count = session.execute(
            text("SELECT COUNT(*) FROM regulation_questions WHERE regulation_id = :rid"),
            {"rid": reg.id},
        ).scalar()
        if existing_count and existing_count > 0:
            return

        # Import here to avoid circular import at module level
        from app.main import QUESTIONS_INTERNAL

        for q in QUESTIONS_INTERNAL:
            orig_id = q["id"]          # "q1" … "q20"
            db_id = f"eu_{orig_id}"    # "eu_q1" … "eu_q20"

            show_if = q.get("show_if")
            if show_if:
                # Update the question_id reference to DB format
                show_if = {
                    "question_id": f"eu_{show_if['question_id']}",
                    "values": show_if["values"],
                }

            article_tags = EUAIACT_ARTICLE_TAGS.get(orig_id, [])

            session.add(
                RegulationQuestion(
                    regulation_id=reg.id,
                    question_id=db_id,
                    section=q["section"],
                    section_title=q["section_title"],
                    question_text=q["text"],
                    question_type=q["type"],
                    options_json=json.dumps(q["options"], ensure_ascii=False),
                    article_tags=json.dumps(article_tags, ensure_ascii=False),
                    show_if_json=json.dumps(show_if, ensure_ascii=False) if show_if else None,
                    order_index=q["order"],
                    is_active=True,
                )
            )
        session.commit()


def _seed_gdpr_questions() -> None:
    from app.seed_data import GDPR_QUESTIONS

    with SessionLocal() as session:
        reg = session.execute(
            select(RegulationsCatalog).where(RegulationsCatalog.code == "gdpr")
        ).scalar_one_or_none()
        if reg is None:
            return

        existing_count = session.execute(
            text("SELECT COUNT(*) FROM regulation_questions WHERE regulation_id = :rid"),
            {"rid": reg.id},
        ).scalar()
        if existing_count and existing_count > 0:
            return

        for q in GDPR_QUESTIONS:
            session.add(
                RegulationQuestion(
                    regulation_id=reg.id,
                    question_id=q["question_id"],
                    section=q["section"],
                    section_title=q["section_title"],
                    question_text=q["question_text"],
                    question_type=q["question_type"],
                    options_json=json.dumps(q["options"], ensure_ascii=False),
                    article_tags=json.dumps(q["article_tags"], ensure_ascii=False),
                    show_if_json=q["show_if_json"],
                    order_index=q["order_index"],
                    is_active=True,
                )
            )
        session.commit()


def _seed_nist_questions() -> None:
    from app.seed_data import NIST_QUESTIONS

    with SessionLocal() as session:
        reg = session.execute(
            select(RegulationsCatalog).where(RegulationsCatalog.code == "nist_ai_rmf")
        ).scalar_one_or_none()
        if reg is None:
            return

        existing_count = session.execute(
            text("SELECT COUNT(*) FROM regulation_questions WHERE regulation_id = :rid"),
            {"rid": reg.id},
        ).scalar()
        if existing_count and existing_count > 0:
            return

        for q in NIST_QUESTIONS:
            session.add(
                RegulationQuestion(
                    regulation_id=reg.id,
                    question_id=q["question_id"],
                    section=q["section"],
                    section_title=q["section_title"],
                    question_text=q["question_text"],
                    question_type=q["question_type"],
                    options_json=json.dumps(q["options"], ensure_ascii=False),
                    article_tags=json.dumps(q["article_tags"], ensure_ascii=False),
                    show_if_json=q["show_if_json"],
                    order_index=q["order_index"],
                    is_active=True,
                )
            )
        session.commit()


# ──────────────────────────────────────────────
# Data access
# ──────────────────────────────────────────────

def get_active_regulations() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.execute(
            select(RegulationsCatalog)
            .where(RegulationsCatalog.is_active == True)
            .order_by(RegulationsCatalog.id)
        ).scalars().all()
        return [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "jurisdiction": r.jurisdiction,
                "description": r.description,
                "deadline": r.deadline,
                "is_active": r.is_active,
            }
            for r in rows
        ]


def get_questions_for_regulations(codes: list[str]) -> list[dict[str, Any]]:
    """Return normalized question dicts for the given regulation codes, ordered by regulation/section/order."""
    with SessionLocal() as session:
        regs = session.execute(
            select(RegulationsCatalog).where(RegulationsCatalog.code.in_(codes))
        ).scalars().all()
        reg_by_id = {r.id: r.code for r in regs}

        rows = session.execute(
            select(RegulationQuestion)
            .where(
                RegulationQuestion.regulation_id.in_(list(reg_by_id.keys())),
                RegulationQuestion.is_active == True,
            )
            .order_by(
                RegulationQuestion.regulation_id,
                RegulationQuestion.section,
                RegulationQuestion.order_index,
            )
        ).scalars().all()

        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r.question_id,
                    "regulation_code": reg_by_id.get(r.regulation_id, ""),
                    "section": r.section,
                    "section_title": r.section_title,
                    "order": r.order_index,
                    "text": r.question_text,
                    "type": r.question_type,
                    "options": json.loads(r.options_json),
                    "show_if": json.loads(r.show_if_json) if r.show_if_json else None,
                    "article_tags": json.loads(r.article_tags) if r.article_tags else [],
                }
            )
        return out


# ──────────────────────────────────────────────
# Submission CRUD
# ──────────────────────────────────────────────

def save_submission(
    *,
    email: str | None,
    answers: dict[str, Any],
    report: dict[str, Any],
    consent: bool,
    meta: dict[str, Any] | None = None,
    regulation_codes: list[str] | None = None,
) -> int:
    meta_clean = meta or {}
    with SessionLocal() as session:
        row = Submission(
            email=email,
            answers_json=json.dumps(answers, ensure_ascii=False),
            report_json=json.dumps(report, ensure_ascii=False),
            consent=consent,
            meta_json=json.dumps(meta_clean, ensure_ascii=False),
            regulation_codes=json.dumps(regulation_codes) if regulation_codes else None,
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
                    "regulation_codes": json.loads(r.regulation_codes) if r.regulation_codes else None,
                }
            )
        return out


def admin_summary_rows() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        stmt = select(Submission).order_by(Submission.created_at.desc())
        rows = list(session.scalars(stmt))
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            rep = json.loads(r.report_json)
            # For multi-regulation reports, pick overall band
            if rep.get("multi_regulation"):
                band = rep.get("overall_band", "")
                pct = ""
            else:
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


# ──────────────────────────────────────────────
# Init
# ──────────────────────────────────────────────

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_add_meta_json()
    _migrate_add_regulation_codes()
    _seed_regulations_catalog()
    _seed_gdpr_questions()
    _seed_nist_questions()
    # EU AI Act seeding happens after QUESTIONS_INTERNAL is available (called from lifespan)
