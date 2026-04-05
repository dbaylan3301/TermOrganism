from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


REPO = Path("/root/TermOrganismGitFork")


def _run_repair(target: str) -> dict[str, Any]:
    env = dict(__import__("os").environ)
    env["TERMORGANISM_USE_DAEMON"] = "0"
    p = subprocess.run(
        ["./termorganism", "repair", str(Path(target).expanduser().resolve()), "--json"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        env=env,
    )
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "").strip() or f"repair failed rc={p.returncode}")
    data = json.loads(p.stdout)
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        data = data["result"]
    return data


def _build_view(data: dict[str, Any]) -> dict[str, Any]:
    routing = data.get("routing") or {}
    return {
        "target": data.get("target_file"),
        "signature": data.get("signature"),
        "success": data.get("success"),
        "mode": data.get("mode"),
        "strategy": data.get("strategy"),
        "planner": {
            "suggested_mode": routing.get("planner_suggested_mode"),
            "reason": routing.get("planner_reason"),
        },
        "final": {
            "effective_mode": routing.get("effective_mode"),
        },
        "intent": {
            "focus": routing.get("intent_focus"),
            "routes": routing.get("intent_preload_routes") or [],
            "confidence": routing.get("intent_confidence"),
            "reason": routing.get("intent_reason"),
        },
        "bridge": {
            "route": routing.get("bridge_recommended_route"),
            "score": routing.get("bridge_score"),
            "reason": routing.get("bridge_reason"),
        },
        "whisper": {
            "kind": routing.get("whisper_kind"),
            "priority": routing.get("whisper_priority"),
            "message": routing.get("whisper_message"),
            "reason": routing.get("whisper_reason"),
            "verify_emphasis": routing.get("whisper_verify_emphasis"),
        },
        "arbitration": {
            "winner": routing.get("arbitration_winner"),
            "candidate_count": routing.get("arbitration_candidate_count"),
            "reason": routing.get("arbitration_reason"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-explain-route")
    parser.add_argument("file")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    data = _run_repair(args.file)
    view = _build_view(data)

    if args.json:
        print(json.dumps(view, ensure_ascii=False, indent=None if args.compact else 2))
        return 0

    print("TermOrganism Route Explain")
    print("--------------------------")
    print(f"target: {view['target']}")
    print(f"signature: {view['signature']}")
    print(f"success: {view['success']}")
    print(f"strategy: {view['strategy']}")
    print(f"planner_suggested: {view['planner']['suggested_mode']}")
    print(f"final_effective: {view['final']['effective_mode']}")
    print(f"planner_reason: {view['planner']['reason']}")
    print(f"intent_focus: {view['intent']['focus']}")
    print(f"intent_routes: {', '.join(view['intent']['routes']) or '-'}")
    print(f"intent_reason: {view['intent']['reason'] or '-'}")
    print(f"bridge_route: {view['bridge']['route'] or '-'}")
    print(f"bridge_score: {view['bridge']['score']}")
    print(f"bridge_reason: {view['bridge']['reason'] or '-'}")
    print(f"whisper_kind: {view['whisper']['kind'] or '-'}")
    print(f"whisper_priority: {view['whisper']['priority']}")
    print(f"whisper_reason: {view['whisper']['reason'] or '-'}")
    print(f"arbitration_winner: {view['arbitration']['winner'] or '-'}")
    print(f"arbitration_count: {view['arbitration']['candidate_count']}")
    print(f"arbitration_reason: {view['arbitration']['reason'] or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
