import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DbConfig:
    path: Path


def connect(cfg: DbConfig) -> sqlite3.Connection:
    cfg.path.parent.mkdir(parents=True, exist_ok=True)
    # Pareto: allow FastAPI threadpool usage with a single shared connection for PoC.
    # Not for prod; later switch to per-request connections or a pool + Postgres.
    conn = sqlite3.connect(cfg.path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bills (
          id INTEGER PRIMARY KEY,
          source TEXT NOT NULL,
          source_bill_id TEXT,
          title TEXT NOT NULL,
          status TEXT,
          introduced_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
          id INTEGER PRIMARY KEY,
          bill_id INTEGER NOT NULL,
          doc_type TEXT NOT NULL,
          source_url TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY (bill_id) REFERENCES bills(id)
        );

        CREATE TABLE IF NOT EXISTS document_versions (
          id INTEGER PRIMARY KEY,
          document_id INTEGER NOT NULL,
          version_hash TEXT NOT NULL,
          fetched_at TEXT NOT NULL,
          mime_type TEXT NOT NULL,
          file_path TEXT NOT NULL,
          page_count INTEGER,
          quality_level TEXT,
          ocr_applied INTEGER NOT NULL,
          notes TEXT,
          FOREIGN KEY (document_id) REFERENCES documents(id),
          UNIQUE(document_id, version_hash)
        );

        CREATE TABLE IF NOT EXISTS pages (
          id INTEGER PRIMARY KEY,
          document_version_id INTEGER NOT NULL,
          page_number INTEGER NOT NULL,
          text TEXT,
          ocr_text TEXT,
          quality_level TEXT,
          has_handwriting INTEGER NOT NULL,
          image_path TEXT,
          FOREIGN KEY (document_version_id) REFERENCES document_versions(id),
          UNIQUE(document_version_id, page_number)
        );

        CREATE TABLE IF NOT EXISTS chunks (
          id INTEGER PRIMARY KEY,
          document_version_id INTEGER NOT NULL,
          chunk_type TEXT NOT NULL,
          label TEXT,
          parent_chunk_id INTEGER,
          page_start INTEGER NOT NULL,
          page_end INTEGER NOT NULL,
          text TEXT NOT NULL,
          char_start INTEGER,
          char_end INTEGER,
          bbox_json TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY (document_version_id) REFERENCES document_versions(id),
          FOREIGN KEY (parent_chunk_id) REFERENCES chunks(id)
        );

        CREATE TABLE IF NOT EXISTS analysis_runs (
          id INTEGER PRIMARY KEY,
          bill_id INTEGER NOT NULL,
          input_fingerprint TEXT NOT NULL,
          pipeline_version TEXT NOT NULL,
          status TEXT NOT NULL,
          started_at TEXT,
          finished_at TEXT,
          quality_summary_json TEXT,
          FOREIGN KEY (bill_id) REFERENCES bills(id)
        );

        CREATE TABLE IF NOT EXISTS outputs (
          id INTEGER PRIMARY KEY,
          analysis_run_id INTEGER NOT NULL,
          output_type TEXT NOT NULL,
          content_json TEXT,
          content_text TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
        );

        CREATE TABLE IF NOT EXISTS evidence (
          id INTEGER PRIMARY KEY,
          analysis_run_id INTEGER NOT NULL,
          claim_id TEXT NOT NULL,
          document_version_id INTEGER NOT NULL,
          page_number INTEGER NOT NULL,
          chunk_id INTEGER,
          article_label TEXT,
          alin_label TEXT,
          char_start INTEGER,
          char_end INTEGER,
          bbox_json TEXT,
          excerpt_text TEXT NOT NULL,
          FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id),
          FOREIGN KEY (document_version_id) REFERENCES document_versions(id),
          FOREIGN KEY (chunk_id) REFERENCES chunks(id)
        );

        CREATE TABLE IF NOT EXISTS errors (
          id INTEGER PRIMARY KEY,
          analysis_run_id INTEGER NOT NULL,
          stage TEXT NOT NULL,
          error_code TEXT NOT NULL,
          message TEXT NOT NULL,
          details_json TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
        );

        CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY,
          type TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          status TEXT NOT NULL,
          attempts INTEGER NOT NULL,
          scheduled_at TEXT NOT NULL,
          locked_at TEXT,
          last_error TEXT
        );
        """
    )
    conn.commit()
