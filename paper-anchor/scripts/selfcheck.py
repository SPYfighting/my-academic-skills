#!/usr/bin/env python3
"""Check the bundled Paper Anchor template and fictional example offline."""

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CLAIM = re.compile(r"^### (R[1-9][0-9]*)\b")
EVIDENCE = re.compile(r"(R[1-9][0-9]*)\.E[1-9][0-9]*")
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
COMPLETED = "完成"
IN_PROGRESS = "进行中"
BLANK = "—"
NON_SUPPORTING = "不支持"


def fixture_errors(text, directory):
    """Check the examples' six-column tables and local fixture links."""
    errors = []
    current_claim = None
    claims, evidence = set(), set()
    for line in text.splitlines():
        heading = CLAIM.match(line)
        if heading:
            current_claim = heading[1]
            if current_claim in claims:
                errors.append("duplicate claim ID")
            claims.add(current_claim)
        if not line.startswith("| R"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        match = EVIDENCE.fullmatch(cells[0])
        if len(cells) != 6 or not match or match[1] != current_claim:
            errors.append("malformed evidence row")
            continue
        evidence_id, work, status, interpretation, result, artifact = cells
        if evidence_id in evidence:
            errors.append("duplicate evidence ID")
        evidence.add(evidence_id)
        if not work or not status:
            errors.append("missing planned work or analysis status")
        artifact_links = LINK.findall(artifact)
        for link_type, links in (("task", LINK.findall(work)), ("artifact", artifact_links)):
            for link in links:
                path = Path(link.split("#", 1)[0])
                if path.is_absolute() or ".." in path.parts or not (directory / path).is_file():
                    errors.append(f"missing or invalid {link_type} link")
        if status == COMPLETED:
            if interpretation in ("", BLANK) or result in ("", BLANK):
                errors.append("completed analysis lacks interpretation or result")
            if not artifact_links:
                errors.append("completed analysis lacks a local fixture artifact")
        elif interpretation != BLANK:
            errors.append("unfinished analysis has a scientific interpretation")
    if not claims or not evidence:
        errors.append("no claim or evidence example")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="list individual checks")
    args = parser.parse_args()
    template = ROOT / "templates/PAPER.md"
    example = ROOT / "examples/PAPER.example.md"
    template_text = template.read_text(encoding="utf-8")
    example_text = example.read_text(encoding="utf-8")

    failures = []

    def check(label, valid):
        if not valid:
            failures.append(label)
            print("FAIL  " + label)
        elif args.verbose:
            print("ok    " + label)

    check("template evidence table", not fixture_errors(template_text, template.parent))
    check("example evidence tables and artifacts", not fixture_errors(example_text, example.parent))
    active = next((line for line in example_text.splitlines()
                   if line.startswith("| R") and f"| {IN_PROGRESS} |" in line), "")
    cells = active.split("|")
    task_links = LINK.findall(cells[2]) if len(cells) == 8 else []
    artifact_links = LINK.findall(cells[6]) if len(cells) == 8 else []
    task = next((link for link in task_links if link.startswith("tasks/")), None)
    table = next((link for link in artifact_links if link.startswith("fig/")), None)
    check("active evidence links its task, interim result, and table",
          task and table and any(link.startswith("results/") for link in artifact_links))
    if task:
        invalid = example_text.replace(task, "tasks/nonexistent-fixture.md", 1)
        check("missing active task rejected", "missing or invalid task link" in fixture_errors(invalid, example.parent))
    if table:
        invalid = example_text.replace(table, "fig/nonexistent-fixture.md", 1)
        check("missing active table rejected",
              "missing or invalid artifact link" in fixture_errors(invalid, example.parent))
    negative = f"| {COMPLETED} | {NON_SUPPORTING} |"
    row = next((line for line in example_text.splitlines()
                if line.startswith("| R") and negative in line), None)
    check("negative evidence shown as completed", row is not None)
    if row is not None:
        no_interpretation = row.replace(negative, f"| {COMPLETED} | {BLANK} |", 1)
        invalid = example_text.replace(row, no_interpretation, 1)
        check("missing interpretation rejected",
              "completed analysis lacks interpretation or result" in fixture_errors(invalid, example.parent))
        broken_row = LINK.sub("[missing](results/nonexistent-fixture.md)", row)
        invalid = example_text.replace(row, broken_row, 1)
        check("missing result file rejected",
              "missing or invalid artifact link" in fixture_errors(invalid, example.parent))
        duplicate = example_text.replace(row, row + "\n" + row, 1)
        check("duplicate evidence ID rejected", "duplicate evidence ID" in fixture_errors(duplicate, example.parent))
    if not failures:
        print("PASS  Paper Anchor offline fixtures")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
