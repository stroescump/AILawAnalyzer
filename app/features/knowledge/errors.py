from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


class PublishValidationError(Exception):
    def __init__(self, issues: list[ValidationIssue]):
        super().__init__("publish_validation_error")
        self.issues = issues
