#!/usr/bin/env python3
from __future__ import annotations

import json

from core.project.graph import build_project_graph
from core.causal.analyzer import analyze_failure_causes
from core.planner.repair_planner import build_repair_plans
from core.planner.branch_executor import execute_repair_plan
from core.verify.contract_synth import synthesize_and_check_contract
from core.semantic.fault_localizer import localize_fault, summarize_suspicions
from core.repro.harness import run_python_file


def main():
    file_path = "demo/cross_file_dep.py"
    repro = run_python_file(file_path).to_dict()
    semantic = {
        "repro": repro,
        "localization": summarize_suspicions(localize_fault(repro.get("stderr", ""), file_path=file_path)),
    }
    graph = build_project_graph(file_path).to_dict()
    causes = [c.to_dict() for c in analyze_failure_causes(
        error_text=repro.get("stderr", ""),
        semantic=semantic,
        project_graph=graph,
    )]
    plans = [p.to_dict() for p in build_repair_plans(
        error_text=repro.get("stderr", ""),
        semantic=semantic,
        causes=causes,
        project_graph=graph,
    )]

    best_plan = plans[0] if plans else None
    branch = execute_repair_plan(best_plan, file_path) if best_plan else None
    contract = synthesize_and_check_contract(
        before_error_text=repro.get("stderr", ""),
        branch_result=branch or {},
        expected_behavior=(best_plan or {}).get("expected_behavior", {}),
    ) if best_plan else None

    print(json.dumps({
        "graph_summary": {
            "project_root": graph.get("project_root"),
            "file_count": len(graph.get("files", [])),
        },
        "causes": causes,
        "plan_count": len(plans),
        "best_plan": best_plan,
        "branch_result": branch,
        "contract_result": contract,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
