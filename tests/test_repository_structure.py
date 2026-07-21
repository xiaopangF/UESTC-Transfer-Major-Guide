import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class RepositoryStructureTests(unittest.TestCase):
    def test_required_contribution_files_exist(self):
        required_files = [
            "CONTRIBUTING.md",
            "PRIVACY.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/experience.yml",
            ".github/ISSUE_TEMPLATE/exam-recall.yml",
            ".github/ISSUE_TEMPLATE/data-update.yml",
            "templates/面试与转专业经验模板.md",
            "templates/机考回忆模板.md",
            "templates/年度流程模板.md",
        ]
        for relative_path in required_files:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_exam_area_accepts_recollections_only(self):
        exam_template = (ROOT / "templates" / "机考回忆模板.md").read_text(
            encoding="utf-8"
        )
        issue_form = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "exam-recall.yml"
        ).read_text(encoding="utf-8")
        exam_index = (
            ROOT / "docs" / "exams" / "computer" / "计算机专业机考回忆索引.md"
        ).read_text(encoding="utf-8")

        combined = "\n".join([exam_template, issue_form, exam_index])
        self.assertIn("record_type: computer_exam_recall", exam_template)
        self.assertIn("只收录", exam_index)
        self.assertNotIn("material_type:", combined)
        self.assertNotIn("official_public", combined)
        self.assertNotIn("original_practice", combined)

    def test_local_markdown_links_resolve(self):
        failures = []
        for markdown_path in ROOT.rglob("*.md"):
            content = markdown_path.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(content):
                clean_target = target.split("#", 1)[0].split("?", 1)[0]
                if (
                    not clean_target
                    or "://" in clean_target
                    or clean_target.startswith("../../issues/")
                ):
                    continue
                resolved = markdown_path.parent / clean_target
                if not resolved.exists():
                    failures.append(
                        f"{markdown_path.relative_to(ROOT)} -> {target}"
                    )
        self.assertEqual([], failures, "Broken local links:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
