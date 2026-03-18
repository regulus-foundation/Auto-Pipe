"""Phase 2: 코드 개발 + 테스트 작성 (console executor, 병렬)"""

from pathlib import Path

from pipeline.state import AutoPipeState
from pipeline.utils import render_prompt, parse_code_output, _emit_log
from core.config_loader import PipelineConfig


def develop_code_node(state: AutoPipeState) -> dict:
    """코드 개발 — console executor (대량 코드 생성)"""
    config = PipelineConfig(state["config_path"])
    executor = config.get_executor("develop_code")
    template = config.get_prompt_template("develop_code")

    # 통합 설계서 사용 (없으면 개별 설계서 조합 — 하위 호환)
    design = state.get("design_spec", "")
    if not design:
        design = f"""## API 설계
{state.get('api_spec', '')}

## DB 스키마
{state.get('db_schema', '')}

## UI 설계
{state.get('ui_spec', '')}"""

    prompt = render_prompt(template, {
        "design_spec": design,
        "requirements": state["requirements"],
    })

    _emit_log("Phase 2: 코드 개발 시작")
    result = executor.run(
        prompt,
        project_path=state.get("project_path", ""),
        on_output=_emit_log,
    )

    if not result.success:
        return {
            "errors": [f"코드 개발 실패: {result.error}"],
            "current_step": "코드 개발 실패",
        }

    source_code = parse_code_output(result.output)
    _emit_log(f"Phase 2: 코드 개발 완료 ({len(source_code)}개 파일)")
    return {
        "source_code": source_code,
        "code_files_created": list(source_code.keys()),
        "current_phase": "develop",
        "current_step": "코드 개발 완료",
        "progress": 35,
        "messages": [f"코드 개발 완료 ({len(source_code)}개 파일, {result.duration_sec:.0f}초)"],
    }


def write_tests_node(state: AutoPipeState) -> dict:
    """테스트 작성 — console executor"""
    config = PipelineConfig(state["config_path"])
    executor = config.get_executor("write_tests")
    template = config.get_prompt_template("write_tests")

    prompt = render_prompt(template, {
        "requirements": state["requirements"],
        "api_spec": state.get("api_spec", ""),
        "source_code": str(list(state.get("source_code", {}).keys())),
    })

    _emit_log("Phase 2: 테스트 작성 시작")
    result = executor.run(
        prompt,
        project_path=state.get("project_path", ""),
        on_output=_emit_log,
    )

    if not result.success:
        return {
            "errors": [f"테스트 작성 실패: {result.error}"],
            "current_step": "테스트 작성 실패",
        }

    test_code = parse_code_output(result.output)
    _emit_log(f"Phase 2: 테스트 작성 완료 ({len(test_code)}개 파일)")
    return {
        "test_code": test_code,
        "code_files_created": list(test_code.keys()),
        "current_phase": "develop",
        "current_step": "테스트 작성 완료",
        "progress": 40,
        "messages": [f"테스트 작성 완료 ({len(test_code)}개 파일, {result.duration_sec:.0f}초)"],
    }


def write_files_node(state: AutoPipeState) -> dict:
    """생성된 코드를 실제 프로젝트에 파일로 기록

    Phase 2(코드 생성) → Phase 3(빌드/테스트) 사이에서 실행.
    source_code, test_code 딕셔너리를 프로젝트 경로에 실제 파일로 저장한다.
    """
    project_path = state.get("project_path", "")
    if not project_path:
        return {"errors": ["프로젝트 경로가 없습니다"]}

    base = Path(project_path)
    written = []

    for code_dict in [state.get("source_code", {}), state.get("test_code", {})]:
        for filepath, content in code_dict.items():
            if not content:
                continue
            full_path = base / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            written.append(filepath)

    _emit_log(f"Phase 2: 프로젝트에 {len(written)}개 파일 기록 → {project_path}")
    return {
        "current_step": f"파일 기록 완료 ({len(written)}개)",
        "progress": 45,
        "messages": [f"프로젝트에 {len(written)}개 파일 기록 완료"],
    }
