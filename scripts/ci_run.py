"""CI runner: every unittest module under scripts/, one process per module, minus the listed Bifrost seam tests.

An excluded ID that no longer exists fails the run, so the exclusion list cannot go stale unnoticed.
test_p3a (CLI acceptance) and test_p7 (P7 report runner) are not unittest modules and run separately.
"""
import argparse, json, os, subprocess, sys, unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

R = Path(__file__).resolve().parents[1]
NOT_UNITTEST = {"test_p3a", "test_p7"}


def ids(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from ids(t)
        else:
            yield t


def child(module, excluded):
    sys.path[:0] = [str(R / "backend"), str(R / "scripts")]
    tests = list(ids(unittest.defaultTestLoader.loadTestsFromName(module)))
    seen = [t.id() for t in tests if t.id() in excluded]
    run = unittest.TestSuite(t for t in tests if t.id() not in excluded)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(run)
    print(json.dumps({"module": module, "ran": result.testsRun, "failures": len(result.failures),
                      "errors": len(result.errors), "skipped": len(result.skipped), "excluded": seen}))
    return 0 if result.wasSuccessful() else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--child"); p.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    a = p.parse_args()
    excluded = {l.strip() for l in (R / "scripts/ci_bifrost_seam_tests.txt").read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")}
    if a.child:
        return child(a.child, excluded)

    modules = sorted(f.stem for f in (R / "scripts").glob("test_*.py") if f.stem not in NOT_UNITTEST)

    def run(m):
        c = subprocess.run([sys.executable, "-B", __file__, "--child", m], cwd=R / "scripts",
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        line = c.stdout.strip().splitlines()[-1] if c.stdout.strip() else "{}"
        try:
            summary = json.loads(line)
        except ValueError:
            summary = {"module": m}
        return m, c.returncode, summary, c.stderr

    with ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(run, modules))

    failed, seen, ran = [], set(), 0
    for m, rc, s, err in results:
        ran += s.get("ran", 0); seen.update(s.get("excluded", []))
        status = "ok" if rc == 0 else "FAILED"
        print(f"{m}: {status} ran={s.get('ran', '?')} failures={s.get('failures', '?')} errors={s.get('errors', '?')} "
              f"skipped={s.get('skipped', '?')} excluded={len(s.get('excluded', []))}")
        if rc:
            failed.append(m); print(err[-4000:], file=sys.stderr)
    stale = sorted(excluded - seen)
    print(f"modules={len(modules)} tests_ran={ran} excluded_bifrost_seam={len(seen)} failed_modules={len(failed)}")
    if stale:
        print("Excluded IDs that no longer exist (update scripts/ci_bifrost_seam_tests.txt):", *stale, sep="\n  ")
    return 1 if failed or stale else 0


if __name__ == "__main__":
    sys.exit(main())
