"""Phase 3: 빌드 + 테스트 실행 + 코드 수정 순환 (tool/console executor)"""

from typing import Literal

from pipeline.state import AutoPipeState
from pipeline.utils import render_prompt, parse_code_output, format_source_code, _emit_log
from core.config_loader import PipelineConfig
from core.executor import create_executor


def _extract_error_lines(output: str) -> list[str]:
    """빌드/테스트 출력에서 에러 라인만 추출"""
    errors = []
    for line in output.split("\n"):
        lower = line.lower().strip()
        if any(kw in lower for kw in ["error:", "error ", "fail", "cannot find symbol", "not applicable"]):
            errors.append(line.strip())
    return errors


def _build_only_command(build_cmd: str, test_cmd: str) -> str:
    """빌드 커맨드에서 테스트를 제외한 커맨드 반환.

    파이프라인이 빌드/테스트를 분리 실행하므로,
    빌드 커맨드가 테스트를 포함하는 경우 자동으로 제외한다.
    """
    if not test_cmd:
        return build_cmd

    # Gradle: ./gradlew build → ./gradlew build -x test
    if "gradlew" in build_cmd and "-x test" not in build_cmd:
        if "build" in build_cmd or "assemble" not in build_cmd:
            return f"{build_cmd} -x test"

    # Maven: mvn package/install/verify → mvn ... -DskipTests
    if ("mvn " in build_cmd or "mvnw " in build_cmd) and "-DskipTests" not in build_cmd:
        return f"{build_cmd} -DskipTests"

    # npm/yarn: build는 보통 테스트 미포함이므로 그대로
    # Go/Rust/Python: build와 test가 별도 커맨드이므로 그대로

    return build_cmd


def pre_build_check_node(state: AutoPipeState) -> dict:
    """사전 빌드+테스트 체크 — 파이프라인 시작 전 기존 상태 확인"""
    config = PipelineConfig(state["config_path"])
    executor = create_executor("tool")
    project_path = state.get("project_path", "")
    updates = {
        "pre_build_result": "success",
        "pre_build_errors": "",
        "pre_test_result": "success",
        "pre_test_errors": "",
        "progress": 2,
        "messages": [],
    }

    # ── 빌드 체크 ──
    build_cfg = config.nodes.get("build", {})
    test_cfg = config.nodes.get("run_tests", {})
    build_cmd = build_cfg.get("command", "") or config.build_command
    test_cmd = test_cfg.get("command", "") or config.test_command

    # 빌드/테스트 분리 실행이므로 빌드에서 테스트 제외
    build_cmd = _build_only_command(build_cmd, test_cmd)
    build_timeout = build_cfg.get("timeout", 300)

    if build_cmd:
        _emit_log(f"사전 빌드 체크: {build_cmd} (타임아웃: {build_timeout}초)")
        result = executor.run(build_cmd, cwd=project_path, timeout=build_timeout)

        if result.success:
            _emit_log("사전 빌드 체크: 통과 ✓")
            updates["messages"].append(f"사전 빌드 통과 ({result.duration_sec:.0f}초)")
        else:
            error_lines = _extract_error_lines(result.output)
            _emit_log("사전 빌드 체크: 기존 빌드 에러 발견 ⚠️")
            for line in error_lines[:10]:
                _emit_log(line)
            updates["pre_build_result"] = "fail"
            updates["pre_build_errors"] = "\n".join(error_lines[:20])
            updates["messages"].append(f"⚠️ 사전 빌드 실패 — 기존 에러 {len(error_lines)}건")
    else:
        _emit_log("사전 빌드 체크: 빌드 커맨드 없음 — 스킵")
        updates["messages"].append("사전 빌드 체크 스킵 (커맨드 없음)")

    # ── 테스트 체크 (빌드 성공 시에만) ──
    test_timeout = test_cfg.get("timeout", 300)

    if test_cmd and updates["pre_build_result"] == "success":
        _emit_log(f"사전 테스트 체크: {test_cmd} (타임아웃: {test_timeout}초)")
        result = executor.run(test_cmd, cwd=project_path, timeout=test_timeout)

        if result.success:
            _emit_log("사전 테스트 체크: 통과 ✓")
            updates["messages"].append(f"사전 테스트 통과 ({result.duration_sec:.0f}초)")
        else:
            # 테스트 출력 전체를 저장 (에러 키워드 매칭이 안 될 수 있으므로)
            error_lines = _extract_error_lines(result.output)
            full_tail = result.output.strip().split("\n")[-30:]
            _emit_log("사전 테스트 체크: 기존 테스트 실패 발견 ⚠️")
            for line in (error_lines or full_tail)[:10]:
                _emit_log(line)
            updates["pre_test_result"] = "fail"
            updates["pre_test_errors"] = "\n".join(full_tail)
            updates["messages"].append(f"⚠️ 사전 테스트 실패 — 기존 테스트 에러")
    elif not test_cmd:
        updates["messages"].append("사전 테스트 체크 스킵 (커맨드 없음)")

    updates["current_step"] = "사전 체크 완료"
    return updates


