"""Export fine-tuning JSONL datasets formatted for Kev training."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import pandas as pd

from src.evaluation.split import load_splits
from src.integrations.kev.client import DEFAULT_INSTRUCTIONS
from src.ranking.candidates import load_candidates
from src.shared.infrastructure.manifest import sha256_file
from src.shared.infrastructure.paths import DATA_DIR, NORMALIZED_DIR
from src.views import (
    IncidentView,
    StateConfig,
    render_state,
    view_from_dict,
)


def export_jsonl(
    dataset_slug: str,
    split_purpose: str,
    output_directory: Path | str,
    grouping_method: str = "g2",
    instructions: str = DEFAULT_INSTRUCTIONS,
    state_config: Optional[StateConfig] = None,
) -> tuple[Path, Path]:
    """Export fine-tuning records for train or val partition in Kev decision JSONL format.

    Raises:
        ValueError: If split_purpose is 'test' or 'external_test' to prevent data contamination.
    """
    normalized_split = split_purpose.lower().strip()
    if normalized_split in ("test", "external_test"):
        raise ValueError(
            f"Exporting '{normalized_split}' to Kev JSONL training data is strictly prohibited."
        )

    target_dir = Path(output_directory)
    target_dir.mkdir(parents=True, exist_ok=True)

    views_file = DATA_DIR / "artifacts" / dataset_slug / f"views_{grouping_method}.jsonl"
    if not views_file.exists():
        raise FileNotFoundError(f"Views file not found at {views_file}. Run views first.")

    candidates_file = DATA_DIR / "artifacts" / dataset_slug / "candidates.json"
    if not candidates_file.exists():
        raise FileNotFoundError(f"Candidates file not found at {candidates_file}. Run candidates first.")

    candidates_inventory = load_candidates(candidates_file)
    splits_frame = load_splits(NORMALIZED_DIR / dataset_slug)
    split_incident_ids = set(
        splits_frame[splits_frame["split_purpose"] == normalized_split]["incident_id"]
    )

    gt_path = NORMALIZED_DIR / dataset_slug / "ground_truth.parquet"
    gt_frame = pd.read_parquet(gt_path)
    gt_map = dict(zip(gt_frame["incident_id"], gt_frame["canonical_target"]))

    rendered_config = state_config or StateConfig()
    output_jsonl_path = target_dir / f"{normalized_split}.jsonl"
    manifest_path = target_dir / f"export_{normalized_split}_manifest.json"

    exported_record_count = 0
    skipped_unobserved_target_count = 0

    with views_file.open("r", encoding="utf-8") as in_handle, output_jsonl_path.open("w", encoding="utf-8") as out_handle:
        for line in in_handle:
            if not line.strip():
                continue
            view_payload = json.loads(line)
            incident_id = view_payload["incident_id"]
            if incident_id not in split_incident_ids:
                continue

            view = view_from_dict(view_payload)
            target_service = gt_map.get(incident_id)
            candidates = candidates_inventory.get(view.system_id, [])

            if not target_service or target_service not in candidates:
                # Target absent from candidate inventory
                skipped_unobserved_target_count += 1
                continue

            rendered = render_state(view, candidates, rendered_config)
            record_payload = {
                "state": rendered.state_text,
                "questions": {
                    "root_cause": {
                        "type": "choice",
                        "instructions": instructions,
                        "criteria": {cand: None for cand in sorted(candidates)},
                        "label": target_service,
                    }
                },
            }
            out_handle.write(json.dumps(record_payload, ensure_ascii=False) + "\n")
            exported_record_count += 1

    manifest_payload: dict[str, Any] = {
        "dataset_slug": dataset_slug,
        "split_purpose": normalized_split,
        "grouping_method": grouping_method,
        "total_incidents_in_split": len(split_incident_ids),
        "exported_records": exported_record_count,
        "skipped_unobserved_targets": skipped_unobserved_target_count,
        "sha256": sha256_file(output_jsonl_path),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n")

    return output_jsonl_path, manifest_path
