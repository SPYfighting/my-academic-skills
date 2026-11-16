# -*- coding: utf-8 -*-
"Run with: python -m unittest discover -s tests (standard library only)."
import importlib.util
import io
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("check_paper", os.path.join(ROOT, "scripts", "check_paper.py"))
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

EXAMPLE = os.path.join(ROOT, "examples", "PAPER.example.md")
TEMPLATE = os.path.join(ROOT, "templates", "PAPER.md")


def run(path, *args):
    out = io.StringIO()
    import contextlib
    with contextlib.redirect_stdout(out):
        code = cp.main([path] + list(args))
    return code, out.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        shutil.copytree(os.path.join(ROOT, "examples"), os.path.join(self.tmp, "ex"))
        self.path = os.path.join(self.tmp, "ex", "PAPER.example.md")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, old, new):
        with open(self.path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn(old, text)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new, 1))

    def errors(self):
        return [m for _, m in self.checked().errors]

    def checked(self):
        paper = cp.load(self.path)
        paper.check()
        return paper

    def edit_evidence(self, eid, **updates):
        fields = ("id", "what", "status", "verdict", "result", "artifact")
        contents = Path(self.path).read_text(encoding="utf-8")
        row = next(line for line in contents.splitlines() if line.startswith("| " + eid + " |"))
        values = dict(zip(fields, cp.split_row(row)))
        values.update(updates)
        self.edit(row, "| " + " | ".join(values[field] for field in fields) + " |")


class TestGood(unittest.TestCase):
    def test_example_passes_clean(self):
        code, out = run(EXAMPLE, "--strict")
        self.assertEqual(code, 0, out)

    def test_template_passes_with_expected_warnings(self):
        p = cp.load(TEMPLATE)
        p.check()
        self.assertEqual(p.errors, [])
        text = " ".join(m for _, m in p.warnings)
        self.assertIn("Replace placeholders", text)

    def test_init_creates_valid_file(self):
        d = tempfile.mkdtemp()
        try:
            target = os.path.join(d, "PAPER.md")
            code, _ = run(target, "--init")
            self.assertEqual(code, 0)
            p = cp.load(target)
            p.check()
            self.assertEqual(p.errors, [])
        finally:
            shutil.rmtree(d)

    def test_init_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PAPER.md"
            original = b"# existing content\n"
            path.write_bytes(original)
            with patch.object(cp.sys, "stderr", new=io.StringIO()) as stderr:
                code, _ = run(str(path), "--init")
            self.assertEqual(code, 2)
            self.assertIn("will not overwrite", stderr.getvalue())
            self.assertEqual(path.read_bytes(), original)


