import csv
import tempfile
import unittest
from pathlib import Path

from scripts import validate_data


class ValidateDataTests(unittest.TestCase):
    def write_csv(self, rows, fieldnames=None):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path = Path(temporary_directory.name) / "历年申请数据.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames or validate_data.EXPECTED_FIELDS,
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def valid_row(self, **overrides):
        row = {field: "" for field in validate_data.EXPECTED_FIELDS}
        row.update(
            {
                "record_id": "test-record",
                "cycle_year": "2025",
                "batch": "test-batch",
                "target_college": "Test College",
                "target_major": "Test Major",
                "applicant_count": "10",
                "source_type": "official_notice",
                "source_title": "Test Source",
                "source_url": "https://example.invalid/source",
                "evidence_level": "official",
                "last_verified_at": "2025-01-01",
            }
        )
        row.update(overrides)
        return row

    def test_header_only_file_is_valid(self):
        errors, warnings = validate_data.validate_csv(self.write_csv([]))
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_valid_row_is_accepted(self):
        errors, warnings = validate_data.validate_csv(
            self.write_csv([self.valid_row()])
        )
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_negative_count_and_non_https_source_are_rejected(self):
        row = self.valid_row(applicant_count="-1", source_url="http://example.test")
        errors, _ = validate_data.validate_csv(self.write_csv([row]))
        self.assertTrue(any("cannot be negative" in error for error in errors))
        self.assertTrue(any("must be an HTTPS URL" in error for error in errors))

    def test_duplicate_record_id_is_rejected(self):
        row = self.valid_row()
        errors, _ = validate_data.validate_csv(self.write_csv([row, row]))
        self.assertTrue(any("duplicate record_id" in error for error in errors))

    def test_schema_matches_validator(self):
        self.assertEqual([], validate_data.validate_schema())


if __name__ == "__main__":
    unittest.main()
