import glob, yaml


def test_alle_workflows_valides_yaml_mit_jobs():
    files = glob.glob(".github/workflows/*.yml")
    assert len(files) == 6
    for f in files:
        d = yaml.safe_load(open(f))
        assert "jobs" in d, f
