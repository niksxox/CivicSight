from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

import pandas as pd


@dataclass
class EtlReport:
    dataset: str
    source_file: str
    input_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    loaded_rows: int = 0
    warnings: list[str] = field(default_factory=list)
    rejected_path: str | None = None
    started_at: float = field(default_factory=perf_counter)
    elapsed_seconds: float = 0.0

    def finish(self) -> "EtlReport":
        self.elapsed_seconds = round(perf_counter() - self.started_at, 2)
        return self

    def as_lines(self) -> list[str]:
        lines = [
            f"Dataset: {self.dataset}",
            f"Source file: {self.source_file}",
            f"Input rows: {self.input_rows}",
            f"Valid rows: {self.valid_rows}",
            f"Rejected rows: {self.rejected_rows}",
            f"Loaded rows: {self.loaded_rows}",
            f"Execution time: {self.elapsed_seconds:.2f}s",
        ]
        if self.rejected_path:
            lines.append(f"Rejected rows file: {self.rejected_path}")
        for warning in self.warnings:
            lines.append(f"Warning: {warning}")
        return lines


def write_rejections(rejected: pd.DataFrame, output_dir: Path, dataset: str) -> str | None:
    if rejected.empty:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"rejected_{dataset}.csv"
    rejected.to_csv(path, index=False)
    return str(path)
