"""Auto-Pipe 파이프라인 State 정의

모든 Phase의 데이터가 이 State를 통해 흐름.
Annotated + reducer로 병렬 노드 충돌 방지.
"""

from typing import TypedDict, Annotated
import operator


def _last(a, b):
    """병렬 노드에서 동시 쓰기 시 마지막 값 사용"""
    return b


def _max(a, b):
    """병렬 노드에서 동시 쓰기 시 최대값 사용"""
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


class AutoPipeState(TypedDict):
    # ─── 입력 ───
    requirements: str
    project_name: str
    project_path: str
    config_path: str  # pipeline.yaml 경로

    # ─── Phase 1: 설계 ───
    requirements_analysis: str
    design_spec: str  # 통합 설계서 (API + DB + UI + 클래스 설계)
    api_spec: str     # 하위 호환 (기존 state 참조용)
    db_schema: str
    ui_spec: str
    design_approved: bool
    design_feedback: str

    # ─── Phase 2: 개발 ───
    source_code: dict  # {filepath: code_content}
    test_code: dict  # {filepath: test_content}
    code_files_created: Annotated[list[str], operator.add]

    # ─── 사전 체크 (빌드 + 테스트) ───
    pre_build_result: str   # "success" | "fail" — 파이프라인 시작 전 빌드 상태
    pre_build_errors: str   # 사전 빌드 에러 로그 (기존 에러 판별용)
    pre_test_result: str    # "success" | "fail" — 파이프라인 시작 전 테스트 상태
    pre_test_errors: str    # 사전 테스트 에러 로그 (기존 에러 판별용)

    # ─── Phase 3: 빌드/테스트 ───
    build_result: str  # "success" | "fail"
    build_log: str
    test_result: str  # "pass" | "fail"
    test_log: str
    test_errors: list[str]
    fix_iteration: int
    max_fix_iterations: int

    # ─── Phase 4: 리뷰 ───
    review_report: str
    security_report: str
    merged_review: str
    review_approved: bool
    review_feedback: str
    review_iteration: int
    max_review_iterations: int

    # ─── Phase 5: 문서 ───
    api_doc: str
    ops_manual: str
    changelog: str
    deliverables: list[str]

    # ─── 공통 (Annotated: 병렬 노드 동시 쓰기 허용) ───
    current_phase: Annotated[str, _last]
    current_step: Annotated[str, _last]
    progress: Annotated[int, _max]
    messages: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
