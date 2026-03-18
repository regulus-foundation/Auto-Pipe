"""Auto-Pipe main pipeline graph builder

Flow:
  Pre-build check (tool)
  Phase 1: Design (console) -- requirements analysis + design in one shot
  [Human Review] -- design approval
  Phase 2: Development (console, parallel) -- code + tests
  Phase 3: Build/Test (tool, cycle) -- build -> test -> fix loop
  Phase 4: Review (api, parallel + human) -- quality/security -> approve/reject
  Phase 5: Docs (api, parallel) -- API docs/manual/changelog -> packaging
"""

from langgraph.graph import StateGraph, END
from core.checkpointer import get_checkpointer

from pipeline.state import AutoPipeState

# Phase 1
from pipeline.nodes.design import generate_design_node
# Phase 2
from pipeline.nodes.develop import (
    develop_code_node,
    write_tests_node,
)
# Phase 3
from pipeline.nodes.build_test import (
    pre_build_check_node,
    build_node,
    run_tests_node,
    check_test_result,
    fix_code_node,
)
# Phase 4
from pipeline.nodes.review import (
    start_review_node,
    review_quality_node,
    review_security_node,
    merge_reviews_node,
    review_decision_node,
    check_review_result,
    apply_review_fixes_node,
)
# Phase 5
from pipeline.nodes.docs import (
    start_docs_node,
    generate_api_doc_node,
    generate_ops_manual_node,
    generate_changelog_node,
    package_node,
    done_node,
)


def build_pipeline_graph():
    """Build main pipeline graph"""
    graph = StateGraph(AutoPipeState)

    # --- Node registration ---

    # Pre-build check
    graph.add_node("pre_build_check", pre_build_check_node)

    # Phase 1: Design (single console node)
    graph.add_node("generate_design", generate_design_node)

    # Phase 2: Development (parallel)
    graph.add_node("develop_code", develop_code_node)
    graph.add_node("write_tests", write_tests_node)

    # Phase 3: Build/Test (cycle)
    graph.add_node("build", build_node)
    graph.add_node("run_tests", run_tests_node)
    graph.add_node("fix_code", fix_code_node)

    # Phase 4: Review (parallel + approval)
    graph.add_node("start_review", start_review_node)
    graph.add_node("review_quality", review_quality_node)
    graph.add_node("review_security", review_security_node)
    graph.add_node("merge_reviews", merge_reviews_node)
    graph.add_node("review_decision", review_decision_node)
    graph.add_node("apply_review_fixes", apply_review_fixes_node)

    # Phase 5: Docs (parallel)
    graph.add_node("start_docs", start_docs_node)
    graph.add_node("generate_api_doc", generate_api_doc_node)
    graph.add_node("generate_ops_manual", generate_ops_manual_node)
    graph.add_node("generate_changelog", generate_changelog_node)
    graph.add_node("package", package_node)
    graph.add_node("done", done_node)

    # --- Edges ---

    # Pre-build check -> Phase 1
    graph.set_entry_point("pre_build_check")
    graph.add_edge("pre_build_check", "generate_design")

    # Phase 1 -> Phase 2 (after Human Review)
    # interrupt_before on develop_code: design approval wait
    graph.add_edge("generate_design", "develop_code")
    graph.add_edge("generate_design", "write_tests")

    # Phase 2 -> Phase 3 (fan-in)
    graph.add_edge("develop_code", "build")
    graph.add_edge("write_tests", "build")

    # Phase 3: build -> test -> check (cycle)
    graph.add_edge("build", "run_tests")
    graph.add_conditional_edges("run_tests", check_test_result, {
        "pass": "start_review",
        "fail": "fix_code",
        "max_retries": "package",
    })
    graph.add_edge("fix_code", "build")

    # Phase 4: gateway -> parallel review -> merge -> approval
    graph.add_edge("start_review", "review_quality")
    graph.add_edge("start_review", "review_security")
    graph.add_edge("review_quality", "merge_reviews")
    graph.add_edge("review_security", "merge_reviews")
    graph.add_edge("merge_reviews", "review_decision")

    graph.add_conditional_edges("review_decision", check_review_result, {
        "approved": "start_docs",
        "rejected": "apply_review_fixes",
        "max_retries": "start_docs",
    })
    graph.add_edge("apply_review_fixes", "start_review")

    # Phase 5: gateway -> parallel docs -> packaging
    graph.add_edge("start_docs", "generate_api_doc")
    graph.add_edge("start_docs", "generate_ops_manual")
    graph.add_edge("start_docs", "generate_changelog")
    graph.add_edge("generate_api_doc", "package")
    graph.add_edge("generate_ops_manual", "package")
    graph.add_edge("generate_changelog", "package")

    graph.add_edge("package", "done")
    graph.add_edge("done", END)

    # --- Compile ---
    return graph.compile(
        checkpointer=get_checkpointer(),
        interrupt_before=["develop_code", "review_decision"],
    )


def get_mermaid():
    """Graph diagram"""
    return build_pipeline_graph().get_graph().draw_mermaid()
