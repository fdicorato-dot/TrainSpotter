import importlib
dry = importlib.import_module("scripts.run_dry_run")

def test_trockenlauf_kompletter_tag():
    r = dry.run("tests/fixtures/recorded_day.json")
    assert r["alerts"] == 1        # Zyklus 2 loest aus (Ausbruch + Volumen)
    assert r["open_end"] == 0      # spekulativ -> zum Schluss zwangsgeschlossen
    assert r["closed"] >= 1
