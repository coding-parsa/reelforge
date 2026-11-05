"""Entry point for `python -m reelforge.hookrunner <hook.py> [--out result.json]`.

Reads the payload as JSON on stdin, executes the hook file, and writes the returned
dict as JSON — to the --out file when given, else to stdout. The file exists because
the packaged app is a windowed exe and has no usable stdout.

Kept deliberately tiny: nothing here may import the app.
"""
from __future__ import annotations

import json
import sys
import traceback


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(json.dumps({"_error": "no hook path"}))
        return 2
    path = argv[0]
    out_path = ""
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 < len(argv):
            out_path = argv[i + 1]
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    result: dict = {}
    try:
        src = open(path, encoding="utf-8").read()
        ns: dict = {"__name__": "reelforge_hook", "__file__": path, "payload": payload,
                    "print": lambda *a, **k: print(*a, file=sys.stderr, **k)}
        exec(compile(src, path, "exec"), ns)   # noqa: S102 — user code, by design
        fn = ns.get("run") or ns.get("main")
        if callable(fn):
            out = fn(payload)
        else:
            out = ns.get("result")
        if isinstance(out, dict):
            result = out
        elif out is not None:
            result = {"_error": f"the hook returned {type(out).__name__}, expected a dict"}
    except Exception:
        result = {"_error": traceback.format_exc(limit=3)[-800:]}

    data = json.dumps(result, ensure_ascii=False, default=str)
    if out_path:
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(data)
            return 0
        except Exception:
            pass
    try:
        sys.stdout.write(data)
        sys.stdout.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
