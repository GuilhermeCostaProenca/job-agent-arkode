from sqlalchemy.engine import Engine
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from src.core.config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, echo=False)


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _run_lightweight_migrations(engine)


def get_session() -> Session:
    return Session(get_engine())


def _run_lightweight_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    statements: list[str] = []
    table_names = set(inspector.get_table_names())

    if "executionruntable" in table_names:
        execution_columns = {column["name"] for column in inspector.get_columns("executionruntable")}
        if "pause_reason" not in execution_columns:
            statements.append("ALTER TABLE executionruntable ADD COLUMN pause_reason VARCHAR NOT NULL DEFAULT ''")
        if "retry_count" not in execution_columns:
            statements.append("ALTER TABLE executionruntable ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0")

    if "applicationtable" in table_names:
        application_columns = {column["name"] for column in inspector.get_columns("applicationtable")}
        if "connector" not in application_columns:
            statements.append("ALTER TABLE applicationtable ADD COLUMN connector VARCHAR NOT NULL DEFAULT 'generic_external'")

    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    _cleanup_duplicate_linkedin_jobs(engine)


def _cleanup_duplicate_linkedin_jobs(engine: Engine) -> None:
    with engine.begin() as connection:
        duplicate_groups = connection.execute(
            text(
                """
                SELECT user_id, external_id
                FROM jobtable
                WHERE source = 'linkedin' AND external_id <> ''
                GROUP BY user_id, external_id
                HAVING COUNT(*) > 1
                """
            )
        ).fetchall()

        for user_id, external_id in duplicate_groups:
            rows = connection.execute(
                text(
                    """
                    SELECT id, run_id, title, company, location, description, score, recommendation, status
                    FROM jobtable
                    WHERE source = 'linkedin' AND user_id = :user_id AND external_id = :external_id
                    """
                ),
                {"user_id": user_id, "external_id": external_id},
            ).mappings().all()
            if len(rows) < 2:
                continue

            canonical = max(rows, key=_linkedin_job_quality_key)
            canonical_id = str(canonical["id"])
            for row in rows:
                stale_id = str(row["id"])
                if stale_id == canonical_id:
                    continue
                _repoint_job_references(connection, stale_id, canonical_id)
                _merge_application_records(connection, stale_id, canonical_id, user_id)
                connection.execute(text("DELETE FROM jobtable WHERE id = :job_id"), {"job_id": stale_id})


def _linkedin_job_quality_key(row: object) -> tuple[int, int, int, int, int]:
    title = str(row["title"] or "")
    company = str(row["company"] or "")
    description = str(row["description"] or "")
    recommendation = str(row["recommendation"] or "")
    status = str(row["status"] or "")
    duplicated_title_penalty = 1 if _looks_duplicated(title) else 0
    duplicated_company_penalty = 1 if _looks_duplicated(company) else 0
    return (
        len(description),
        int(row["score"] or 0),
        1 if recommendation == "APPLY" else 0,
        1 if status != "new" else 0,
        -duplicated_title_penalty - duplicated_company_penalty,
    )


def _looks_duplicated(value: str) -> bool:
    normalized = " ".join(value.lower().split())
    if not normalized:
        return False
    midpoint = len(normalized) // 2
    if len(normalized) % 2 == 0 and normalized[:midpoint] == normalized[midpoint:]:
        return True
    words = normalized.split(" ")
    if len(words) % 2 == 0:
        half = len(words) // 2
        return words[:half] == words[half:]
    return False


def _repoint_job_references(connection, stale_job_id: str, canonical_job_id: str) -> None:
    for table_name in [
        "artifacttable",
        "approvaltable",
        "usersignaltable",
        "writingdeltatable",
        "applicationartifactsenttable",
        "applicationanswertable",
        "executionruntable",
    ]:
        connection.execute(
            text(f"UPDATE {table_name} SET job_id = :canonical_job_id WHERE job_id = :stale_job_id"),
            {"canonical_job_id": canonical_job_id, "stale_job_id": stale_job_id},
        )


def _merge_application_records(connection, stale_job_id: str, canonical_job_id: str, user_id: str) -> None:
    stale_application_id = f"app-{stale_job_id}"
    canonical_application_id = f"app-{canonical_job_id}"
    stale_application = connection.execute(
        text("SELECT * FROM applicationtable WHERE id = :application_id AND user_id = :user_id"),
        {"application_id": stale_application_id, "user_id": user_id},
    ).mappings().first()
    if stale_application is None:
        return

    canonical_application = connection.execute(
        text("SELECT * FROM applicationtable WHERE id = :application_id AND user_id = :user_id"),
        {"application_id": canonical_application_id, "user_id": user_id},
    ).mappings().first()

    if canonical_application is None:
        connection.execute(
            text(
                """
                UPDATE applicationtable
                SET id = :canonical_application_id, job_id = :canonical_job_id
                WHERE id = :stale_application_id AND user_id = :user_id
                """
            ),
            {
                "canonical_application_id": canonical_application_id,
                "canonical_job_id": canonical_job_id,
                "stale_application_id": stale_application_id,
                "user_id": user_id,
            },
        )
    else:
        connection.execute(
            text(
                """
                UPDATE applicationtable
                SET
                    status = CASE
                        WHEN applicationtable.status IN ('applied', 'replied', 'interview', 'offer') THEN applicationtable.status
                        ELSE :stale_status
                    END,
                    recommendation = CASE
                        WHEN applicationtable.recommendation = 'APPLY' THEN applicationtable.recommendation
                        ELSE :stale_recommendation
                    END,
                    link = CASE
                        WHEN applicationtable.link <> '' THEN applicationtable.link
                        ELSE :stale_link
                    END,
                    notes = CASE
                        WHEN applicationtable.notes <> '' THEN applicationtable.notes
                        ELSE :stale_notes
                    END
                WHERE id = :canonical_application_id AND user_id = :user_id
                """
            ),
            {
                "canonical_application_id": canonical_application_id,
                "user_id": user_id,
                "stale_status": stale_application["status"],
                "stale_recommendation": stale_application["recommendation"],
                "stale_link": stale_application["link"],
                "stale_notes": stale_application["notes"],
            },
        )
        connection.execute(
            text("DELETE FROM applicationtable WHERE id = :stale_application_id AND user_id = :user_id"),
            {"stale_application_id": stale_application_id, "user_id": user_id},
        )

    for table_name in ["executionruntable", "applicationartifactsenttable", "applicationanswertable", "emaileventtable"]:
        connection.execute(
            text(
                f"""
                UPDATE {table_name}
                SET application_id = :canonical_application_id, job_id = :canonical_job_id
                WHERE application_id = :stale_application_id
                """
            )
            if table_name != "emaileventtable"
            else text(
                f"""
                UPDATE {table_name}
                SET application_id = :canonical_application_id
                WHERE application_id = :stale_application_id
                """
            ),
            {
                "canonical_application_id": canonical_application_id,
                "canonical_job_id": canonical_job_id,
                "stale_application_id": stale_application_id,
            },
        )