class TestBroken(Base):
    def test_done_without_artifact(self):
        self.edit_evidence("R1.E4", status="✅ 完成", verdict="不支持", result="p=0.34")
        self.assertTrue(any("requires an artifact path" in e for e in self.errors()))

    def test_missing_artifact_file(self):
        os.remove(os.path.join(self.tmp, "ex", "results", "r3_cost.md"))
        self.assertTrue(any("Artifact path does not exist" in e for e in self.errors()))

    def test_supported_with_open_evidence_warns(self):
        self.edit("- **状态**：🔄 进行中\n- **图表**：Fig. 3", "- **状态**：✅ 已支持\n- **图表**：Fig. 3")
        code, out = run(self.path, "--fix-dashboard")
        self.assertEqual(code, 0, out)
        self.assertIn("unfinished analyses", out)

    def test_supported_without_completed_evidence_fails(self):
        self.edit("- **状态**：🔄 进行中\n- **图表**：Fig. 4", "- **状态**：✅ 已支持\n- **图表**：Fig. 4")
        self.edit_evidence("R4.E1", status="⬜ 待做", verdict="—")
        self.assertTrue(any("require at least one completed evidence item" in e for e in self.errors()))

    def test_no_lock_mechanism(self):
        code, out = run(self.path, "--strict")
        self.assertEqual(code, 0, out)
        self.assertFalse(any(f.endswith(".lock.json") for f in os.listdir(os.path.dirname(self.path))))

    def test_bad_status_and_duplicate_id(self):
        self.edit_evidence("R2.E3", id="R2.E1", status="做完了")
        errs = self.errors()
        self.assertTrue(any("Unknown status" in e for e in errs))
        self.assertTrue(any("Duplicate" in e for e in errs))

    def test_dashboard_drift_and_fix(self):
        self.edit_evidence("R1.E4", status="🔄 进行中")
        self.edit("- **下一步**：补 Adapter 基线", "- **下一步**：先做显著性检验，再补 Adapter 基线")
        self.assertTrue(any("Dashboard differs" in e for e in self.errors()))
        code, out = run(self.path, "--fix-dashboard")
        self.assertEqual(code, 0, out)

    def test_missing_changelog(self):
        with open(self.path, encoding="utf-8") as f:
            text = f.read()
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text.split("## 变更日志")[0])
        code, out = run(self.path)
        self.assertEqual(code, 1)
        self.assertIn("Missing section", out)

    def test_completed_and_pending_verdicts(self):
        self.edit_evidence("R3.E1", verdict="—")
        self.edit_evidence("R4.E2", verdict="部分支持")
        errs = self.errors()
        self.assertTrue(any("R3.E1" in err and "valid interpretation" in err for err in errs))
        self.assertTrue(any("R4.E2" in err and "until the analysis is completed" in err for err in errs))

    def test_supported_with_only_inconclusive_or_unassessed_verdicts_warns(self):
        self.edit_evidence("R3.E1", verdict="无法判定")
        self.edit_evidence("R3.E2", verdict="未判读")
        code, out = run(self.path)
        self.assertEqual(code, 0, out)
        self.assertIn("without supporting or partially supporting evidence", out)

    def test_evidence_header_separator_column_counts_must_match(self):
        body = Path(self.path).read_text(encoding="utf-8")
        lines = body.splitlines()
        header = next(i for i, line in enumerate(lines) if line.startswith("| 证据 |"))
        self.edit(lines[header + 1], "|---|---|---|---|---|")
        self.assertTrue(any("Evidence separator must match the header width" in err for err in self.errors()))

    def test_technical_failure_reason_required(self):
        self.edit_evidence("R4.E2", status="🛑 技术失败")
        self.assertTrue(any("Record the reason or symptoms of technical failure" in err for err in self.errors()))

    def test_directory_and_remote_artifacts(self):
        self.edit_evidence("R3.E1", artifact="[结果目录](results)")
        self.edit_evidence("R3.E2", artifact="[外部结果](https://example.invalid/missing)")
        checked = self.checked()
        self.assertTrue(any("Artifact path is not a file" in msg for _, msg in checked.errors))
        self.assertTrue(any("External artifact link has not been verified" in msg for _, msg in checked.warnings))

    def test_cli_diagnostics_are_ascii_with_unicode_input(self):
        self.edit_evidence("R3.E1", artifact="[结果](results/缺失.md)")
        code, out = run(self.path)
        self.assertEqual(code, 1)
        self.assertTrue(out.isascii(), out)
        self.assertIn(r"results/\u7f3a\u5931.md", out)

    def test_urlencoded_relative_link_to_file(self):
        results = Path(self.path).parent / "results"
        (results / "result note#1.md").write_text("data", encoding="utf-8")
        self.edit_evidence("R3.E1", artifact="[结果](results/result%20note%231.md#section)")
        code, out = run(self.path, "--strict")
        self.assertEqual(code, 0, out)

    def test_impossible_calendar_date(self):
        oldest_date = cp.load(self.path).changelog[0][0]
        self.edit("| " + oldest_date + " |", "| 2026-02-30 |")
        self.assertTrue(any("valid YYYY-MM-DD" in err for err in self.errors()))

    def test_dashboard_markers_must_stay_inside_section(self):
        path = Path(self.path)
        body = path.read_text(encoding="utf-8").replace(cp.DASH_END, "")
        path.write_bytes((body + "\n" + cp.DASH_END + "\n").encode("utf-8"))
        original = path.read_bytes()
        code, out = run(self.path, "--fix-dashboard")
        self.assertEqual(code, 1, out)
        self.assertIn("requires one correctly ordered pair of block markers", out)
        self.assertEqual(path.read_bytes(), original)

    def test_dashboard_preserves_crlf_and_other_bytes(self):
        self.edit("| 结论 | 一句话 | 状态 | 证据进度 | 下一步 |",
                  "| 结论 | 一句话 | 状态 | 过期看板 | 下一步 |")
        path = Path(self.path)
        original = path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8")
        path.write_bytes(original)
        code, out = run(self.path, "--fix-dashboard")
        self.assertEqual(code, 0, out)
        self.assertEqual(path.read_bytes(), original.replace("过期看板".encode("utf-8"), "证据进度".encode("utf-8")))

    def test_dashboard_detects_concurrent_edit(self):
        self.edit("| 结论 | 一句话 | 状态 | 证据进度 | 下一步 |",
                  "| 结论 | 一句话 | 状态 | 过期看板 | 下一步 |")
        paper = cp.load(self.path)
        path = Path(self.path)
        newer = path.read_bytes() + b"\n"
        path.write_bytes(newer)
        with self.assertRaisesRegex(OSError, "changed during this check"):
            paper.fix_dashboard()
        self.assertEqual(path.read_bytes(), newer)

    def test_staged_check_uses_index_bytes(self):
        path = Path(self.path)
        original = path.read_bytes()
        changed = b"# incomplete working copy\n"
        path.write_bytes(changed)
        with patch.object(cp.subprocess, "run") as git:
            git.return_value = cp.subprocess.CompletedProcess([], 0, stdout=original, stderr=b"")
            code, out = run(self.path, "--staged", "--strict")
        git.assert_called_once_with(["git", "show", ":./" + path.name], cwd=str(path.parent), capture_output=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(path.read_bytes(), changed)


class TestEvidenceSemantics(Base):
    def test_negative_result_counts_as_complete(self):
        checked = self.checked()
        evidence = next(e for r in checked.results for e in r.evidence if e.id == "R4.E1")
        self.assertEqual((evidence.status, evidence.verdict), ("done", "不支持"))
        row = next(row for row in checked.render_dashboard() if "**R4**" in row)
        self.assertIn("1/2 · ❌1", row)

    def test_technical_failure_is_separate_from_negative_result(self):
        self.edit_evidence("R4.E2", status="🛑 技术失败", result="运行超过内存上限")
        code, out = run(self.path, "--fix-dashboard", "--strict")
        self.assertEqual(code, 0, out)
        row = next(row for row in cp.load(self.path).render_dashboard() if "**R4**" in row)
        self.assertIn("1/2 · ❌1 🛑1", row)

    def test_legacy_evidence_does_not_infer_support(self):
        path = Path(self.path)
        lines = path.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            cells = cp.split_row(line)
            if not cells or len(cells) != 6:
                continue
            if cells[0] == "证据":
                cells[2] = "状态"
            elif not cp.is_sep(cells) and not cp.EV_ID_RE.fullmatch(cells[0]):
                continue
            elif cells[3] == "不支持":
                cells[2] = "❌ 不支持"
            del cells[3]
            lines[i] = "| " + " | ".join(cells) + " |"
        path.write_bytes("\n".join(lines).encode("utf-8"))
        code, out = run(self.path, "--fix-dashboard", "--strict")
        self.assertEqual(code, 0, out)
        paper = cp.load(self.path)
        by_id = {e.id: e for result in paper.results for e in result.evidence}
        self.assertEqual((by_id["R3.E1"].status, by_id["R3.E1"].verdict), ("done", "未判读"))
        self.assertEqual((by_id["R4.E1"].status, by_id["R4.E1"].verdict), ("done", "不支持"))
        self.assertIn("❌ 不支持", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