def build_node(state: AutoPipeState) -> dict:
    """빌드 실행 (tool executor)"""
    config = PipelineConfig(state["config_path"])

    # 노드 설정에서 command 가져오기, 없으면 프로젝트 빌드 커맨드
    node_cfg = config.nodes.get("build", {})
    test_cfg = config.nodes.get("run_tests", {})
    command = node_cfg.get("command", "") or config.build_command
    test_cmd = test_cfg.get("command", "") or config.test_command

    # 빌드/테스트 분리 실행이므로 빌드에서 테스트 제외
    command = _build_only_command(command, test_cmd)
    if not command:
        return {
            "build_result": "success",
            "build_log": "빌드 커맨드 없음 — 스킵",
            "current_step": "빌드 스킵",
            "progress": 50,
            "messages": ["빌드 커맨드 없음 — 스킵"],
        }

    build_timeout = node_cfg.get("timeout", 300)
    executor = create_executor("tool")
    _emit_log(f"Phase 3: 빌드 실행 — {command} (타임아웃: {build_timeout}초)")
    result = executor.run(command, cwd=state.get("project_path", ""), timeout=build_timeout)

    _emit_log(f"Phase 3: 빌드 {'성공' if result.success else '실패'}")
    if not result.success:
        # 빌드 에러 로그 출력 (마지막 50줄)
        error_lines = result.output.strip().split("\n")[-50:]
        _emit_log("── 빌드 에러 로그 ──")
        for line in error_lines:
            _emit_log(line)
        _emit_log("── 빌드 에러 끝 ──")
    return {
        "build_result": "success" if result.success else "fail",
        "build_log": result.output,
        "current_phase": "build_test",
        "current_step": f"빌드 {'성공' if result.success else '실패'}",
        "progress": 50,
        "messages": [f"빌드 {'성공' if result.success else '실패'} ({result.duration_sec:.0f}초)"],
    }


def run_tests_node(state: AutoPipeState) -> dict:
    """테스트 실행 (tool executor)"""
    # 빌드 실패 시 테스트 스킵
    if state.get("build_result") == "fail":
        return {
            "test_result": "fail",
            "test_log": "빌드 실패로 테스트 스킵",
            "test_errors": ["빌드 실패"],
            "messages": ["빌드 실패로 테스트 스킵"],
        }

    config = PipelineConfig(state["config_path"])
    node_cfg = config.nodes.get("run_tests", {})
    command = node_cfg.get("command", "") or config.test_command
    if not command:
        return {
            "test_result": "pass",
            "test_log": "테스트 커맨드 없음 — 스킵",
            "test_errors": [],
            "current_step": "테스트 스킵",
            "progress": 60,
            "messages": ["테스트 커맨드 없음 — 스킵"],
        }

    test_timeout = node_cfg.get("timeout", 300)
    executor = create_executor("tool")
    _emit_log(f"Phase 3: 테스트 실행 — {command} (타임아웃: {test_timeout}초)")
    result = executor.run(command, cwd=state.get("project_path", ""), timeout=test_timeout)

    errors = []
    if not result.success:
        # 에러 로그에서 실패 라인 추출
        for line in result.output.split("\n"):
            if any(kw in line.lower() for kw in ["fail", "error", "assert"]):
                errors.append(line.strip())
        if not errors:
            errors = [result.error or "테스트 실패"]

    _emit_log(f"Phase 3: 테스트 {'통과' if result.success else f'실패 ({len(errors)}건)'}")
    if not result.success:
        _emit_log("── 테스트 에러 로그 ──")
        for e in errors[:20]:
            _emit_log(e)
        _emit_log("── 테스트 에러 끝 ──")
    return {
        "test_result": "pass" if result.success else "fail",
        "test_log": result.output,
        "test_errors": errors,
        "current_step": f"테스트 {'통과' if result.success else '실패'}",
        "progress": 60,
        "messages": [f"테스트 {'통과' if result.success else f'실패 ({len(errors)}건)'} ({result.duration_sec:.0f}초)"],
    }


