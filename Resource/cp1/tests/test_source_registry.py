from cp1_core.source_registry import get_source, load_sources


def test_registry_contains_all_chosen_sources():
    sources = load_sources()
    assert {"rcaeval", "lemma_rca", "loghub2", "opseval", "correlated_alerts", "suricata_ctu13"} <= sources.keys()
    assert get_source("rcaeval_github").type == "github_repository"
