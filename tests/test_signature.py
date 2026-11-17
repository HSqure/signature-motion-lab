"""Browser regression tests for the standalone Signature Motion Lab v0.8.0."""
import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
PRESETS = json.loads((ROOT / "assets/sample-grid-v080.json").read_text(encoding="utf-8"))

with sync_playwright() as p:
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    browser = p.chromium.launch(headless=True, executable_path=executable or None, args=["--no-sandbox"])
    page = browser.new_page(accept_downloads=True)
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.set_content(HTML, wait_until="load")
    assert page.locator("#sig-view svg").count() == 1
    assert len(PRESETS) == 10 and len({x["seed"] for x in PRESETS}) == 10
    for preset in PRESETS:
        name = preset["name"]
        result = page.evaluate("""options => {
            const api = window.SignatureMotionLabV080;
            const a = api.render(options.name, options);
            const b = api.render(options.name, options);
            const points = a.strokes.flatMap(s => s.type === 'stroke' ? s.points :
              s.type === 'dash' ? [{x:s.x,y:s.y},{x:s.x+s.dx,y:s.y+s.dy}] : [{x:s.x,y:s.y}]);
            return {
                stable: a.svg === b.svg,
                finite: points.length > 0 && points.every(p => Number.isFinite(p.x) && Number.isFinite(p.y)),
                endGap: a.terminal && a.tailJoin ? Math.hypot(a.terminal.x-a.tailJoin.x, a.terminal.y-a.tailJoin.y) : null
            };
        }""", preset)
        assert result["stable"], f"Non-deterministic output: {name}"
        assert result["finite"], f"Non-finite geometry: {name}"
        assert result["endGap"] is None or result["endGap"] < 1e-9, f"Disconnected tail: {name}"
    page.locator("#sig-name").fill("Jesse Faden")
    assert page.locator("#sig-nameprint").inner_text() == "Jesse Faden"
    page.locator("#sig-again").click()
    assert page.locator("#sig-seed").inner_text().strip() == "S001"
    page.locator("#sig-drive").fill("0")
    page.locator("#sig-ystretch").fill("160")
    page.locator("#sig-bowl").fill("140")
    options = page.evaluate("window.SignatureMotionLabV080.getOptions()")
    assert (options["drive"], options["xstretch"], options["ystretch"], options["bowl"]) == (0, 55, 160, 140)
    page.locator("#sig-tailorbit").check()
    assert page.locator("#sig-orbitcount").is_enabled()
    page.locator("#sig-reset").click()
    assert page.locator("#sig-seed").inner_text().strip() == "S000"
    assert page.locator("#sig-orbitcount").is_disabled()
    with page.expect_download() as dl:
        page.locator("#sig-save").click()
    assert dl.value.suggested_filename.lower().endswith(".svg")
    assert not errors, errors
    browser.close()
print(f"PASS: {len(PRESETS)} gallery presets, extreme geometry, UI controls, SVG export")