def _is_pre_existing_error(state: AutoPipeState) -> bool:
    """현재 빌드/테스트 에러가 사전 체크 에러와 동일한지 판별"""
    # 빌드 에러 비교
    if state.get("build_result") == "fail" and state.get("pre_build_result") == "fail":
        pre_errors = state.get("pre_build_errors", "")
        build_log = state.get("build_log", "")
        if _match_errors(pre_errors, build_log):
            return True

    # 테스트 에러 비교
    if state.get("test_result") == "fail" and state.get("pre_test_result") == "fail":
        pre_errors = state.get("pre_test_errors", "")
        test_log = state.get("test_log", "")
        if _match_errors(pre_errors, test_log):
            return True

    return False


def _match_errors(pre_errors: str, current_log: str) -> bool:
    """사전 에러와 현재 로그 비교 — 80% 이상 일치하면 기존 에러"""
    if not pre_errors:
        return False
    pre_lines = [l.strip() for l in pre_errors.split("\n") if l.strip()]
    if not pre_lines:
        return False
    match_count = sum(1 for line in pre_lines if line in current_log)
    return match_count >= len(pre_lines) * 0.8


def check_test_result(state: AutoPipeState) -> Literal["pass", "fail", "max_retries"]:
    """테스트 결과에 따라 분기"""
    if state.get("test_result") == "pass":
        return "pass"

    # 사전 체크 에러와 동일하면 fix 루프 스킵
    if _is_pre_existing_error(state):
        _emit_log("⚠️ 에러가 파이프라인 시작 전부터 존재하던 기존 에러입니다 — fix 루프 스킵")
        return "max_retries"

    if state.get("fix_iteration", 0) >= state.get("max_fix_iterations", 5):
        return "max_retries"
    return "fail"


def fix_code_node(state: AutoPipeState) -> dict:
    """테스트 실패 시 코드 수정 (console/api executor)"""
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("fix_code")
        template = config.get_prompt_template("fix_code")
    except ValueError:
        executor = config.get_executor("develop_code")
        template = ""

    if not template:
        template = """# 코드 수정 (반복 #{iteration})

다음 에러를 수정해주세요.

## 설계서
{design_spec}

## 현재 코드
{source_code}

## 에러 내용
{test_errors}

## 빌드 로그
{build_log}

## 규칙
- 에러가 발생한 파일만 수정
- 파일별로 `=== FILE: 경로 ===` 형식으로 구분
"""

    # 통합 설계서 사용 (없으면 개별 설계서 조합 — 하위 호환)
    design = state.get("design_spec", "")
    if not design:
        design = f"""## API 설계
{state.get('api_spec', '')}

## DB 스키마
{state.get('db_schema', '')}

## UI 설계
{state.get('ui_spec', '')}"""

    iteration = state.get("fix_iteration", 0) + 1
    prompt = render_prompt(template, {
        "design_spec": design,
        "source_code": format_source_code(state.get("source_code", {})),
        "test_errors": "\n".join(state.get("test_errors", [])),
        "build_log": state.get("build_log", "")[:2000],
        "iteration": str(iteration),
        "requirements": state.get("requirements", ""),
        "api_spec": state.get("api_spec", ""),
        "db_schema": state.get("db_schema", ""),
        "ui_spec": state.get("ui_spec", ""),
    })

    _emit_log(f"Phase 3: 코드 수정 #{iteration}")
    result = executor.run(
        prompt,
        project_path=state.get("project_path", ""),
        on_output=_emit_log,
    )

    if not result.success:
        return {
            "fix_iteration": iteration,
            "errors": [f"코드 수정 실패: {result.error}"],
        }

    updated_code = parse_code_output(result.output)
    merged = {**state.get("source_code", {}), **updated_code}

    _emit_log(f"Phase 3: 코드 수정 완료 ({len(updated_code)}개 파일)")
    return {
        "source_code": merged,
        "fix_iteration": iteration,
        "current_step": f"코드 수정 #{iteration} 완료",
        "messages": [f"코드 수정 #{iteration} ({len(updated_code)}개 파일)"],
    }
