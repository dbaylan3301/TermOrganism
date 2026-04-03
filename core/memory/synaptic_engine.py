from __future__ import annotations

from pathlib import Path
from typing import Any

from .synaptic_store import SynapticStore
from .synaptic_types import SynapticEvent, SynapticNode


class SynapticMemory:
    DEFAULT_ROUTES = ("fast_v2", "hot_force", "fast", "repair_plan")

    def __init__(self, store: SynapticStore | None = None) -> None:
        self.store = store or SynapticStore()

    def _node_error(self, signature: str) -> SynapticNode:
        return SynapticNode(
            id=f"err:{signature}",
            type="error_signature",
            label=signature,
        )

    def _node_route(self, route: str) -> SynapticNode:
        return SynapticNode(
            id=f"route:{route}",
            type="repair_route",
            label=route,
        )

    def _node_repo(self, repo_type: str) -> SynapticNode:
        return SynapticNode(
            id=f"repo:{repo_type}",
            type="repo_type",
            label=repo_type,
        )

    def _node_intent(self, intent: str) -> SynapticNode:
        return SynapticNode(
            id=f"intent:{intent}",
            type="intent",
            label=intent,
        )

    def _node_file_ext(self, file_path: str | None) -> SynapticNode | None:
        if not file_path:
            return None
        p = Path(file_path)
        ext = p.suffix.lower() if p.suffix else "<none>"
        return SynapticNode(
            id=f"fileext:{ext}",
            type="file_extension",
            label=ext,
        )

    def _ensure_nodes(
        self,
        *,
        signature: str,
        route: str,
        repo_type: str | None,
        intent: str | None,
        file_path: str | None,
    ) -> None:
        self.store.upsert_node(self._node_error(signature))
        self.store.upsert_node(self._node_route(route))

        if repo_type:
            self.store.upsert_node(self._node_repo(repo_type))
        if intent:
            self.store.upsert_node(self._node_intent(intent))
        file_node = self._node_file_ext(file_path)
        if file_node:
            self.store.upsert_node(file_node)

    def _reward_delta(
        self,
        *,
        success: bool,
        verify_ok: bool | None,
        test_ok: bool | None,
    ) -> float:
        delta = 0.08 if success else -0.10
        if verify_ok is True:
            delta += 0.04
        elif verify_ok is False:
            delta -= 0.05

        if test_ok is True:
            delta += 0.06
        elif test_ok is False:
            delta -= 0.08

        return max(-0.20, min(0.20, delta))

    def remember_repair_outcome(
        self,
        *,
        signature: str,
        route: str,
        success: bool,
        file_path: str | None = None,
        repo_type: str | None = None,
        intent: str = "repair",
        confidence: float = 0.0,
        verify_ok: bool | None = None,
        test_ok: bool | None = None,
        latency_ms: float | None = None,
    ) -> dict[str, Any]:
        self._ensure_nodes(
            signature=signature,
            route=route,
            repo_type=repo_type,
            intent=intent,
            file_path=file_path,
        )

        delta = self._reward_delta(success=success, verify_ok=verify_ok, test_ok=test_ok)

        err_edge = self.store.adjust_edge(
            source_id=f"err:{signature}",
            target_id=f"route:{route}",
            kind="error_route",
            delta=delta,
            success=success,
            confidence=confidence,
            meta={"signature": signature},
        )

        if repo_type:
            self.store.adjust_edge(
                source_id=f"repo:{repo_type}",
                target_id=f"route:{route}",
                kind="repo_route",
                delta=delta * 0.60,
                success=success,
                confidence=confidence,
                meta={"repo_type": repo_type},
            )

        if intent:
            self.store.adjust_edge(
                source_id=f"intent:{intent}",
                target_id=f"route:{route}",
                kind="intent_route",
                delta=delta * 0.45,
                success=success,
                confidence=confidence,
                meta={"intent": intent},
            )

        file_node = self._node_file_ext(file_path)
        if file_node is not None:
            self.store.adjust_edge(
                source_id=file_node.id,
                target_id=f"route:{route}",
                kind="fileext_route",
                delta=delta * 0.50,
                success=success,
                confidence=confidence,
                meta={"file_ext": file_node.label},
            )
            self.store.adjust_edge(
                source_id=file_node.id,
                target_id=f"err:{signature}",
                kind="fileext_error",
                delta=delta * 0.30,
                success=success,
                confidence=confidence,
                meta={"file_ext": file_node.label},
            )

        self.store.add_event(
            SynapticEvent(
                event_type="repair_outcome",
                payload={
                    "signature": signature,
                    "route": route,
                    "success": success,
                    "file_path": file_path,
                    "repo_type": repo_type,
                    "intent": intent,
                    "confidence": confidence,
                    "verify_ok": verify_ok,
                    "test_ok": test_ok,
                    "latency_ms": latency_ms,
                    "delta": delta,
                },
            )
        )

        return {
            "signature": signature,
            "route": route,
            "delta": round(delta, 4),
            "error_route_weight": round(err_edge.weight, 4),
            "success": success,
        }

    def rank_routes(
        self,
        *,
        signature: str,
        repo_type: str | None = None,
        file_path: str | None = None,
        intent: str | None = "repair",
        candidate_routes: tuple[str, ...] | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        candidates = list(candidate_routes or self.DEFAULT_ROUTES)
        file_node = self._node_file_ext(file_path)

        weights = {
            "error_route": 0.55,
            "repo_route": 0.15,
            "fileext_route": 0.15,
            "intent_route": 0.15,
        }

        ranked: list[dict[str, Any]] = []

        for route in candidates:
            evidence: dict[str, Any] = {}
            total = 0.0
            denom = 0.0
            seen_total = 0

            err_edge = self.store.get_edge(f"err:{signature}", f"route:{route}", "error_route")
            if err_edge:
                evidence["error_route"] = round(err_edge.weight, 4)
                total += err_edge.weight * weights["error_route"]
                denom += weights["error_route"]
                seen_total += err_edge.seen_count

            if repo_type:
                repo_edge = self.store.get_edge(f"repo:{repo_type}", f"route:{route}", "repo_route")
                if repo_edge:
                    evidence["repo_route"] = round(repo_edge.weight, 4)
                    total += repo_edge.weight * weights["repo_route"]
                    denom += weights["repo_route"]
                    seen_total += repo_edge.seen_count

            if file_node is not None:
                file_edge = self.store.get_edge(file_node.id, f"route:{route}", "fileext_route")
                if file_edge:
                    evidence["fileext_route"] = round(file_edge.weight, 4)
                    total += file_edge.weight * weights["fileext_route"]
                    denom += weights["fileext_route"]
                    seen_total += file_edge.seen_count

            if intent:
                intent_edge = self.store.get_edge(f"intent:{intent}", f"route:{route}", "intent_route")
                if intent_edge:
                    evidence["intent_route"] = round(intent_edge.weight, 4)
                    total += intent_edge.weight * weights["intent_route"]
                    denom += weights["intent_route"]
                    seen_total += intent_edge.seen_count

            base = 0.50 if denom == 0 else total / denom
            prior = round(max(0.0, min(1.0, base)), 4)

            ranked.append(
                {
                    "route": route,
                    "prior": prior,
                    "seen_total": int(seen_total),
                    "evidence": evidence,
                    "matched": bool(evidence),
                }
            )

        ranked.sort(key=lambda x: (x["prior"], x["seen_total"]), reverse=True)
        return ranked

    def explain_prior(
        self,
        *,
        signature: str,
        repo_type: str | None = None,
        file_path: str | None = None,
        intent: str | None = "repair",
        candidate_routes: tuple[str, ...] | list[str] | None = None,
    ) -> dict[str, Any]:
        routes = self.rank_routes(
            signature=signature,
            repo_type=repo_type,
            file_path=file_path,
            intent=intent,
            candidate_routes=candidate_routes,
        )
        return {
            "signature": signature,
            "repo_type": repo_type,
            "file_path": file_path,
            "intent": intent,
            "routes": routes,
            "best_route": routes[0]["route"] if routes else None,
        }

    def stats(self) -> dict[str, Any]:
        return self.store.stats()
