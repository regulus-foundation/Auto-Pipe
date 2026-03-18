"""Phase 1: 설계 생성 노드

요구사항 분석 + 통합 설계를 Console 한 번에 수행
(프로젝트 코드를 직접 읽고 분석 -> 설계까지 한 번에)
"""

from pipeline.state import AutoPipeState
from pipeline.utils import render_prompt, _emit_log
from core.config_loader import PipelineConfig


def generate_design_node(state: AutoPipeState) -> dict:
    """요구사항 분석 + 통합 설계 (console — 프로젝트 코드 직접 읽고 한 번에)"""
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("generate_design")
        template = config.get_prompt_template("generate_design")
    except ValueError:
        from core.executor import create_executor
        executor = create_executor("console")
        template = ""

    if not template:
        template = """# 요구사항 분석 + 통합 설계

## 요구사항
{requirements}

## 작업
프로젝트 코드를 직접 확인하고, 아래를 순서대로 수행하세요:

### 1단계: 요구사항 분석
- 기존 코드를 읽고 영향받는 레이어/모듈 파악
- 필요한 API 엔드포인트 정리
- DB 스키마 변경 사항 파악
- 주요 비즈니스 로직 정리

### 2단계: 상세 설계
- API 설계 (엔드포인트, 요청/응답 스키마, 인증/권한)
- DB 스키마 변경 (테이블, 컬럼, 관계, 마이그레이션)
- UI/화면 설계 (필요한 경우)
- 클래스/모듈 설계 (생성/수정할 파일 목록, 각 파일의 역할)

## 규칙
- 기존 프로젝트의 아키텍처, 네이밍, 패턴을 100% 따를 것
- 기존 코드를 직접 읽고 패턴을 파악한 뒤 설계할 것
- 구체적인 파일 경로, 클래스명, 메서드명까지 명시할 것
"""

    prompt = render_prompt(template, {
        "requirements": state["requirements"],
        "analysis_result": state.get("requirements_analysis", ""),  # 하위 호환
    })

    _emit_log("Phase 1: 요구사항 분석 + 설계 시작 (Console)")
    result = executor.run(
        prompt,
        project_path=state.get("project_path", ""),
        on_output=_emit_log,
    )

    if not result.success:
        return {
            "errors": [f"설계 생성 실패: {result.error}"],
            "current_phase": "design",
            "current_step": "설계 생성 실패",
        }

    _emit_log("Phase 1: 요구사항 분석 + 설계 완료")
    return {
        "design_spec": result.output,
        "current_phase": "design",
        "current_step": "설계 완료",
        "progress": 20,
        "messages": [f"요구사항 분석 + 설계 완료 ({result.duration_sec:.0f}초)"],
    }
