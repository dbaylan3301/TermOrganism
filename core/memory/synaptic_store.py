from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .synaptic_types import SynapticEdge, SynapticEvent, SynapticNode


def _now() -> float:
    return time.time()


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


class SynapticStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".termorganism" / "synaptic.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    label TEXT NOT NULL DEFAULT '',
                    meta_json TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 0.5,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    seen_count INTEGER NOT NULL DEFAULT 0,
                    last_seen_ts REAL NOT NULL DEFAULT 0.0,
                    avg_confidence REAL NOT NULL DEFAULT 0.0,
                    meta_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY (source_id, target_id, kind)
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
                CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);
                CREATE INDEX IF NOT EXISTS idx_edges_last_seen ON edges(last_seen_ts DESC);
                CREATE INDEX IF NOT EXISTS idx_events_type_ts ON events(event_type, ts DESC);
                """
            )

    def upsert_node(self, node: SynapticNode) -> None:
        now = _now()
        with self._connect() as conn:
            existing = conn.execute("SELECT 1 FROM nodes WHERE id = ?", (node.id,)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE nodes
                    SET type = ?, label = ?, meta_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        node.type,
                        node.label,
                        json.dumps(node.meta, ensure_ascii=False),
                        now,
                        node.id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO nodes (id, type, label, meta_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node.id,
                        node.type,
                        node.label,
                        json.dumps(node.meta, ensure_ascii=False),
                        now,
                        now,
                    ),
                )

    def get_edge(self, source_id: str, target_id: str, kind: str) -> SynapticEdge | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT source_id, target_id, kind, weight, success_count, failure_count,
                       seen_count, last_seen_ts, avg_confidence, meta_json
                FROM edges
                WHERE source_id = ? AND target_id = ? AND kind = ?
                """,
                (source_id, target_id, kind),
            ).fetchone()
        if row is None:
            return None
        return SynapticEdge(
            source_id=row["source_id"],
            target_id=row["target_id"],
            kind=row["kind"],
            weight=float(row["weight"]),
            success_count=int(row["success_count"]),
            failure_count=int(row["failure_count"]),
            seen_count=int(row["seen_count"]),
            last_seen_ts=float(row["last_seen_ts"]),
            avg_confidence=float(row["avg_confidence"]),
            meta=json.loads(row["meta_json"] or "{}"),
        )

    def upsert_edge(self, edge: SynapticEdge) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO edges (
                    source_id, target_id, kind, weight, success_count, failure_count,
                    seen_count, last_seen_ts, avg_confidence, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, kind) DO UPDATE SET
                    weight = excluded.weight,
                    success_count = excluded.success_count,
                    failure_count = excluded.failure_count,
                    seen_count = excluded.seen_count,
                    last_seen_ts = excluded.last_seen_ts,
                    avg_confidence = excluded.avg_confidence,
                    meta_json = excluded.meta_json
                """,
                (
                    edge.source_id,
                    edge.target_id,
                    edge.kind,
                    _clamp(edge.weight),
                    edge.success_count,
                    edge.failure_count,
                    edge.seen_count,
                    edge.last_seen_ts,
                    _clamp(edge.avg_confidence),
                    json.dumps(edge.meta, ensure_ascii=False),
                ),
            )

    def adjust_edge(
        self,
        *,
        source_id: str,
        target_id: str,
        kind: str,
        delta: float,
        success: bool | None,
        confidence: float = 0.0,
        meta: dict[str, Any] | None = None,
    ) -> SynapticEdge:
        edge = self.get_edge(source_id, target_id, kind)
        if edge is None:
            edge = SynapticEdge(
                source_id=source_id,
                target_id=target_id,
                kind=kind,
                weight=0.50,
                meta=meta or {},
            )

        edge.seen_count += 1
        edge.last_seen_ts = _now()
        edge.weight = _clamp(edge.weight + delta)

        if success is True:
            edge.success_count += 1
        elif success is False:
            edge.failure_count += 1

        prev_seen = max(edge.seen_count - 1, 0)
        if edge.seen_count > 0:
            edge.avg_confidence = _clamp(
                ((edge.avg_confidence * prev_seen) + max(0.0, min(1.0, confidence))) / edge.seen_count
            )

        if meta:
            merged = dict(edge.meta)
            merged.update(meta)
            edge.meta = merged

        self.upsert_edge(edge)
        return edge

    def add_event(self, event: SynapticEvent) -> None:
        ts = event.ts or _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (ts, event_type, payload_json)
                VALUES (?, ?, ?)
                """,
                (ts, event.event_type, json.dumps(event.payload, ensure_ascii=False)),
            )

    def top_edges_for_source(self, source_id: str, kind: str, limit: int = 10) -> list[SynapticEdge]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT source_id, target_id, kind, weight, success_count, failure_count,
                       seen_count, last_seen_ts, avg_confidence, meta_json
                FROM edges
                WHERE source_id = ? AND kind = ?
                ORDER BY weight DESC, seen_count DESC, last_seen_ts DESC
                LIMIT ?
                """,
                (source_id, kind, limit),
            ).fetchall()

        out: list[SynapticEdge] = []
        for row in rows:
            out.append(
                SynapticEdge(
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    kind=row["kind"],
                    weight=float(row["weight"]),
                    success_count=int(row["success_count"]),
                    failure_count=int(row["failure_count"]),
                    seen_count=int(row["seen_count"]),
                    last_seen_ts=float(row["last_seen_ts"]),
                    avg_confidence=float(row["avg_confidence"]),
                    meta=json.loads(row["meta_json"] or "{}"),
                )
            )
        return out

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            node_count = conn.execute("SELECT COUNT(*) AS c FROM nodes").fetchone()["c"]
            edge_count = conn.execute("SELECT COUNT(*) AS c FROM edges").fetchone()["c"]
            event_count = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
        return {
            "db_path": str(self.db_path),
            "nodes": int(node_count),
            "edges": int(edge_count),
            "events": int(event_count),
        }
