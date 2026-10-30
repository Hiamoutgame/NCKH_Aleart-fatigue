"""HTTP client interface for Kev System One inference server."""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional, Sequence

import httpx
import numpy as np

DEFAULT_INSTRUCTIONS = "Which service is the most likely root cause of this incident?"


class KevClient:
    """Client communicating with a running Kev decision serving endpoint over HTTP."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8009",
        timeout: float = 120.0,
        api_key: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or os.environ.get("KEV_API_KEY")
        self.transport = transport
        self._model_name: Optional[str] = None

    def _build_client(self) -> httpx.Client:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers,
            transport=self.transport,
        )

    @property
    def model_name(self) -> str:
        if self._model_name is not None:
            return self._model_name
        try:
            with self._build_client() as client:
                response = client.get("/v1/models")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    if models and isinstance(models[0], dict):
                        self._model_name = models[0].get("id", "kev-latest")
                    else:
                        self._model_name = "kev-latest"
                else:
                    self._model_name = "kev-latest"
        except Exception:
            self._model_name = "kev-latest"
        return self._model_name

    def choice(
        self,
        state: str,
        options: Sequence[str],
        instructions: str = DEFAULT_INSTRUCTIONS,
    ) -> dict[str, float]:
        """Submit a single choice question and return normalized posterior probabilities."""
        sorted_options = sorted(options)
        payload = {
            "state": state,
            "model": "kev-latest",
            "questions": {
                "root_cause": {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": {opt: None for opt in sorted_options},
                }
            },
        }

        with self._build_client() as client:
            response = client.post("/v1/systemone", json=payload)
            if response.status_code == 422:
                raise ValueError(
                    f"Kev rejected request with 422 (context length overflow or invalid input): {response.text}"
                )
            response.raise_for_status()
            data = response.json()

        answers = data.get("answers", {}).get("root_cause", {})
        probabilities = answers.get("probabilities", {})

        if set(probabilities.keys()) != set(sorted_options):
            raise ValueError(
                f"Returned option keys do not match expected candidates. "
                f"Expected: {sorted_options}, Got: {list(probabilities.keys())}"
            )

        prob_sum = sum(probabilities.values())
        if not np.isclose(prob_sum, 1.0, atol=1e-2):
            raise ValueError(f"Probabilities do not sum to ~1.0: sum={prob_sum:.4f}")

        return {k: float(v) for k, v in probabilities.items()}

    def permute(
        self,
        state: str,
        options: Sequence[str],
        instructions: str = DEFAULT_INSTRUCTIONS,
        n_perm: int = 6,
        seed: int = 0,
    ) -> dict[str, float]:
        """Submit choice question with n_perm option orderings to cancel position bias."""
        sorted_options = sorted(options)
        payload = {
            "request": {
                "state": state,
                "model": "kev-latest",
                "questions": {
                    "root_cause": {
                        "type": "choice",
                        "instructions": instructions,
                        "criteria": {opt: None for opt in sorted_options},
                    }
                },
            },
            "question": "root_cause",
            "n_perm": n_perm,
            "seed": seed,
        }

        with self._build_client() as client:
            response = client.post("/v1/systemone/permute", json=payload)
            if response.status_code == 422:
                raise ValueError(f"Kev permute rejected request with 422: {response.text}")
            response.raise_for_status()
            data = response.json()

        runs = data.get("runs", [])
        if not runs:
            raise ValueError("Empty permutation runs returned by Kev server")

        aggregated_probs = {opt: 0.0 for opt in sorted_options}
        for run in runs:
            run_probs = run.get("probabilities", {})
            for opt in sorted_options:
                aggregated_probs[opt] += float(run_probs.get(opt, 0.0))

        total_runs = float(len(runs))
        normalized_probs = {opt: val / total_runs for opt, val in aggregated_probs.items()}
        return normalized_probs
