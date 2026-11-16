"""Browser regression tests for the standalone Signature Motion Lab."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
PARAMS = {
    "flow": 89, "struct": 24, "micro": 70, "ab": 94,
    "sp": 79, "fl": 35, "sm": 94, "bw": 1.15, "pr": 4,
    "dash": 42, "loops": {"g": False, "d": False, "l": False},
    "seed": 0,
}
NAMES = ["Alan Wake", "Margie Golding", "McDonald", "Jodie d'Angelo",
         "Miguel Iga", "A", "gdl", "iJ"]

with sync_playwright() as p:
    import shutil
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    browser = p.chromium.launch(headless=True, executable_path=executable if executable else None, args=["--no-sandbox"])
    page = browser.new_page(accept_downloads=True)
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.set_content(HTML, wait_until="load")
    assert page.locator("#sig-view svg").count() == 1
    for name in NAMES:
        result = page.evaluate("""([name, options]) => {
            let a = window.SignatureMotionLabV5.generate(name, options);
            let b = window.SignatureMotionLabV5.generate(name, options);
            let paths = a.strokes.filter(x => x.type === 'stroke');
            return {
                stable: JSON.stringify(a) === JSON.stringify(b),
                finite: paths.every(s => s.points.every(p => Number.isFinite(p.x) && Number.isFinite(p.y))),
                endGap: a.terminal && a.tailJoin ? Math.hypot(a.terminal.x-a.tailJoin.x, a.terminal.y-a.tailJoin.y) : null
            };
        }""", [name, PARAMS])
        assert result["stable"], f"Non-deterministic output: {name}"
        assert result["finite"], f"Non-finite geometry: {name}"
        assert result["endGap"] is None or result["endGap"] < 1e-9, f"Disconnected tail: {name}"
    page.locator("#sig-name").fill("Margie Golding")
    assert page.locator("#sig-nameprint").inner_text() == "Margie Golding"
    page.locator("#sig-again").click()
    assert page.locator("#sig-seed").inner_text().strip() == "S001"
    page.locator("#sig-reset").click()
    assert page.locator("#sig-seed").inner_text().strip() == "S000"
    with page.expect_download() as dl:
        page.locator("#sig-save").click()
    assert dl.value.suggested_filename.lower().endswith(".svg")
    assert not errors, errors
    browser.close()
print(f"PASS: {len(NAMES)} signature geometry samples, UI controls, SVG export")
