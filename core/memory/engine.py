from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class RepairRecord:
    id: str
    project_hash: str
    file_hash: str
    failure_signature: str
    repair_type: str
    repair_code: str
    confidence: float
    success_verified: bool
    timestamp: datetime
    context_summary: dict


class MemoryEngine:
    """
    SQLite-backed repair memory.
    - local project memory: .termorganism/memory.db
    - global anonymized memory: ~/.termorganism/global_memory.db
    """

    def __init__(
        self,
        db_path: Path = Path(".termorganism/memory.db"),
        global_db_path: Path = Path.home() / ".termorganism/global_memory.db",
    ):
        self.db_path = db_path
        self.global_db_path = global_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.global_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self, path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(path)
        return conn

    def _init_schema(self):
        schema = """
        CREATE TABLE IF NOT EXISTS repairs (
            id TEXT PRIMARY KEY,
            project_hash TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            failure_signature TEXT NOT NULL,
            repair_type TEXT NOT NULL,
            repair_code TEXT,
            confidence REAL,
            success_verified BOOLEAN,
            timestamp TEXT,
            context_summary TEXT,
            latency_ms INTEGER,
            sandbox_used BOOLEAN
        );

        CREATE INDEX IF NOT EXISTS idx_failure_sig ON repairs(failure_signature);
        CREATE INDEX IF NOT EXISTS idx_project ON repairs(project_hash);
        CREATE INDEX IF NOT EXISTS idx_file ON repairs(file_hash);
        CREATE INDEX IF NOT EXISTS idx_success ON repairs(success_verified, confidence);

        CREATE TABLE IF NOT EXISTS patterns (
            id TEXT PRIMARY KEY,
            signature_pattern TEXT UNIQUE,
            success_rate REAL,
            total_attempts INTEGER,
            avg_confidence REAL,
            last_seen TEXT
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );
        """
        for db in [self.db_path, self.global_db_path]:
            conn = self._connect(db)
            try:
                conn.executescript(schema)
                conn.commit()
            finally:
                conn.close()

    def project_hash_for(self, target_path: Path | str | None) -> str:
        if not target_path:
            return hashlib.sha256(b"unknown-project").hexdigest()[:16]
        p = Path(target_path).resolve()
        root = p.parent
        for cand in [root] + list(root.parents):
            if (cand / ".git").exists():
                root = cand
                break
        return hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]

    def file_hash_for(self, target_path: Path | str | None) -> str:
        if not target_path:
            return hashlib.sha256(b"unknown-file").hexdigest()[:16]
        p = Path(target_path)
        try:
            return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        except Exception:
            return hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:16]

    def record_repair(self, record: RepairRecord, local_only: bool = False):
        conn = self._connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO repairs
                (id, project_hash, file_hash, failure_signature, repair_type, repair_code,
                 confidence, success_verified, timestamp, context_summary, latency_ms, sandbox_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_hash,
                    record.file_hash,
                    record.failure_signature,
                    record.repair_type,
                    record.repair_code,
                    float(record.confidence or 0.0),
                    1 if record.success_verified else 0,
                    record.timestamp.isoformat(),
                    json.dumps(record.context_summary, ensure_ascii=False),
                    int(record.context_summary.get("latency_ms", 0) or 0),
                    1 if record.context_summary.get("sandbox_used") else 0,
                ),
            )
            conn.commit()
            self._update_pattern(record.failure_signature, record.success_verified, float(record.confidence or 0.0))
        finally:
            conn.close()

        if not local_only and record.success_verified and float(record.confidence or 0.0) > 0.9:
            self._sync_to_global(record)

    def find_similar_repairs(
        self,
        failure_signature: str,
        project_hash: Optional[str] = None,
        limit: int = 5,
    ) -> List[RepairRecord]:
        conn = self._connect(self.db_path)
        try:
            rows = []
            if project_hash:
                cursor = conn.execute(
                    """
                    SELECT * FROM repairs
                    WHERE failure_signature = ?
                      AND project_hash = ?
                      AND success_verified = 1
                      AND confidence > 0.8
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (failure_signature, project_hash, limit),
                )
                rows = cursor.fetchall()

            if len(rows) < 2:
                cursor = conn.execute(
                    """
                    SELECT * FROM repairs
                    WHERE failure_signature = ?
                      AND success_verified = 1
                      AND confidence > 0.8
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (failure_signature, limit),
                )
                rows = cursor.fetchall()

            if len(rows) < 2:
                cursor = conn.execute(
                    """
                    SELECT * FROM repairs
                    WHERE failure_signature LIKE ?
                      AND success_verified = 1
                    ORDER BY confidence DESC, timestamp DESC
                    LIMIT ?
                    """,
                    (f"%{failure_signature[:12]}%", limit),
                )
                rows = cursor.fetchall()

            return [self._row_to_record(r) for r in rows]
        finally:
            conn.close()

    def get_repair_prior(self, failure_signature: str, repair_type: str) -> float:
        conn = self._connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN success_verified THEN 1 ELSE 0 END) as success
                FROM repairs
                WHERE failure_signature = ?
                  AND repair_type = ?
                """,
                (failure_signature, repair_type),
            )
            row = cursor.fetchone()
            if not row or row[0] == 0:
                return 0.5
            total = int(row[0] or 0)
            success = int(row[1] or 0)
            return round((success + 1) / (total + 2), 4)
        finally:
            conn.close()

    def suggest_from_memory(self, failure_context: dict, current_file: Path) -> Optional[Dict]:
        sig = self._normalize_failure(failure_context)
        project_hash = self.project_hash_for(current_file)
        similar = self.find_similar_repairs(sig, project_hash=project_hash, limit=3)
        if not similar:
            return None

        best = max(
            similar,
            key=lambda r: float(r.confidence or 0.0) * (0.9 ** max(0, (datetime.now() - r.timestamp).days)),
        )
        return {
            "suggested_repair": best.repair_code,
            "confidence": float(best.confidence or 0.0),
            "historical_success_rate": self.get_repair_prior(sig, best.repair_type),
            "based_on": f"{len(similar)} similar cases",
            "apply_recommendation": "auto" if float(best.confidence or 0.0) > 0.95 else "review",
            "repair_type": best.repair_type,
        }

    def _normalize_failure(self, context: dict) -> str:
        tb = context.get("traceback", []) or []
        normalized = []

        for frame in tb:
            function = frame.get("function") or "unknown_fn"
            error_type = frame.get("error_type") or context.get("error_type") or "UnknownError"
            normalized.append(f"{function}:{error_type}")

        if not normalized:
            error_text = str(context.get("error_text") or "")
            m = re.search(r"([A-Za-z_][A-Za-z0-9_]*Error)", error_text)
            err = m.group(1) if m else "UnknownError"
            normalized.append(err)

        return hashlib.sha256("|".join(normalized).encode("utf-8")).hexdigest()[:32]

    def _update_pattern(self, signature: str, success: bool, confidence: float):
        conn = self._connect(self.db_path)
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO patterns (id, signature_pattern, success_rate, total_attempts, avg_confidence, last_seen)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(signature_pattern) DO UPDATE SET
                    success_rate = (success_rate * total_attempts + ?) / (total_attempts + 1),
                    avg_confidence = (avg_confidence * total_attempts + ?) / (total_attempts + 1),
                    total_attempts = total_attempts + 1,
                    last_seen = ?
                """,
                (
                    hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16],
                    signature,
                    1.0 if success else 0.0,
                    confidence,
                    now,
                    1.0 if success else 0.0,
                    confidence,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _sync_to_global(self, record: RepairRecord):
        conn = self._connect(self.global_db_path)
        try:
            anonymized_code = self._anonymize_code(record.repair_code or "")
            conn.execute(
                """
                INSERT OR REPLACE INTO repairs
                (id, project_hash, file_hash, failure_signature, repair_type, repair_code,
                 confidence, success_verified, timestamp, context_summary, latency_ms, sandbox_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    "global",
                    hashlib.sha256(record.file_hash.encode("utf-8")).hexdigest()[:16],
                    record.failure_signature,
                    record.repair_type,
                    anonymized_code,
                    float(record.confidence or 0.0),
                    1 if record.success_verified else 0,
                    record.timestamp.isoformat(),
                    json.dumps({}, ensure_ascii=False),
                    int(record.context_summary.get("latency_ms", 0) or 0),
                    1 if record.context_summary.get("sandbox_used") else 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _anonymize_code(self, code: str) -> str:
        return re.sub(r'\b[A-Z_][A-Z_0-9]{2,}\b', 'CONST', code or '')

    def _row_to_record(self, row) -> RepairRecord:
        return RepairRecord(
            id=row[0],
            project_hash=row[1],
            file_hash=row[2],
            failure_signature=row[3],
            repair_type=row[4],
            repair_code=row[5] or "",
            confidence=float(row[6] or 0.0),
            success_verified=bool(row[7]),
            timestamp=datetime.fromisoformat(row[8]),
            context_summary=json.loads(row[9]) if row[9] else {},
        )
