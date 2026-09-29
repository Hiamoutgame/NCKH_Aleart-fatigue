from cp1_core.analysis import classify_case_id, is_normal_window


def test_classify_case_id_for_all_rcaeval_systems():
    assert classify_case_id("re2ob_checkoutservice_cpu_1")["sys"] == "RE2-OB"
    assert classify_case_id("re2ss_carts_cpu_1")["sys"] == "RE2-SS"
    assert classify_case_id("re3tt_ts-route-service_mem_1")["sys"] == "RE3-TT"


def test_unknown_case_id_is_explicit():
    assert classify_case_id("not-a-case")["system"] == "OTHER"


def test_injection_boundary_starts_faulty_window():
    assert is_normal_window(99, 100)
    assert not is_normal_window(100, 100)
