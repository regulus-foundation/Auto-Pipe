"""Phase 4: 코드 리뷰 (api executor, 병렬 + Human-in-the-Loop)"""

from typing import Literal

from pipeline.state import AutoPipeState
from pipeline.utils import render_prompt, parse_code_output, format_source_code, _emit_log
from core.config_loader import PipelineConfig


def start_review_node(state: AutoPipeState) -> dict:
    """리뷰 시작 게이트웨이 (병렬 fan-out용)"""
    return {
        "current_phase": "review",
        "current_step": "코드 리뷰 시작",
        "progress": 65,
        "messages": ["코드 리뷰 시작"],
    }


def review_quality_node(state: AutoPipeState) -> dict:
    """코드 품질 리뷰 (api executor)"""
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("review_quality")
        template = config.get_prompt_template("review_quality")
    except ValueError:
        executor = config.get_executor("code_review")
        template = config.get_prompt_template("code_review")

    prompt = render_prompt(template, {
        "code": format_source_code(state.get("source_code", {})),
        "api_spec": state.get("api_spec", ""),
        "requirements": state.get("requirements", ""),
    })

    _emit_log("Phase 4: 코드 품질 리뷰 시작")
    result = executor.run(prompt)

    if not result.success:
        return {"errors": [f"코드 리뷰 실패: {result.error}"]}

    _emit_log("Phase 4: 코드 품질 리뷰 완료")
    return {
        "review_report": result.output,
        "current_step": "코드 품질 리뷰 완료",
        "progress": 75,
        "messages": [f"코드 품질 리뷰 완료 ({result.duration_sec:.0f}초)"],
    }


def review_security_node(state: AutoPipeState) -> dict:
    """보안 체크 (api executor)"""
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("review_security")
        template = config.get_prompt_template("review_security")
    except ValueError:
        executor = config.get_executor("code_review")
        template = config.get_prompt_template("code_review")

    prompt = render_prompt(template, {
        "code": format_source_code(state.get("source_code", {})),
    })

    _emit_log("Phase 4: 보안 체크 시작")
    result = executor.run(prompt)

    if not result.success:
        return {"errors": [f"보안 체크 실패: {result.error}"]}

    _emit_log("Phase 4: 보안 체크 완료")
    return {
        "security_report": result.output,
        "current_step": "보안 체크 완료",
        "progress": 75,
        "messages": [f"보안 체크 완료 ({result.duration_sec:.0f}초)"],
    }


def merge_reviews_node(state: AutoPipeState) -> dict:
    """리뷰 결과 통합"""
    merged = f"""## 코드 품질 리뷰
{state.get('review_report', '(없음)')}

## 보안 체크
{state.get('security_report', '(없음)')}
"""
    _emit_log("Phase 4: 리뷰 통합 완료 — 승인 대기")
    return {
        "merged_review": merged,
        "current_step": "리뷰 통합 완료 — 승인 대기",
        "progress": 80,
        "messages": ["리뷰 통합 완료 — 승인 대기"],
    }


def review_decision_node(state: AutoPipeState) -> dict:
    """리뷰 승인/반려 판정 (Human-in-the-Loop 후 실행)"""
    return {
        "current_step": "리뷰 승인 처리",
        "progress": 85,
    }


def check_review_result(state: AutoPipeState) -> Literal["approved", "rejected", "max_retries"]:
    """리뷰 결과에 따라 분기"""
    if state.get("review_approved"):
        return "approved"
    if state.get("review_iteration", 0) >= state.get("max_review_iterations", 3):
        return "max_retries"
    return "rejected"


def apply_review_fixes_node(state: AutoPipeState) -> dict:
    """리뷰 피드백 반영 코드 수정"""
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("apply_review_fixes")
    except ValueError:
        executor = config.get_executor("develop_code")

    template = """# 리뷰 피드백 반영 코드 수정

## 리뷰 피드백
{review_feedback}

## 현재 코드
{source_code}

## 규칙
- 피드백에 해당하는 파일만 수정
- 파일별로 `=== FILE: 경로 ===` 형식으로 구분
"""

    iteration = state.get("review_iteration", 0) + 1
    prompt = render_prompt(template, {
        "review_feedback": state.get("review_feedback", state.get("merged_review", "")),
        "source_code": format_source_code(state.get("source_code", {})),
    })

    _emit_log(f"Phase 4: 리뷰 수정 #{iteration}")
    result = executor.run(
        prompt,
        project_path=state.get("project_path", ""),
        on_output=_emit_log,
    )

    if not result.success:
        return {
            "review_iteration": iteration,
            "errors": [f"리뷰 수정 실패: {result.error}"],
        }

    updated_code = parse_code_output(result.output)
    merged = {**state.get("source_code", {}), **updated_code}

    _emit_log(f"Phase 4: 리뷰 수정 완료 ({len(updated_code)}개 파일)")
    return {
        "source_code": merged,
        "review_iteration": iteration,
        "review_approved": False,
        "current_step": f"리뷰 수정 #{iteration} 완료",
        "messages": [f"리뷰 수정 #{iteration} ({len(updated_code)}개 파일)"],
    }
