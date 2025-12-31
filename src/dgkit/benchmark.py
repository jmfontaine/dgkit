import time
from dataclasses import dataclass, field
from typing import Self


@dataclass
class Summary:
    elapsed_seconds: float
    records_read: int
    records_dropped: int
    records_modified: int
    records_written: int
    records_unhandled: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def records_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return 0
        return self.records_read / self.elapsed_seconds

    def display(self) -> str:
        lines = [
            f"Read:      {self.records_read:,}",
            f"Dropped:   {self.records_dropped:,}",
            f"Modified:  {self.records_modified:,}",
            f"Written:   {self.records_written:,}",
        ]
        if self.records_unhandled > 0:
            lines.append(f"Unhandled: {self.records_unhandled:,}")
        lines.append(
            f"Time:      {self.elapsed_seconds:.2f}s ({self.records_per_second:,.0f} records/sec)"
        )
        return "\n".join(lines)


@dataclass
class SummaryCollector:
    _start_time: float = field(default=0, init=False)
    _records_read: int = field(default=0, init=False)
    _records_dropped: int = field(default=0, init=False)
    _records_modified: int = field(default=0, init=False)
    _records_written: int = field(default=0, init=False)
    _records_unhandled: int = field(default=0, init=False)
    _warnings: list[str] = field(default_factory=list, init=False)

    def __enter__(self) -> Self:
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def record_read(self) -> None:
        self._records_read += 1

    def record_dropped(self) -> None:
        self._records_dropped += 1

    def record_modified(self) -> None:
        self._records_modified += 1

    def record_written(self) -> None:
        self._records_written += 1

    def record_unhandled(self, message: str) -> None:
        self._records_unhandled += 1
        self._warnings.append(message)

    @property
    def warnings(self) -> list[str]:
        return self._warnings

    def result(self) -> Summary:
        elapsed = time.perf_counter() - self._start_time
        return Summary(
            elapsed_seconds=elapsed,
            records_read=self._records_read,
            records_dropped=self._records_dropped,
            records_modified=self._records_modified,
            records_written=self._records_written,
            records_unhandled=self._records_unhandled,
            warnings=self._warnings,
        )
