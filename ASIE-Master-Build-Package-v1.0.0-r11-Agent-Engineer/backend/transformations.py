from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.contracts import json_dumps, new_id, now_iso


TRANSFORMATION_TYPES = {
    "select_column",
    "aggregate_average",
    "aggregate_sum",
    "filter",
    "remove_outliers",
    "normalize",
    "manual_derivation_note",
}
TRANSFORMATION_STATES = {"draft", "review_required", "approved", "rejected"}


def normalize_transformation_payload(
    dataset: dict[str, Any],
    payload: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operation_type = str(payload.get("operation_type") or (existing or {}).get("operation_type") or "manual_derivation_note")
    if operation_type not in TRANSFORMATION_TYPES:
        raise ValueError("invalid_transformation_operation")
    review_status = str(payload.get("review_status") or (existing or {}).get("review_status") or "review_required")
    if review_status not in TRANSFORMATION_STATES:
        raise ValueError("invalid_transformation_review_status")

    input_columns = _string_list(payload.get("input_columns") or (existing or {}).get("input_columns") or [])
    dataset_columns = set(dataset.get("columns") or [])
    missing_columns = [column for column in input_columns if column not in dataset_columns]
    if missing_columns:
        raise ValueError("transformation_input_column_not_found:" + ",".join(missing_columns))

    filters = payload.get("filters") or (existing or {}).get("filters") or {}
    output = _derive_output(dataset, operation_type, input_columns, payload)
    now = now_iso()
    return {
        "transformation_id": str(
            payload.get("transformation_id") or (existing or {}).get("transformation_id") or new_id("transform")
        ),
        "dataset_id": dataset["dataset_id"],
        "operation_type": operation_type,
        "operation_label": str(
            payload.get("operation_label")
            or (existing or {}).get("operation_label")
            or operation_type.replace("_", " ")
        ),
        "input_columns_json": json_dumps(input_columns),
        "filters_json": json_dumps(filters),
        "aggregation_method": str(payload.get("aggregation_method") or (existing or {}).get("aggregation_method") or operation_type),
        "output_value": output["output_value"],
        "output_unit": str(payload.get("output_unit") or (existing or {}).get("output_unit") or ""),
        "review_status": review_status,
        "review_notes": str(payload.get("review_notes") or (existing or {}).get("review_notes") or ""),
        "lineage_json": json_dumps(
            {
                "steps": _lineage_steps(dataset, operation_type, input_columns, filters, output),
                "source_dataset_id": dataset["dataset_id"],
                "source_profile_ref": f"dataset:{dataset['dataset_id']}:profile",
                "quality_review": transformation_quality_review(
                    {
                        "operation_type": operation_type,
                        "input_columns": input_columns,
                        "output_value": output["output_value"],
                        "review_status": review_status,
                    },
                    dataset,
                ),
                "external_fetch_enabled": False,
            }
        ),
        "created_at": str((existing or {}).get("created_at") or now),
        "updated_at": now,
    }


def build_transformation_lineage(
    evidence_ledger: list[dict[str, Any]],
    transformations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {row["transformation_id"]: row for row in transformations}
    lineage = []
    for ledger in evidence_ledger:
        transformation_id = ledger.get("transformation_id") or ""
        if not transformation_id:
            continue
        transformation = by_id.get(transformation_id, {})
        lineage.append(
            {
                "lineage_id": f"lineage_{ledger.get('evidence_link_id')}",
                "snapshot_id": ledger.get("snapshot_id"),
                "run_id": ledger.get("run_id"),
                "ledger_id": ledger.get("ledger_id"),
                "dataset_id": ledger.get("dataset_id"),
                "transformation_id": transformation_id,
                "target_type": ledger.get("target_type"),
                "target_id": ledger.get("target_id"),
                "operation_type": transformation.get("operation_type", ledger.get("transformation_operation", "")),
                "review_status": transformation.get("review_status", ledger.get("transformation_status", "")),
                "quality_review": transformation.get("lineage", {}).get("quality_review", {}),
                "review_notes": transformation.get("review_notes", ""),
                "output_value": transformation.get("output_value", ledger.get("transformation_output_value")),
                "output_unit": transformation.get("output_unit", ledger.get("transformation_output_unit", "")),
                "steps": transformation.get("lineage", {}).get("steps", []),
                "external_fetch_enabled": False,
            }
        )
    return lineage


def transformation_quality_review(transformation: dict[str, Any], dataset: dict[str, Any] | None = None) -> dict[str, Any]:
    operation_type = str(transformation.get("operation_type") or "")
    input_columns = _string_list(transformation.get("input_columns") or [])
    output_value = transformation.get("output_value")
    review_status = str(transformation.get("review_status") or "")
    reasons: list[str] = []
    warning_reasons: list[str] = []
    if review_status == "rejected":
        reasons.append("transformation_rejected_by_reviewer")
    elif review_status != "approved":
        warning_reasons.append("transformation_not_approved")
    if operation_type not in TRANSFORMATION_TYPES:
        reasons.append("invalid_operation_type")
    if operation_type != "manual_derivation_note" and not input_columns:
        reasons.append("missing_input_columns")
    if operation_type in {"aggregate_average", "aggregate_sum"} and output_value in {None, ""}:
        reasons.append("missing_derived_output_value")
    dataset_columns = set((dataset or {}).get("columns") or [])
    if dataset_columns:
        missing = [column for column in input_columns if column not in dataset_columns]
        if missing:
            reasons.append("input_column_not_found:" + ",".join(missing))
    status = "rejected" if reasons else "warning" if warning_reasons else "passed"
    return {
        "status": status,
        "reasons": reasons + warning_reasons,
        "operation_type": operation_type,
        "input_columns": input_columns,
        "review_status": review_status,
    }


def _derive_output(dataset: dict[str, Any], operation_type: str, input_columns: list[str], payload: dict[str, Any]) -> dict[str, str | None]:
    explicit = payload.get("output_value")
    if explicit not in {None, ""}:
        return {"output_value": str(explicit)}
    if operation_type not in {"aggregate_average", "aggregate_sum"} or not input_columns:
        return {"output_value": None}
    profile = (dataset.get("notes") or {}).get("profile") or {}
    first_profile = profile.get(input_columns[0]) or {}
    mean_value = first_profile.get("mean")
    non_null_count = first_profile.get("non_null_count")
    if mean_value is None:
        return {"output_value": None}
    if operation_type == "aggregate_average":
        return {"output_value": str(_round_decimal(mean_value))}
    if non_null_count is None:
        return {"output_value": None}
    return {"output_value": str(_round_decimal(Decimal(str(mean_value)) * Decimal(str(non_null_count))))}


def _lineage_steps(
    dataset: dict[str, Any],
    operation_type: str,
    input_columns: list[str],
    filters: Any,
    output: dict[str, str | None],
) -> list[dict[str, Any]]:
    steps = [
        {
            "step_id": "dataset_profile",
            "operation": "read_dataset_profile",
            "dataset_id": dataset["dataset_id"],
            "row_count": dataset.get("row_count", 0),
            "columns": input_columns or dataset.get("columns", []),
        }
    ]
    if filters:
        steps.append({"step_id": "filters", "operation": "apply_declared_filters", "filters": filters})
    steps.append(
        {
            "step_id": "derive_value",
            "operation": operation_type,
            "input_columns": input_columns,
            "output_value": output["output_value"],
        }
    )
    return steps


def _round_decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []
