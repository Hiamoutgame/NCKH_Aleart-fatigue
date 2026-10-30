"""Unit tests for KevClient, KevRanker, and fine-tuning export using httpx.MockTransport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from src.integrations.kev import (
    KevClient,
    KevRanker,
    export_jsonl,
)
from src.views import IncidentView, ServiceView


def test_kev_client_choice_success():
    """Verify KevClient correctly parses valid posterior probabilities."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/systemone"
        data = json.loads(request.content)
        criteria = data["questions"]["root_cause"]["criteria"]
        assert set(criteria.keys()) == {"adservice", "cartservice"}
        return httpx.Response(
            200,
            json={
                "answers": {
                    "root_cause": {
                        "choice": "cartservice",
                        "probabilities": {"adservice": 0.2, "cartservice": 0.8},
                    }
                }
            },
        )

    transport = httpx.MockTransport(mock_handler)
    client = KevClient(base_url="http://mock-kev:8009", transport=transport)
    probs = client.choice("state text", ["cartservice", "adservice"])
    assert probs == {"adservice": 0.2, "cartservice": 0.8}


def test_kev_client_raises_on_option_mismatch_or_invalid_sum():
    """Verify KevClient raises ValueError if options mismatch or probabilities don't sum to 1."""
    # 1. Option mismatch
    transport_mismatch = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={
                "answers": {
                    "root_cause": {
                        "probabilities": {"cartservice": 1.0},  # missing adservice
                    }
                }
            },
        )
    )
    client_mismatch = KevClient(transport=transport_mismatch)
    with pytest.raises(ValueError, match="Returned option keys do not match"):
        client_mismatch.choice("state", ["cartservice", "adservice"])

    # 2. Invalid probability sum
    transport_bad_sum = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={
                "answers": {
                    "root_cause": {
                        "probabilities": {"cartservice": 0.2, "adservice": 0.2},  # sum = 0.4 != 1.0
                    }
                }
            },
        )
    )
    client_bad_sum = KevClient(transport=transport_bad_sum)
    with pytest.raises(ValueError, match="Probabilities do not sum to ~1.0"):
        client_bad_sum.choice("state", ["cartservice", "adservice"])


def test_kev_client_raises_on_http_422():
    """Verify KevClient detects and reports context length 422 error without silently truncating."""
    transport_422 = httpx.MockTransport(
        lambda req: httpx.Response(422, text="state token count 70,000 exceeds limit 65,536")
    )
    client = KevClient(transport=transport_422)
    with pytest.raises(ValueError, match="Kev rejected request with 422"):
        client.choice("oversize state", ["cartservice"])


def test_kev_ranker_ranking():
    """Verify KevRanker converts Kev probabilities into ranked service objects."""
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={
                "answers": {
                    "root_cause": {
                        "probabilities": {"adservice": 0.1, "cartservice": 0.9},
                    }
                }
            },
        )
    )
    client = KevClient(transport=transport)
    ranker = KevRanker(client=client, name="kev-test")

    view = IncidentView(
        incident_id="inc1", system_id="ob", method="g2",
        before_seconds=100.0, after_seconds=100.0,
        services=(
            ServiceView("cartservice", 0, 10, 5, 0, 0, 1, ()),
            ServiceView("adservice", 0, 5, 0, 0, 0, 1, ()),
        ),
    )
    ranked = ranker.rank(view, ["adservice", "cartservice"])
    assert len(ranked) == 2
    assert ranked[0].service_id == "cartservice"
    assert ranked[0].score == 0.9
    assert ranked[0].rank == 1
    assert ranked[1].service_id == "adservice"
    assert ranked[1].rank == 2


def test_export_jsonl_refuses_test_split(tmp_path: Path):
    """Verify export_jsonl strictly refuses test and external_test splits."""
    with pytest.raises(ValueError, match="strictly prohibited"):
        export_jsonl(dataset_slug="rcaeval", split_purpose="test", output_directory=tmp_path)

    with pytest.raises(ValueError, match="strictly prohibited"):
        export_jsonl(dataset_slug="rcaeval", split_purpose="external_test", output_directory=tmp_path)
