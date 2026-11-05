"""EXAMPLE — force a look, or tweak the cards, right before the render.

Copy to `<home>/hooks/before_render.py`. Return any subset of
{"script": ..., "design": ..., "brand": ...}; everything else keeps its value.

Useful for: brand-locked channels (always ink_teal), A/B tests, or appending a
disclaimer card to every video.
"""


def run(payload):
    design = dict(payload["design"])

    # pin the palette and layout, let the rest stay varied
    design["theme"] = "ink_teal"
    design["layout"] = "editorial"

    script = payload["script"]

    # examples of things a hook can do cheaply:
    # 1. normalise the kickers so every card starts with the same casing
    for scene in script.get("scenes", []):
        if scene.get("kicker"):
            scene["kicker"] = scene["kicker"][:1].upper() + scene["kicker"][1:]

    # 2. append a legal/contact card before the CTA (uncomment to use)
    # scenes = script.get("scenes", [])
    # if scenes and scenes[-1].get("kind") == "cta":
    #     scenes.insert(-1, {"kind": "fact", "kicker": "Contact", "big": "Questions?\nAsk us",
    #                        "body": "Write to us and we answer within one working day.",
    #                        "chip": "one working day"})

    return {"design": design, "script": script}
