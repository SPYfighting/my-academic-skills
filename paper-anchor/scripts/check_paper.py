#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate PAPER.md with the Python 3.8+ standard library.

See --help for the command-line options. Exit 0 on success, 1 on
validation failure, and 2 on usage or file errors.
"""
import argparse
import datetime
import difflib
import os
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import unquote

VERSION = "0.3.1"
VS16 = "\ufe0f"

# (英文键, 图标, 中文标签)
RESULT_STATUS = [
    ("idea", "💡", "设想"),
    ("active", "🔄", "进行中"),
    ("supported", "✅", "已支持"),
    ("refuted", "❌", "被推翻"),
    ("parked", "💤", "搁置"),
]
EVIDENCE_STATUS = [
    ("todo", "⬜", "待做"),
    ("doing", "🔄", "进行中"),
    ("blocked", "🚧", "受阻"),
    ("done", "✅", "完成"),
    ("technical_failure", "🛑", "技术失败"),
    ("dropped", "💤", "搁置"),
]
LEGACY_EVIDENCE_STATUS = EVIDENCE_STATUS + [("failed", "❌", "不支持")]
EVIDENCE_VERDICTS = ("支持", "部分支持", "不支持", "无法判定", "未判读")
PROPOSAL_STATUS = [
    ("pending", "⏳", "待确认"),
    ("accepted", "👍", "已采纳"),
    ("rejected", "👎", "已拒绝"),
]

SECTIONS = [
    ("dashboard", ("一览", "dashboard", "at a glance")),
    ("handoff", ("交接", "handoff")),
    ("thesis", ("论点", "thesis")),
    ("results", ("结论", "results")),
    ("proposals", ("提议", "proposals")),
    ("questions", ("待决问题", "open questions")),
    ("changelog", ("变更日志", "changelog")),
]
SECTION_NAMES = {
    "dashboard": "Dashboard", "handoff": "Handoff",
    "thesis": "Thesis", "results": "Results",
    "proposals": "Proposals", "questions": "Open questions",
    "changelog": "Changelog",
}
F_CLAIM = ("主张", "claim")
F_STATUS = ("状态", "status")
F_FIGURE = ("图表", "figure", "figure/table")
F_NEXT = ("下一步", "next")
F_THESIS = ("一句话论点", "thesis", "one-line thesis")
F_LAST = ("上一棒", "last")
F_DONE = ("刚完成", "just done")
F_HANDNEXT = ("下一棒建议", "next up")

DASH_START = "<!-- paper-anchor:dashboard:start · 本块由 check_paper.py --fix-dashboard 生成，请勿手改 -->"
DASH_START_PREFIX = "<!-- paper-anchor:dashboard:start"
DASH_END = "<!-- paper-anchor:dashboard:end -->"

EMPTY = {"", "—", "-", "–", "无", "n/a", "N/A", "none"}
PLACEHOLDER = "待填"
DATE_PH = "YYYY-MM-DD"
SUMMARY_MAX = 80
THESIS_MAX = 120

FIELD_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*[：:]?\s*(.*?)\s*$")
RESULT_RE = re.compile(r"^###\s+(R\d+)\s*[·:：.\-—]\s*(.+?)\s*$")
EV_ID_RE = re.compile(r"^R(\d+)\.E\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r'\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+"[^"]*")?\)')
CODE_RE = re.compile(r"`([^`]+)`")
URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def norm(s):
    return s.replace(VS16, "").strip()


def is_key(name, aliases):
    return norm(name).rstrip("：:").strip().lower() in aliases


def label(vocab, key):
    for k, e, l in vocab:
        if k == key:
            return e + " " + l
    return key


def parse_status(text, vocab):
    "Return the status key and an error message, if any."
    t = norm(text)
    allowed = " / ".join(key for key, _, _ in vocab)
    if not t:
        return None, "Missing status; expected: " + allowed
    for key, emo, lab in vocab:
        if t.startswith(emo):
            rest = t[len(emo):].strip()
            if rest and rest != lab and rest.lower() != key:
                return None, "Status marker %s conflicts with the value '%s' (expected '%s %s')" % (emo, rest, emo, lab)
            return key, None
    for key, emo, lab in vocab:
        if t == lab or t.lower() == key:
            return key, None
    return None, "Unknown status '%s'; expected: %s" % (text.strip(), allowed)


def split_row(line):
    s = line.strip()
    if not s.startswith("|"):
        return None
    s = s.replace("\\|", "\x00")[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip().replace("\x00", "|") for c in s.split("|")]


def is_sep(cells):
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells)


def table_rows(lines, start, end):
    "Return zero-based line numbers and cells, skipping headers and separators."
    out = []
    i = start
    while i < end:
        cells = split_row(lines[i])
        if cells is None:
            i += 1
            continue
        nxt = split_row(lines[i + 1]) if i + 1 < end else None
        if nxt is not None and is_sep(nxt) and not is_sep(cells):
            i += 2  # 表头 + 分隔行
            continue
        if not is_sep(cells):
            out.append((i, cells))
        i += 1
    return out


def clean_id(s):
    return s.strip().strip("*`").strip()


def esc(s):
    return s.replace("|", "\\|")


def calendar_date(value):
    if DATE_RE.fullmatch(value):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            pass
    return None


class Evidence(object):
    def __init__(self, eid, status, verdict, summary, art_cell, line, legacy):
        self.id, self.status, self.verdict = eid, status, verdict
        self.summary, self.art_cell, self.line = summary, art_cell, line
        self.legacy = legacy
        self.paths = []


class Result(object):
    def __init__(self, rid, title, line):
        self.id, self.title, self.line = rid, title, line
        self.claim = self.status = self.figure = self.next = None
        self.status_line = line
        self.evidence = []


class Paper(object):
    def __init__(self, path, raw=None):
        self.path = os.path.abspath(path)
        self.base = os.path.dirname(self.path)
        if raw is None:
            with open(self.path, encoding="utf-8", newline="") as f:
                raw = f.read()
        self.raw = raw
        self.raw_lines = raw.split("\n")
        self.lines = [line[:-1] if line.endswith("\r") else line for line in self.raw_lines]
        self.errors, self.warnings = [], []
        self.sections = {}
        self.thesis = {}
        self.thesis_line = None
        self.results = []
        self.proposals = []  # (id, status, line)
        self.q_open = self.q_closed = 0
        self.changelog = []  # (date, who, what, why, line)
        self.handoff = {}
        self.dash = None  # (start, end) 0基

    # ---------- 记录问题 ----------
    def err(self, line, msg):
        self.errors.append((line, msg))

    def warn(self, line, msg):
        self.warnings.append((line, msg))

    # ---------- 解析 ----------
    def parse(self):
        L = self.lines
        heads, fence = [], False
        dash_starts, dash_ends = [], []
        for i, l in enumerate(L):
            if l.lstrip().startswith("```"):
                fence = not fence
            if fence:
                continue
            if re.match(r"^##\s", l):
                heads.append(i)
            if l.strip().startswith(DASH_START_PREFIX):
                dash_starts.append(i)
            elif l.strip() == DASH_END:
                dash_ends.append(i)
        for n, i in enumerate(heads):
            end = heads[n + 1] if n + 1 < len(heads) else len(L)
            h = L[i].lower()
            for key, words in SECTIONS:
                if any(w in h for w in words):
                    if key in self.sections:
                        self.err(i + 1, "Duplicate section: %s" % SECTION_NAMES[key])
                    else:
                        self.sections[key] = (i, end)
                    break
        for key, _ in SECTIONS:
            if key not in self.sections:
                self.err(None, "Missing section: ## %s" % SECTION_NAMES[key])
        if "dashboard" in self.sections:
            start, end = self.sections["dashboard"]
            if len(dash_starts) == len(dash_ends) == 1 and start < dash_starts[0] < dash_ends[0] < end:
                self.dash = (dash_starts[0], dash_ends[0])
            else:
                self.err(start + 1, "Dashboard requires one correctly ordered pair of block markers (%s ... %s)" % (DASH_START_PREFIX + " -->", DASH_END))
        self._thesis()
        self._results()
        self._proposals()
        self._questions()
        self._changelog()
        self._handoff()

    def _fields(self, key):
        if key not in self.sections:
            return []
        s, e = self.sections[key]
        out = []
        for i in range(s + 1, e):
            m = FIELD_RE.match(self.lines[i])
            if m:
                out.append((i, m.group(1), m.group(2)))
        return out

    def _thesis(self):
        for i, k, v in self._fields("thesis"):
            name = norm(k).rstrip("：:")
            self.thesis[name] = v
            if is_key(k, F_THESIS):
                self.thesis_line = i
        if "thesis" in self.sections and self.thesis_line is None:
            self.err(self.sections["thesis"][0] + 1, "Thesis section is missing the one-line thesis field")
        elif self.thesis_line is not None:
            v = self.thesis_value()
            if not v:
                self.err(self.thesis_line + 1, "The one-line thesis is empty")
            elif len(v) > THESIS_MAX:
                self.warn(self.thesis_line + 1, "The one-line thesis has %d characters; use at most %d and expand in the research question" % (len(v), THESIS_MAX))

    def thesis_value(self):
        for k, v in self.thesis.items():
            if is_key(k, F_THESIS):
                return v
        return ""

    def _results(self):
        if "results" not in self.sections:
            return
        s, e = self.sections["results"]
        L = self.lines
        starts = []
        for i in range(s + 1, e):
            if L[i].startswith("### "):
                m = RESULT_RE.match(L[i])
                if not m:
                    self.err(i + 1, "Expected a result heading like '### R1: Short title'; found: %s" % L[i].strip())
                    continue
                starts.append((i, m.group(1), m.group(2)))
        if not starts:
            self.err(s + 1, "Results section has no result headings (for example, '### R1: Short title')")
        seen_r, seen_e = set(), set()
        for n, (i, rid, title) in enumerate(starts):
            end = starts[n + 1][0] if n + 1 < len(starts) else e
            r = Result(rid, title, i + 1)
            if rid in seen_r:
                self.err(i + 1, "Duplicate result ID %s" % rid)
            seen_r.add(rid)
            for j in range(i + 1, end):
                m = FIELD_RE.match(L[j])
                if not m:
                    continue
                k, v = m.group(1), m.group(2)
                if is_key(k, F_CLAIM):
                    r.claim = v
                elif is_key(k, F_STATUS):
                    r.status_line = j + 1
                    key, msg = parse_status(v, RESULT_STATUS)
                    if msg:
                        self.err(j + 1, "[%s] %s" % (rid, msg))
                    r.status = key
                elif is_key(k, F_FIGURE):
                    r.figure = v
                elif is_key(k, F_NEXT):
                    r.next = v
            width = None
            for j in range(i + 1, end - 1):
                cells = split_row(L[j])
                if cells and norm(cells[0]).lower() in ("证据", "evidence"):
                    width = len(cells)
                    separator = split_row(L[j + 1])
                    if width not in (5, 6):
                        self.err(j + 1, "[%s] Evidence header requires 6 columns (5 for legacy tables); found %d" % (rid, width))
                    if not is_sep(separator) or len(separator) != width:
                        self.err(j + 2, "[%s] Evidence separator must match the header width (%d columns)" % (rid, width))
                    break
            for j, cells in table_rows(L, i + 1, end):
                eid = clean_id(cells[0])
                if not EV_ID_RE.match(eid):
                    self.err(j + 1, "Expected an evidence ID like %s.E1; found '%s'" % (rid, cells[0]))
                    continue
                if len(cells) not in (5, 6) or (width is not None and len(cells) != width):
                    required = str(width) if width in (5, 6) else "6 (5 for legacy tables)"
                    self.err(j + 1, "[%s] Expected %s evidence columns; found %d" % (eid, required, len(cells)))
                    continue
                if not eid.startswith(rid + "."):
                    self.err(j + 1, "[%s] Listed under %s but does not start with %s" % (eid, rid, rid))
                if eid in seen_e:
                    self.err(j + 1, "Duplicate evidence ID %s" % eid)
                seen_e.add(eid)
                legacy = len(cells) == 5
                vocab = LEGACY_EVIDENCE_STATUS if legacy else EVIDENCE_STATUS
                key, msg = parse_status(cells[2], vocab)
                if msg:
                    self.err(j + 1, "[%s] %s" % (eid, msg))
                if legacy:
                    verdict = {"done": "未判读", "failed": "不支持"}.get(key, "—")
                    if key == "failed":
                        key = "done"
                else:
                    verdict = norm(cells[3])
                ev = Evidence(eid, key, verdict, cells[-2], cells[-1], j + 1, legacy)
                ev.paths = self._paths(ev)
                r.evidence.append(ev)
            self.results.append(r)

    def _paths(self, ev):
        cell = ev.art_cell.strip()
        if cell in EMPTY:
            return []
        paths = []
        for target in LINK_RE.findall(cell):
            if target.startswith("<"):
                target = target[1:-1]
            if not URL_RE.match(target):
                target = unquote(target.split("#", 1)[0])
            paths.append(target)
        rest = LINK_RE.sub("", cell)
        paths += CODE_RE.findall(rest)
        if not paths:
            self.warn(ev.line, "[%s] Write artifact paths as `path` or [name](path)" % ev.id)
            paths = [p.strip() for p in re.split(r"[,，;；、]", cell) if p.strip()]
        return paths

    def _proposals(self):
        if "proposals" not in self.sections:
            return
        s, e = self.sections["proposals"]
        seen = set()
        for j, cells in table_rows(self.lines, s + 1, e):
            pid = clean_id(cells[0])
            if not re.match(r"^P\d+$", pid):
                self.err(j + 1, "Expected a proposal ID like P1; found '%s'" % cells[0])
                continue
            if pid in seen:
                self.err(j + 1, "Duplicate proposal ID %s" % pid)
            seen.add(pid)
            if len(cells) != 5:
                self.err(j + 1, "[%s] Proposal rows require 5 columns (ID, status, proposal, rationale, author)" % pid)
                continue
            key, msg = parse_status(cells[1], PROPOSAL_STATUS)
            if msg:
                self.err(j + 1, "[%s] %s" % (pid, msg))
            if not cells[2] or not cells[3]:
                self.warn(j + 1, "[%s] Record both the proposal and its rationale" % pid)
            self.proposals.append((pid, key, j + 1))

    def _questions(self):
        if "questions" not in self.sections:
            return
        s, e = self.sections["questions"]
        for i in range(s + 1, e):
            l = self.lines[i].strip()
            if re.match(r"^[-*]\s+\[ \]", l):
                self.q_open += 1
            elif re.match(r"^[-*]\s+\[[xX]\]", l):
                self.q_closed += 1

    def _changelog(self):
        if "changelog" not in self.sections:
            return
        s, e = self.sections["changelog"]
        prev = None
        for j, cells in table_rows(self.lines, s + 1, e):
            if len(cells) != 4:
                self.err(j + 1, "Changelog rows require 4 columns (date, actor, change, reason)")
                continue
            d = cells[0]
            date = calendar_date(d)
            if d == DATE_PH:
                self.warn(j + 1, "Changelog date is still the %s placeholder" % DATE_PH)
            elif not date:
                self.err(j + 1, "Expected a valid YYYY-MM-DD changelog date; found '%s'" % d)
            elif prev and date < prev:
                self.warn(j + 1, "Changelog dates are out of order (%s precedes the previous valid date %s)" % (d, prev))
            if date:
                prev = date
            if not cells[1] or not cells[2]:
                self.err(j + 1, "Changelog requires an actor and a description of the change")
            elif not cells[3]:
                self.warn(j + 1, "Changelog entry has no reason")
            self.changelog.append(tuple(cells) + (j + 1,))
        if not self.changelog:
            self.err(s + 1, "Changelog requires at least one entry")

    def _handoff(self):
        if "handoff" not in self.sections:
            return
        for i, k, v in self._fields("handoff"):
            for aliases in (F_LAST, F_DONE, F_HANDNEXT):
                if is_key(k, aliases):
                    self.handoff[aliases[0]] = (v, i + 1)
        line = self.sections["handoff"][0] + 1
        for aliases in (F_LAST, F_DONE, F_HANDNEXT):
            if aliases[0] not in self.handoff or self.handoff[aliases[0]][0] in EMPTY:
                self.warn(line, "Handoff is missing the '%s' field" % aliases[0])
        if F_LAST[0] in self.handoff and self.changelog:
            v, ln = self.handoff[F_LAST[0]]
            m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
            handoff_date = calendar_date(m.group(1)) if m else None
            dates = map(calendar_date, (c[0] for c in self.changelog))
            last = max(filter(None, dates), default=None)
            if m and not handoff_date:
                self.warn(ln, "Invalid handoff date: %s" % m.group(1))
            elif handoff_date and last and handoff_date < last:
                self.warn(ln, "Handoff date %s precedes changelog date %s; review the handoff" % (handoff_date, last))

    # ---------- 语义检查 ----------
    def check(self):
        for r in self.results:
            self._check_result(r)
        ph = [i + 1 for i, l in enumerate(self.lines)
              if PLACEHOLDER in l and not l.lstrip().startswith("<!--")
              and not (self.dash and self.dash[0] <= i <= self.dash[1])]
        if ph:
            shown = "、".join(str(x) for x in ph[:12]) + ("…" if len(ph) > 12 else "")
            self.warn(None, "Replace placeholders in %d lines (%s)" % (len(ph), shown))
        self._check_dashboard()

    def _check_result(self, r):
        if r.claim is None or r.claim in EMPTY:
            self.err(r.line, "[%s] Missing claim field" % r.id)
        if r.status is None and not any(ln == r.status_line and "[%s]" % r.id in m for ln, m in self.errors):
            self.err(r.line, "[%s] Missing status field" % r.id)
        if r.figure is None or r.figure in EMPTY:
            self.warn(r.line, "[%s] Missing figure field (for example, Fig. 2)" % r.id)
        if r.status in ("idea", "active") and (r.next is None or r.next in EMPTY):
            self.warn(r.line, "[%s] Missing next step" % r.id)
        for ev in r.evidence:
            self._check_evidence(ev)
        active = [e for e in r.evidence if e.status != "dropped"]
        done = [e for e in active if e.status == "done"]
        against = [e.id for e in done if e.verdict == "不支持"]
        if not r.evidence:
            self.warn(r.line, "[%s] No evidence items recorded" % r.id)
        if r.status == "supported":
            if not done:
                self.err(r.status_line, "[%s] Supported results require at least one completed evidence item" % r.id)
            elif len(done) < len(active):
                left = ", ".join(e.id for e in active if e.status != "done")
                self.warn(r.status_line, "[%s] Result is marked supported with unfinished analyses: %s. Review the decision." % (r.id, left))
            if against:
                self.warn(r.status_line, "[%s] Result is marked supported with evidence against it: %s. Review the decision." % (r.id, ", ".join(against)))
            elif any(not e.legacy for e in done) and not any(e.verdict in ("支持", "部分支持") for e in done):
                self.warn(r.status_line, "[%s] Result is marked supported without supporting or partially supporting evidence. Review the decision." % r.id)
        elif r.status == "refuted":
            if not against:
                self.warn(r.status_line, "[%s] Result is marked refuted without evidence against it. Review the decision." % r.id)
        elif r.status == "idea":
            if any(e.status in ("doing", "done", "technical_failure", "blocked") for e in r.evidence):
                self.warn(r.status_line, "[%s] Work has started; consider marking the result in progress" % r.id)

    def _check_evidence(self, ev):
        st = ev.status
        if st == "done" and ev.verdict not in EVIDENCE_VERDICTS:
            self.err(ev.line, "[%s] Completed analysis requires a valid interpretation (%s); found '%s'" % (ev.id, " / ".join(EVIDENCE_VERDICTS), ev.verdict))
        elif st and st != "done" and ev.verdict not in EMPTY:
            self.err(ev.line, "[%s] Leave interpretation blank until the analysis is completed" % ev.id)
        if st == "done" and ev.summary in EMPTY:
            self.err(ev.line, "[%s] Completed analysis requires a one-line result" % ev.id)
        if st == "blocked" and ev.summary in EMPTY:
            self.warn(ev.line, "[%s] Record why the analysis is blocked in the result field" % ev.id)
        if st == "technical_failure" and ev.summary in EMPTY:
            self.err(ev.line, "[%s] Record the reason or symptoms of technical failure" % ev.id)
        if st == "done" and not ev.paths:
            if ev.legacy and ev.verdict == "不支持":
                self.warn(ev.line, "[%s] Legacy opposing evidence has no artifact path; add one for review" % ev.id)
            else:
                self.err(ev.line, "[%s] Completed analysis requires an artifact path (result, figure, or log)" % ev.id)
        if len(ev.summary) > SUMMARY_MAX:
            self.warn(ev.line, "[%s] Result has %d characters, over the %d limit; summarize it and link the details" % (ev.id, len(ev.summary), SUMMARY_MAX))
        for p in ev.paths:
            if URL_RE.match(p):
                self.warn(ev.line, "[%s] External artifact link has not been verified: %s" % (ev.id, p))
                continue
            full = os.path.join(self.base, p)
            if os.path.isfile(full):
                continue
            detail = "path is not a file" if os.path.exists(full) else "path does not exist"
            problem = self.err if st == "done" else self.warn
            problem(ev.line, "[%s] Artifact %s: %s (relative to the directory containing %s)" %
                    (ev.id, detail, p, os.path.basename(self.path)))

    # ---------- 一览 ----------
    def last_update(self):
        if not self.changelog:
            return "—"
        c = self.changelog[-1]
        return "%s（%s）" % (c[0], c[1])

    def render_dashboard(self):
        rows = []
        for r in self.results:
            active = [e for e in r.evidence if e.status != "dropped"]
            done = sum(1 for e in active if e.status == "done")
            bar = ("█" * done + "░" * (len(active) - done) + " ") if len(active) <= 12 else ""
            prog = "%s%d/%d" % (bar, done, len(active))
            indicators = [
                ("❌", sum(1 for e in active if e.status == "done" and e.verdict == "不支持")),
                ("🚧", sum(1 for e in active if e.status == "blocked")),
                ("🛑", sum(1 for e in active if e.status == "technical_failure")),
            ]
            extra = ["%s%d" % (icon, count) for icon, count in indicators if count]
            if extra:
                prog += " · " + " ".join(extra)
            st = label(RESULT_STATUS, r.status) if r.status else "？"
            nxt = r.next if r.next and r.next not in EMPTY else "—"
            rows.append("| **%s** | %s | %s | %s | %s |" % (r.id, esc(r.title), st, prog, esc(nxt)))
        pending = sum(1 for p in self.proposals if p[1] == "pending")
        pend = ("⚠️ **%d 条提议等你确认**（见「提议」）" % pending) if pending else "⏳ 待确认提议 0"
        out = [
            DASH_START,
            "**论点**：" + (self.thesis_value() or "—"),
            "",
            "| 结论 | 一句话 | 状态 | 证据进度 | 下一步 |",
            "|---|---|---|---|---|",
        ] + rows + [
            "",
            "%s · ❓ 待决问题 %d · 🕒 最后更新 %s" % (pend, self.q_open, self.last_update()),
            DASH_END,
        ]
        return out

    def _check_dashboard(self):
        if not self.dash:
            return
        s, e = self.dash
        cur = [l.rstrip() for l in self.lines[s:e + 1]]
        cur[0] = DASH_START if cur[0].strip().startswith(DASH_START_PREFIX) else cur[0]
        new = self.render_dashboard()
        if cur != new:
            diff = [d for d in difflib.unified_diff(cur, new, lineterm="", n=0)
                    if d[:1] in "+-" and not d.startswith(("+++", "---"))]
            msg = "Dashboard differs from the document. Run --fix-dashboard to regenerate it. Diff:\n" + \
                  "\n".join("        " + d for d in diff[:10])
            self.err(s + 1, msg)

    def fix_dashboard(self):
        if not self.dash:
            return False
        s, e = self.dash
        generated = self.render_dashboard()
        if generated == self.lines[s:e + 1]:
            return False
        terminator = "\r" if self.raw_lines[s].endswith("\r") else ""
        replacement = [line + terminator for line in generated[:-1]]
        closing_terminator = "\r" if self.raw_lines[e].endswith("\r") else ""
        replacement.append(generated[-1] + closing_terminator)
        data = "\n".join(self.raw_lines[:s] + replacement + self.raw_lines[e + 1:])
        target = os.path.realpath(self.path)
        mode = stat.S_IMODE(os.stat(target).st_mode)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                             dir=os.path.dirname(target), prefix=".paper-anchor-",
                                             delete=False) as tmp:
                tmp_path = tmp.name
                tmp.write(data)
                tmp.flush()
                os.fsync(tmp.fileno())
            with open(target, encoding="utf-8", newline="") as f:
                if f.read() != self.raw:
                    raise OSError("PAPER.md changed during this check. Merge updates, then rerun --fix-dashboard.")
            os.chmod(tmp_path, mode)
            os.replace(tmp_path, target)
            tmp_path = None
        finally:
            if tmp_path is not None:
                os.unlink(tmp_path)
        return True

    # ---------- 报告 ----------
    def stats(self):
        evs = [e for r in self.results for e in r.evidence]
        cnt = dict((k, 0) for k, _, _ in EVIDENCE_STATUS)
        for e in evs:
            if e.status in cnt:
                cnt[e.status] += 1
        parts = ", ".join("%s=%d" % (key, cnt[key]) for key, _, _ in EVIDENCE_STATUS)
        pending = sum(1 for p in self.proposals if p[1] == "pending")
        return "%d results; %d evidence items (%s); %d pending proposals; %d open questions" % (
            len(self.results), len(evs), parts, pending, self.q_open)


def ascii_diagnostic(text):
    # Keep arbitrary input and OS errors safe to print on ASCII terminals.
    return text.encode("ascii", errors="backslashreplace").decode("ascii")


def report(p, quiet=False, strict=False, out=None):
    out = out or sys.stdout
    def line(ln, msg):
        tag = ("L%-4d" % ln) if ln else "     "
        out.write(ascii_diagnostic("  %s %s\n" % (tag, msg)))
    try:
        rel = os.path.relpath(p.path)
    except ValueError:
        rel = p.path
    out.write(ascii_diagnostic("paper-anchor check: %s\n   %s\n" % (rel, p.stats())))
    if p.errors:
        out.write("\nErrors: %d\n" % len(p.errors))
        for ln, msg in sorted(p.errors, key=lambda x: x[0] or 0):
            line(ln, msg)
    if p.warnings and not quiet:
        out.write("\nWarnings: %d\n" % len(p.warnings))
        for ln, msg in sorted(p.warnings, key=lambda x: x[0] or 0):
            line(ln, msg)
    failed = bool(p.errors) or (strict and p.warnings)
    if failed:
        out.write("\nResult: FAIL\n")
    elif p.warnings:
        out.write("\nResult: PASS (%d warnings)\n" % len(p.warnings))
    else:
        out.write("\nResult: PASS\n")
    return 1 if failed else 0


def load(path, staged=False):
    raw = None
    if staged:
        base, filename = os.path.split(os.path.abspath(path))
        proc = subprocess.run(["git", "show", ":./" + filename], cwd=base, capture_output=True)
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", errors="replace").strip()
            raise OSError("Could not read %s from the Git index: %s" % (path, detail))
        raw = proc.stdout.decode("utf-8")
    p = Paper(path, raw)
    p.parse()
    return p


def find_template():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.path.join(here, "..", "templates", "PAPER.md"),
              os.path.join(here, "templates", "PAPER.md")):
        if os.path.exists(c):
            return os.path.normpath(c)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="paper-anchor: check the structure and consistency of PAPER.md")
    ap.add_argument("paper", nargs="?", default="PAPER.md")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--fix-dashboard", action="store_true", help="regenerate the dashboard, then check the document")
    mode.add_argument("--init", action="store_true", help="create PAPER.md from the template")
    mode.add_argument("--staged", action="store_true", help="read PAPER.md from the Git index")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--quiet", action="store_true", help="suppress individual warnings")
    ap.add_argument("--version", action="version", version="paper-anchor " + VERSION)
    a = ap.parse_args(argv)

    if a.init:
        tpl = find_template()
        if not tpl:
            sys.stderr.write("Cannot find templates/PAPER.md\n")
            return 2
        try:
            with open(tpl, encoding="utf-8") as f:
                text = f.read().replace(DATE_PH, datetime.date.today().isoformat())
            with open(a.paper, "x", encoding="utf-8") as f:
                f.write(text)
        except FileExistsError:
            sys.stderr.write(ascii_diagnostic("Already exists; will not overwrite: %s\n" % a.paper))
            return 2
        except (OSError, UnicodeError) as exc:
            sys.stderr.write(ascii_diagnostic("paper-anchor: %s\n" % exc))
            return 2
        print(ascii_diagnostic(
            "Created %s. Fill in confirmed claims and evidence, then run --fix-dashboard." % a.paper
        ))
        return 0

    if not a.staged and not os.path.isfile(a.paper):
        sys.stderr.write(ascii_diagnostic("File not found: %s (use --init to create it)\n" % a.paper))
        return 2
    try:
        p = load(a.paper, staged=a.staged)
        if a.fix_dashboard and p.fix_dashboard():
            print("Regenerated the dashboard.")
            p = load(a.paper)
    except (OSError, UnicodeError) as exc:
        sys.stderr.write(ascii_diagnostic("paper-anchor: %s\n" % exc))
        return 2
    p.check()
    return report(p, quiet=a.quiet, strict=a.strict)


if __name__ == "__main__":
    sys.exit(main())
