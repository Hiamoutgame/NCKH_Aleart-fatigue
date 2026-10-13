from cp1_core.normalization import normalize_message
from cp1_core.severity import infer_severity, is_warning


def test_warning_parser_uses_word_boundaries():
    assert is_warning("WARN request failed")
    assert is_warning("WARNING request failed")
    assert not is_warning("prewarning text")


def test_severity_parser_reads_log4j_header():
    assert infer_severity("2024-01-01 10:00:00.000 WARN 1 --- [main] message") == "WARNING"
    assert infer_severity("ERROR connection refused") == "ERROR"


def test_normalization_removes_dynamic_values():
    first = normalize_message("2024-01-01 10:00:00.000 WARN 1 --- [main] request 123 failed")
    second = normalize_message("2024-01-01 10:00:01.000 WARN 1 --- [main] request 456 failed")
    assert first == second
    assert "<N>" in first
