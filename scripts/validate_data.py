#!/usr/bin/env python3
"""Validate the repository's application statistics without third-party packages."""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "docs" / "data" / "application-stats.csv"
SCHEMA_FILE = ROOT / "docs" / "data" / "application-stats.schema.json"

EXPECTED_FIELDS = [
    "record_id",
    "cycle_year",
    "academic_term",
    "batch",
    "target_college",
    "target_major",
    "target_track",
    "planned_quota",
    "applicant_count",
    "eligible_count",
    "exam_attendee_count",
    "admitted_count",
    "source_type",
    "source_title",
    "source_url",
    "source_published_at",
    "evidence_level",
    "last_verified_at",
    "notes",
]

REQUIRED_FIELDS = {
    "record_id",
    "cycle_year",
    "batch",
    "target_college",
    "target_major",
    "source_type",
    "source_title",
    "source_url",
    "evidence_level",
    "last_verified_at",
}

COUNT_FIELDS = {
    "planned_quota",
    "applicant_count",
    "eligible_count",
    "exam_attendee_count",
    "admitted_count",
}

DATE_FIELDS = {"source_published_at", "last_verified_at"}
SOURCE_TYPES = {
    "official_notice",
    "official_attachment",
    "candidate_report",
    "other_public",
}
EVIDENCE_LEVELS = {"official", "corroborated", "single_report", "unverified"}
OFFICIAL_SOURCE_TYPES = {"official_notice", "official_attachment"}
RECORD_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
YEAR_PATTERN = re.compile(r"^[0-9]{4}$")


def validate_schema(schema_path: Path = SCHEMA_FILE) -> list[str]:
    errors: list[str] = []
    try:
        with schema_path.open(encoding="utf-8") as handle:
            schema = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{schema_path}: cannot read valid JSON schema: {exc}"]

    schema_fields = list(schema.get("properties", {}).keys())
    if schema_fields != EXPECTED_FIELDS:
        errors.append(
            f"{schema_path}: schema property order does not match the CSV header"
        )

    schema_required = set(schema.get("required", []))
    if schema_required != REQUIRED_FIELDS:
        errors.append(
            f"{schema_path}: required fields do not match validator rules"
        )

    return errors


def _is_https_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _nonempty(values: Iterable[str]) -> bool:
    return any(value.strip() for value in values)


def validate_csv(csv_path: Path = DATA_FILE) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    try:
        handle = csv_path.open(encoding="utf-8-sig", newline="")
    except OSError as exc:
        return [f"{csv_path}: cannot open data file: {exc}"], warnings

    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_FIELDS:
            errors.append(
                f"{csv_path}: header must exactly match the documented field order"
            )
            return errors, warnings

        for line_number, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                errors.append(f"{csv_path}:{line_number}: unexpected extra column")
                continue

            row = {key: (value or "").strip() for key, value in raw_row.items()}
            if not _nonempty(row.values()):
                continue

            for field in sorted(REQUIRED_FIELDS):
                if not row[field]:
                    errors.append(
                        f"{csv_path}:{line_number}: required field '{field}' is empty"
                    )

            record_id = row["record_id"]
            if record_id and not RECORD_ID_PATTERN.fullmatch(record_id):
                errors.append(
                    f"{csv_path}:{line_number}: invalid record_id '{record_id}'"
                )
            if record_id in seen_ids:
                errors.append(
                    f"{csv_path}:{line_number}: duplicate record_id '{record_id}'"
                )
            elif record_id:
                seen_ids.add(record_id)

            year_value = row["cycle_year"]
            if year_value and not YEAR_PATTERN.fullmatch(year_value):
                errors.append(
                    f"{csv_path}:{line_number}: cycle_year must be four ASCII digits"
                )
            elif year_value and not 2000 <= int(year_value) <= 2100:
                errors.append(
                    f"{csv_path}:{line_number}: cycle_year is outside 2000-2100"
                )

            parsed_counts: dict[str, int] = {}
            for field in sorted(COUNT_FIELDS):
                value = row[field]
                if not value:
                    continue
                try:
                    parsed = int(value)
                except ValueError:
                    errors.append(
                        f"{csv_path}:{line_number}: '{field}' must be an integer"
                    )
                    continue
                if parsed < 0:
                    errors.append(
                        f"{csv_path}:{line_number}: '{field}' cannot be negative"
                    )
                parsed_counts[field] = parsed

            if not any(row[field] for field in COUNT_FIELDS):
                errors.append(
                    f"{csv_path}:{line_number}: at least one count field is required"
                )

            for field in sorted(DATE_FIELDS):
                value = row[field]
                if not value:
                    continue
                try:
                    date.fromisoformat(value)
                except ValueError:
                    errors.append(
                        f"{csv_path}:{line_number}: '{field}' must use YYYY-MM-DD"
                    )

            if row["source_type"] and row["source_type"] not in SOURCE_TYPES:
                errors.append(
                    f"{csv_path}:{line_number}: unknown source_type "
                    f"'{row['source_type']}'"
                )

            if (
                row["evidence_level"]
                and row["evidence_level"] not in EVIDENCE_LEVELS
            ):
                errors.append(
                    f"{csv_path}:{line_number}: unknown evidence_level "
                    f"'{row['evidence_level']}'"
                )

            if row["source_url"] and not _is_https_url(row["source_url"]):
                errors.append(
                    f"{csv_path}:{line_number}: source_url must be an HTTPS URL"
                )

            if (
                row["evidence_level"] == "official"
                and row["source_type"] not in OFFICIAL_SOURCE_TYPES
            ):
                errors.append(
                    f"{csv_path}:{line_number}: official evidence requires an "
                    "official source type"
                )

            if row["evidence_level"] == "corroborated" and not row["notes"]:
                warnings.append(
                    f"{csv_path}:{line_number}: corroborated evidence should "
                    "describe additional sources in notes"
                )

            applicants = parsed_counts.get("applicant_count")
            admitted = parsed_counts.get("admitted_count")
            if (
                applicants is not None
                and admitted is not None
                and admitted > applicants
            ):
                warnings.append(
                    f"{csv_path}:{line_number}: admitted_count exceeds "
                    "applicant_count; explain differing scopes in notes"
                )

    return errors, warnings


def main() -> int:
    errors = validate_schema()
    csv_errors, warnings = validate_csv()
    errors.extend(csv_errors)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(f"Validation passed with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
