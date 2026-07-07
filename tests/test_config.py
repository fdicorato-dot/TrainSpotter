import trainspotter.config as cfg

def test_listen_parameter_vollstaendig():
    for d in (cfg.MISSED_TRAIN_PCT, cfg.STOP_PCT, cfg.TARGET1_PCT):
        assert set(d) == set(cfg.LISTEN)

def test_kernwerte():
    assert cfg.STOP_PCT["konservativ"] == 3.0
    assert cfg.TARGET1_PCT["spekulativ"] == 10.0
    assert cfg.SLIPPAGE_PCT == 0.2
