import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from app.features.knowledge.hashing import content_hash_sha256
from app.features.knowledge.models import KnowledgeObject, KnowledgeStatus, KnowledgeVersion


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ObjectType = Literal["sme_claim", "knowledge_pack", "claim_template"]


@dataclass(frozen=True)
class PublishResult:
    object_id: str
    version: int
    content_hash: str


class KnowledgeRepo:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _tables(self, object_type: ObjectType) -> tuple[str, str, str]:
        if object_type == "sme_claim":
            return ("sme_claims", "sme_claim_versions", "claim_id")
        if object_type == "knowledge_pack":
            return ("knowledge_packs", "knowledge_pack_versions", "pack_id")
        if object_type == "claim_template":
            return ("claim_templates", "claim_template_versions", "template_id")
        raise ValueError(f"unknown object_type: {object_type}")

    def create_object(self, object_type: ObjectType, object_id: str, actor: str) -> None:
        obj_table, _, id_col = self._tables(object_type)
        now = _now_iso()
        self._conn.execute(
            f"""
            INSERT INTO {obj_table} ({id_col}, current_version, status, created_by, created_at)
            VALUES (?, NULL, 'draft', ?, ?)
            """,
            (object_id, actor, now),
        )
        self._audit(actor, "create_object", object_type, object_id, None, diff=None)
        self._conn.commit()

    def get_object(self, object_type: ObjectType, object_id: str) -> KnowledgeObject | None:
        obj_table, _, id_col = self._tables(object_type)
        row = self._conn.execute(
            f"SELECT {id_col} AS object_id, current_version, status, created_by, created_at FROM {obj_table} WHERE {id_col} = ?",
            (object_id,),
        ).fetchone()
        if not row:
            return None
        return KnowledgeObject(
            object_id=str(row["object_id"]),
            current_version=row["current_version"],
            status=row["status"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )

    def list_objects(self, object_type: ObjectType, limit: int = 200) -> list[KnowledgeObject]:
        obj_table, _, id_col = self._tables(object_type)
        rows = self._conn.execute(
            f"""
            SELECT {id_col} AS object_id, current_version, status, created_by, created_at
            FROM {obj_table}
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            KnowledgeObject(
                object_id=str(r["object_id"]),
                current_version=r["current_version"],
                status=r["status"],
                created_by=r["created_by"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def upsert_draft_version(
        self,
        object_type: ObjectType,
        object_id: str,
        content: dict[str, Any],
        actor: str,
    ) -> PublishResult:
        """Create or replace a draft version.

        PoC simplification: we keep a single draft version number 0.
        Publishing creates version 1..N.
        """

        _, ver_table, id_col = self._tables(object_type)
        now = _now_iso()
        h = content_hash_sha256(content)
        self._conn.execute(
            f"""
            INSERT INTO {ver_table} ({id_col}, version, content_json, content_hash, status, created_by, approved_by, created_at, approved_at)
            VALUES (?, 0, ?, ?, 'draft', ?, NULL, ?, NULL)
            ON CONFLICT({id_col}, version) DO UPDATE SET
              content_json=excluded.content_json,
              content_hash=excluded.content_hash,
              status='draft',
              created_by=excluded.created_by,
              created_at=excluded.created_at,
              approved_by=NULL,
              approved_at=NULL
            """,
            (object_id, json.dumps(content, ensure_ascii=False), h, actor, now),
        )
        self._audit(actor, "upsert_draft", object_type, object_id, 0, diff=None)
        self._conn.commit()
        return PublishResult(object_id=object_id, version=0, content_hash=h)

    def get_version(
        self, object_type: ObjectType, object_id: str, version: int
    ) -> KnowledgeVersion | None:
        _, ver_table, id_col = self._tables(object_type)
        row = self._conn.execute(
            f"""
            SELECT {id_col} AS object_id, version, content_json, content_hash, status,
                   created_by, approved_by, created_at, approved_at
            FROM {ver_table}
            WHERE {id_col} = ? AND version = ?
            """,
            (object_id, version),
        ).fetchone()
        if not row:
            return None
        return KnowledgeVersion(
            object_id=str(row["object_id"]),
            version=int(row["version"]),
            content=json.loads(row["content_json"]),
            content_hash=str(row["content_hash"]),
            status=row["status"],
            created_by=row["created_by"],
            approved_by=row["approved_by"],
            created_at=row["created_at"],
            approved_at=row["approved_at"],
        )

    def publish(
        self,
        object_type: ObjectType,
        object_id: str,
        actor: str,
        validate_fn,
    ) -> PublishResult:
        """Publish current draft (version 0) as next version.

        validate_fn(content) must raise ValueError on invalid content.
        """

        obj_table, ver_table, id_col = self._tables(object_type)
        draft = self.get_version(object_type, object_id, version=0)
        if not draft:
            raise ValueError("no_draft")

        validate_fn(draft.content)

        row = self._conn.execute(
            f"SELECT current_version FROM {obj_table} WHERE {id_col} = ?",
            (object_id,),
        ).fetchone()
        if not row:
            raise ValueError("object_not_found")

        current_version = row["current_version"]
        next_version = 1 if current_version is None else int(current_version) + 1

        now = _now_iso()
        self._conn.execute(
            f"""
            INSERT INTO {ver_table} ({id_col}, version, content_json, content_hash, status, created_by, approved_by, created_at, approved_at)
            VALUES (?, ?, ?, ?, 'published', ?, ?, ?, ?)
            """,
            (
                object_id,
                next_version,
                json.dumps(draft.content, ensure_ascii=False),
                draft.content_hash,
                draft.created_by,
                actor,
                draft.created_at,
                now,
            ),
        )
        self._conn.execute(
            f"UPDATE {obj_table} SET current_version = ?, status = 'published' WHERE {id_col} = ?",
            (next_version, object_id),
        )
        self._audit(actor, "publish", object_type, object_id, next_version, diff=None)
        self._conn.commit()
        return PublishResult(object_id=object_id, version=next_version, content_hash=draft.content_hash)

    def _audit(
        self,
        actor: str,
        action: str,
        object_type: ObjectType,
        object_id: str,
        object_version: int | None,
        diff: dict[str, Any] | None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO knowledge_audit_log (actor, action, object_type, object_id, object_version, diff_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                actor,
                action,
                object_type,
                object_id,
                object_version,
                None if diff is None else json.dumps(diff, ensure_ascii=False),
                _now_iso(),
            ),
        )


def parse_status(s: str) -> KnowledgeStatus:
    if s not in ("draft", "published", "archived"):
        raise ValueError("invalid_status")
    return s  # type: ignore[return-value]
