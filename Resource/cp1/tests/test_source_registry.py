from cp1_core.source_registry import get_source, load_sources


def test_registry_contains_all_chosen_sources():
    sources = load_sources()
    assert set(sources) == {"rcaeval", "lemma_rca", "nezha", "rcaeval_github"}
    assert get_source("rcaeval_github").type == "github_repository"


def test_registry_paths_match_adapter_inputs():
    from src.shared.infrastructure.paths import DATASET_PATHS

    for slug, path in DATASET_PATHS.items():
        assert get_source(slug).local_path == path
