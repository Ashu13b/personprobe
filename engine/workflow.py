"""Explicit, monotonic research workflow stages."""

from __future__ import annotations

from typing import Literal

from .models import Source

SOURCE_STAGE = Literal[
    "discovered", "retrieved", "identity_checked", "provenance_checked"
]
SOURCE_STAGE_ORDER: tuple[SOURCE_STAGE, ...] = (
    "discovered",
    "retrieved",
    "identity_checked",
    "provenance_checked",
)


def advance_source_stage(source: Source, stage: SOURCE_STAGE) -> bool:
    """Advance a source only after the corresponding gate has passed."""
    current_index = SOURCE_STAGE_ORDER.index(source.workflow_stage)
    target_index = SOURCE_STAGE_ORDER.index(stage)
    if target_index <= current_index:
        return False
    if target_index != current_index + 1:
        return False
    source.workflow_stage = stage
    return True
