from cp1_core.paths import ARTIFACTS_DIR, CP1_ROOT, PROJECT_ROOT


def test_paths_are_resolved_from_module_location():
    assert CP1_ROOT.name == "cp1"
    assert PROJECT_ROOT.name in {"NCKH", "NCKH_Aleart-fatigue", "Resource"}
    assert ARTIFACTS_DIR == CP1_ROOT / "artifacts"
