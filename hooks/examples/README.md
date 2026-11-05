# Hook examples

Each file here is a working starting point. To activate one, copy it into the hooks
folder as the stage name:

| example | becomes | runs |
|---|---|---|
| `01_script_without_ai.py` | `before_script.py` | before the AI, can replace it entirely |
| `02_design_and_copy.py` | `before_render.py` | after the script, before composing |
| `03_publish.py` | `after_render.py` | after the mp4 exists |

The Extend tab in the app creates empty versions of all three for you, and
`Open folder` takes you to the right place.

## The contract

```
stdin  → JSON payload
stdout → JSON answer (or nothing)
```

Python hooks define `run(payload)` and return a dict. `payload` is also available as
a global, so a script without functions still works:

```python
result = {"design": {"theme": "wine_sand"}}
```

JavaScript hooks (`before_render.js`) get the same payload on stdin and print a JSON
object; they run with `node`, so Node has to be installed.

A hook that raises, times out (5 min) or prints junk is logged and skipped — it can
never break a render.
