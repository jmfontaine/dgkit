import time
from dataclasses import dataclass, field
from typing import Self


@dataclass
class Summary:
    elapsed_seconds: float
    record_count: int

    @property
    def records_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return 0
        return self.record_count / self.elapsed_seconds

    def display(self) -> str:
        return (
            f"Processed {self.record_count:,} records "
            f"in {self.elapsed_seconds:.2f}s "
            f"({self.records_per_second:,.0f} records/sec)"
        )


@dataclass
class SummaryCollector:
    _start_time: float = field(default=0, init=False)
    _record_count: int = field(default=0, init=False)

    def __enter__(self) -> Self:
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def count(self, n: int = 1) -> None:
        self._record_count += n

    def result(self) -> Summary:
        elapsed = time.perf_counter() - self._start_time
        return Summary(
            elapsed_seconds=elapsed,
            record_count=self._record_count,
        )
