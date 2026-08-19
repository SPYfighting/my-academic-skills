#!/usr/bin/env python3
"""Run every skill's self-check. Nothing here needs editing when a skill is added.

Convention: a skill is any top-level directory holding a SKILL.md. If it also
has scripts/selfcheck.py, that file is its self-check and this runner calls it.
A skill without one is reported as unchecked rather than silently passing.

    python check.py
    python check.py --verbose
    python check.py binder-design-campaign     # one skill

Standard library only. Exit code 0 when every self-check passed.
"""

import argparse
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))


def find_skills():
    for name in sorted(os.listdir(REPO)):
        path = os.path.join(REPO, name)
        if name.startswith(".") or not os.path.isdir(path):
            continue
        if os.path.isfile(os.path.join(path, "SKILL.md")):
            yield name, path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skills", nargs="*", help="skill names; default is all of them")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    skills = [(n, p) for n, p in find_skills() if not args.skills or n in args.skills]
    if not skills:
        print("no skills found" if not args.skills else
              "no skill matched {}".format(args.skills), file=sys.stderr)
        return 1

    failed, unchecked = [], []
    for name, path in skills:
        selfcheck = os.path.join(path, "scripts", "selfcheck.py")
        # Flush before handing the terminal to the child, or the parent's
        # buffered headers arrive after the child's unbuffered output.
        print("=" * 70)
        print(name)
        print("=" * 70, flush=True)
        if not os.path.isfile(selfcheck):
            print("  no scripts/selfcheck.py; nothing verified here")
            unchecked.append(name)
            continue
        cmd = [sys.executable, selfcheck] + (["--verbose"] if args.verbose else [])
        proc = subprocess.run(cmd, cwd=path)
        if proc.returncode != 0:
            failed.append(name)
        print("")

    print("=" * 70)
    if failed:
        print("FAILED: " + ", ".join(failed))
    if unchecked:
        print("UNCHECKED (no self-check): " + ", ".join(unchecked))
    if not failed and not unchecked:
        print("all {} skill(s) passed".format(len(skills)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
