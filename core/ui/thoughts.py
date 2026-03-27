from __future__ import annotations

import json
import queue
import sys
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import time
from typing import Any


@dataclass
class ThoughtEvent:
    phase: str
    message: str
    kind: str = "info"  # info, warn, success, fail
    confidence: float | None = None
    file_path: str | None = None
    line_no: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ThoughtSink:
    def emit(self, event: ThoughtEvent) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class NullThoughtSink(ThoughtSink):
    def emit(self, event: ThoughtEvent) -> None:
        return


class JsonlThoughtSink(ThoughtSink):
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def emit(self, event: ThoughtEvent) -> None:
        self._fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass


class MultiThoughtSink(ThoughtSink):
    def __init__(self, sinks: list[ThoughtSink]):
        self.sinks = [s for s in sinks if s is not None]

    def emit(self, event: ThoughtEvent) -> None:
        for sink in self.sinks:
            try:
                sink.emit(event)
            except Exception:
                continue

    def close(self) -> None:
        for sink in self.sinks:
            try:
                sink.close()
            except Exception:
                continue


class AsyncThoughtBus:
    def __init__(self, sink: ThoughtSink):
        self.sink = sink
        self.q: queue.Queue[ThoughtEvent | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def emit(self, event: ThoughtEvent) -> None:
        self.q.put(event)

    def _run(self) -> None:
        while True:
            item = self.q.get()
            if item is None:
                break
            try:
                self.sink.emit(item)
            except Exception:
                continue

    def close(self) -> None:
        self.q.put(None)
        self._thread.join(timeout=1.5)
        try:
            self.sink.close()
        except Exception:
            pass


def build_thought_sink(
    enable_live: bool = False,
    enable_tree: bool = False,
    jsonl_path: str | None = None,
) -> ThoughtSink | None:
    sinks: list[ThoughtSink] = []

    if enable_tree:
        try:
            from core.ui.rich_sink import RichTreeThoughtSink
            sinks.append(RichTreeThoughtSink())
        except Exception as exc:
            print(f"[termorganism] --think-tree disabled: {exc}", file=sys.stderr)
    elif enable_live:
        try:
            from core.ui.rich_sink import RichLiveThoughtSink
            sinks.append(RichLiveThoughtSink())
        except Exception as exc:
            print(f"[termorganism] --think disabled: {exc}", file=sys.stderr)

    if jsonl_path:
        sinks.append(JsonlThoughtSink(jsonl_path))

    if not sinks:
        return None
    if len(sinks) == 1:
        return sinks[0]
    return MultiThoughtSink(sinks)
