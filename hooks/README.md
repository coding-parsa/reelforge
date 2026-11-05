# Hooks

Drop one file per stage in this folder and Reelforge runs it inside the pipeline.
`before_script` can build the script itself (no AI), `before_render` can change the
cards or the design, `after_render` gets the finished video (upload it, copy it, log it).

    before_script.py   {"project","article","config"}        -> {"script": {...}}
    before_render.py   {"project","script","design","brand"} -> {"script","design","brand"}
    after_render.py    {"project","video","cover","meta"}    -> {"url": "https://…"}

Python hooks define `run(payload)` and return a dict; `payload` is also a global.
JavaScript hooks (`*.js`) print JSON on stdout and run with Node.
Any output the app does not understand is ignored, and a crashing hook is logged
instead of stopping the render.
