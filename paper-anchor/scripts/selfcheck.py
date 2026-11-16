#!/usr/bin/env python3
"""Run the offline Paper Anchor checks against synthetic Markdown fixtures."""

import argparse
from pathlib import Path
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="list individual tests")
    args = parser.parse_args()
    tests = Path(__file__).resolve().parents[1] / "tests"
    suite = unittest.defaultTestLoader.discover(str(tests))
    if suite.countTestCases() == 0:
        print("FAIL: no Paper Anchor tests discovered")
        return 1
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
