"""Phase 5: 문서 생성 + 산출물 패키징 (api executor, 병렬)"""

from pathlib import Path

from pipeline.state import AutoPipeState
from pipeline.utils import render_prompt, format_source_code, _emit_log
from core.config_loader import PipelineConfig


def start_docs_node(state: AutoPipeState) -> dict:
    """문서 생성 시작 게이트웨이 (병렬 fan-out용)"""
    return {
        "current_phase": "docs",
        "current_step": "문서 생성 시작",
        "progress": 85,
        "messages": ["문서 생성 시작"],
    }


def generate_api_doc_node(state: AutoPipeState) -> dict:
    """API 문서 생성"""
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("generate_api_doc")
        template = config.get_prompt_template("generate_api_doc")
    except ValueError:
        executor = config.get_executor("generate_docs")
        template = config.get_prompt_template("generate_docs")

    prompt = render_prompt(template, {
        "implementation": format_source_code(state.get("source_code", {})),
        "api_spec": state.get("api_spec", ""),
        "requirements": state.get("requirements", ""),
    })

    _emit_log("Phase 5: API 문서 생성 시작")
    result = executor.run(prompt)

    if not result.success:
        return {"errors": [f"API 문서 생성 실패: {result.error}"]}

    _emit_log("Phase 5: API 문서 생성 완료")
    return {
        "api_doc": result.output,
        "current_step": "API 문서 완료",
        "progress": 88,
        "messages": [f"API 문서 생성 완료 ({result.duration_sec:.0f}초)"],
    }


def generate_ops_manual_node(state: AutoPipeState) -> dict:
    """운영 매뉴얼 생성"""
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("generate_ops_manual")
        template = config.get_prompt_template("generate_ops_manual")
    except ValueError:
        executor = config.get_executor("generate_docs")
        template = config.get_prompt_template("generate_docs")

    prompt = render_prompt(template, {
        "implementation": format_source_code(state.get("source_code", {})),
        "db_schema": state.get("db_schema", ""),
        "requirements": state.get("requirements", ""),
    })

    _emit_log("Phase 5: 운영 매뉴얼 생성 시작")
    result = executor.run(prompt)

    if not result.success:
        return {"errors": [f"운영 매뉴얼 생성 실패: {result.error}"]}

    _emit_log("Phase 5: 운영 매뉴얼 생성 완료")
    return {
        "ops_manual": result.output,
        "current_step": "운영 매뉴얼 완료",
        "progress": 90,
        "messages": [f"운영 매뉴얼 생성 완료 ({result.duration_sec:.0f}초)"],
    }


def generate_changelog_node(state: AutoPipeState) -> dict:
    """변경 이력 생성"""
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("generate_changelog")
        template = config.get_prompt_template("generate_changelog")
    except ValueError:
        executor = config.get_executor("generate_docs")
        template = config.get_prompt_template("generate_docs")

    prompt = render_prompt(template, {
        "implementation": format_source_code(state.get("source_code", {})),
        "requirements": state.get("requirements", ""),
    })

    _emit_log("Phase 5: 변경 이력 생성 시작")
    result = executor.run(prompt)

    if not result.success:
        return {"errors": [f"변경 이력 생성 실패: {result.error}"]}

    _emit_log("Phase 5: 변경 이력 생성 완료")
    return {
        "changelog": result.output,
        "current_step": "변경 이력 완료",
        "progress": 92,
        "messages": [f"변경 이력 생성 완료 ({result.duration_sec:.0f}초)"],
    }


def package_node(state: AutoPipeState) -> dict:
    """산출물 패키징 — 파일로 저장"""
    project_name = state.get("project_name", "unknown")
    config_dir = Path(state["config_path"]).parent
    output_dir = config_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    files_to_save = {
        "design/api-spec.md": state.get("api_spec", ""),
        "design/db-schema.md": state.get("db_schema", ""),
        "design/ui-spec.md": state.get("ui_spec", ""),
        "docs/api-doc.md": state.get("api_doc", ""),
        "docs/ops-manual.md": state.get("ops_manual", ""),
        "docs/changelog.md": state.get("changelog", ""),
        "reports/review.md": state.get("merged_review", ""),
    }

    # 소스 코드
    for filepath, content in state.get("source_code", {}).items():
        files_to_save[f"src/{filepath}"] = content

    # 테스트 코드
    for filepath, content in state.get("test_code", {}).items():
        files_to_save[f"test/{filepath}"] = content

    saved = []
    for rel_path, content in files_to_save.items():
        if content:
            full_path = output_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            saved.append(str(rel_path))

    _emit_log(f"산출물 패키징 완료: {len(saved)}개 파일 → {output_dir}")
    return {
        "deliverables": saved,
        "current_step": "산출물 패키징 완료",
        "progress": 95,
        "messages": [f"산출물 패키징 완료 ({len(saved)}개 파일)"],
    }


def done_node(state: AutoPipeState) -> dict:
    """완료"""
    _emit_log("파이프라인 완료!")
    return {
        "current_phase": "done",
        "current_step": "완료",
        "progress": 100,
        "messages": ["파이프라인 완료"],
    }
