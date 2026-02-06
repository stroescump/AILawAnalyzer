from enum import Enum


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    partial = "partial"
    blocked = "blocked"


class ErrorStage(str, Enum):
    ingest = "ingest"
    parse = "parse"
    ocr = "ocr"
    chunk = "chunk"
    extract = "extract"
    explain = "explain"


class OutputType(str, Enum):
    extractor_json = "extractor_json"
    explainer_summary = "explainer_summary"
    sustainability_index = "sustainability_index"
