"""EXAMPLE — build the script yourself, without any AI.

Copy this file to `<home>/hooks/before_script.py` (the Extend tab can do it) and
Reelforge stops calling the model: whatever you return is what gets rendered.

`payload` looks like:
    {
      "stage": "before_script",
      "project": "<id>",
      "article": {"title": ..., "text": ..., "blocks": [...], "url": ...},
      "config":  {"brand": {...}, "assets": "...", "out": "..."}
    }

Return {"script": {...}} — or {} to let the normal pipeline continue.
"""


def run(payload):
    article = payload["article"]
    # keep the first sentence of every paragraph that mentions a number
    facts = [b["text"] for b in article.get("blocks", [])
             if b["type"] == "p" and any(ch.isdigit() for ch in b["text"])][:3]
    if not facts:
        return {}

    scenes = [{
        "kind": "fact",
        "kicker": "From the article",
        "big": split_headline(article.get("title", "Untitled")),
        "body": facts[0][:180],
        "chip": "1 of 3",
    }]
    for i, fact in enumerate(facts[1:], start=2):
        scenes.append({
            "kind": "fact",
            "kicker": f"Point {i}",
            "big": split_headline("What the numbers say"),
            "body": fact[:180],
            "chip": "the detail",
        })
    scenes.append({
        "kind": "cta",
        "kicker": payload["config"]["brand"]["brand_name"],
        "big": "Read the full\\nguide",
        "body": payload["config"]["brand"]["brand_cta_body"] or "Everything in one place.",
        "chip": payload["config"]["brand"]["brand_cta_chip"] or "Open",
    })
    return {"script": {"title": article.get("title", "")[:90], "scenes": scenes}}


def split_headline(text, max_words=7):
    """The design wants two short lines; the renderer also fixes this, but start clean."""
    words = str(text).split()[:max_words]
    if len(words) <= 3:
        return " ".join(words)
    cut = (len(words) + 1) // 2
    return " ".join(words[:cut]) + "\n" + " ".join(words[cut:])
