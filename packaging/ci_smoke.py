"""Smoke test for CI: compose a page from a blank script and check the timeline.

No browser, no ffmpeg, no network — it only proves the composer and the design
system still produce a sane, non-empty composition.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelforge import ai, compose, paths, themes  # noqa: E402


def main() -> int:
    paths.ensure_home()
    brand = {"name": "CI", "latin": "CI", "site": "ci.test", "logo": "", "cta_title": "Read more",
             "cta_body": "One sentence.", "cta_chip": "Open", "footer_cta": "Follow"}
    script = ai.blank_script(brand)
    ok = 0
    for theme, layout, bg in (("navy_gold", "editorial", "gradient"),
                              ("ink_teal", "center", "gradient"),
                              ("wine_sand", "index", "photo"),
                              ("forest_cream", "rail", "duotone")):
        design = {"theme": theme, "layout": layout, "background": bg, "transition": "wipe",
                  "frame": "brackets", "brand": "header", "format": "9:16"}
        info = compose.compose(script, design, brand,
                               project_dir=paths.projects_dir() / f"ci-{theme}", seed=f"ci-{theme}",
                               assets={"broll": [], "music": [], "sfx": {}, "photos": []})
        assert info["total"] > 4, info
        assert len(info["scenes"]) == len(script["scenes"]), info
        page = (paths.projects_dir() / f"ci-{theme}" / "index.html").read_text(encoding="utf-8")
        assert "gsap.timeline" in page and page.count('class="scene') >= 3, page[:200]
        ok += 1
    # the design picker must always return a complete, valid design
    for i in range(12):
        d = themes.pick(f"seed-{i}")
        assert set(d) >= set(themes.AUTO_KEYS), d
        assert d["theme"] in themes.all_themes(), d
    print(f"ok — {ok} compositions, design picker stable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
