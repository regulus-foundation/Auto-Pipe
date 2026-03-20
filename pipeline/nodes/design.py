"""Phase 1: 설계 생성 노드

2-step approach:
  Step 1 (API, lightweight): 요구사항 → 관련 코드 경로 추출
  Step 2 (Console, scoped): 해당 경로만 읽고 설계 생성
"""

from pipeline.state import AutoPipeState
from pipeline.utils import render_prompt, _emit_log
from core.config_loader import PipelineConfig


def _extract_relevant_paths(state: AutoPipeState, config: PipelineConfig) -> str:
    """API로 요구사항을 분석해서 관련 코드 경로만 추출 (가볍고 빠름)"""
    from core.executor import create_executor

    # Bootstrap 분석 결과에서 프로젝트 구조 로드
    project_path = state.get("project_path", "")
    config_dir = config._config_path.parent if hasattr(config, '_config_path') else None

    # Deep analysis 프롬프트 템플릿에서 아키텍처 정보 추출
    design_template = ""
    try:
        design_template = config.get_prompt_template("generate_design")
    except (ValueError, Exception):
        pass

    # 아키텍처 정보가 프롬프트에 포함되어 있으면 그걸 활용
    arch_context = ""
    if design_template:
        # 프롬프트에서 "## 작업" 이전까지가 프로젝트 컨텍스트
        marker = "## 작업"
        idx = design_template.find(marker)
        if idx > 0:
            arch_context = design_template[:idx].strip()

    prompt = f"""You are a code path analyzer. Given the project architecture and requirements,
identify ONLY the relevant source code directories and file patterns that need to be read for this task.

## Project Architecture
{arch_context or '(no architecture info available)'}

## Requirements
{state['requirements']}

## Task
List the specific directories and file patterns (glob) that are relevant to this requirement.
Be precise — include only what's needed, not the entire project.

Output format (one per line):
```
src/main/java/com/example/auth/
src/main/java/com/example/config/SecurityConfig.java
src/main/java/com/example/domain/user/
```

Rules:
- Include the relevant domain/module directories
- Include related config files
- Include related entity/repository/service/controller paths
- Include related test directories if they exist
- Do NOT include unrelated modules
- Keep the list focused (typically 3-10 paths)
"""

    api_executor = create_executor("api", model="gpt-4o-mini")
    result = api_executor.run(prompt)

    if result.success and result.output.strip():
        return result.output.strip()
    return ""


def generate_design_node(state: AutoPipeState) -> dict:
    """요구사항 분석 + 통합 설계

    Step 1: API로 관련 경로 추출 (빠름, ~5초)
    Step 2: Console로 해당 경로만 읽고 설계 (스코프 제한, 빠름)
    """
    config = PipelineConfig(state["config_path"])

    try:
        executor = config.get_executor("generate_design")
        template = config.get_prompt_template("generate_design")
    except ValueError:
        from core.executor import create_executor
        executor = create_executor("console")
        template = ""

    # Step 1: 관련 경로 추출 (API — lightweight)
    _emit_log("Phase 1-1: 관련 코드 경로 분석 중 (API)...")
    relevant_paths = _extract_relevant_paths(state, config)

    if relevant_paths:
        _emit_log(f"Phase 1-1: 관련 경로 추출 완료")
        # 경로 정보를 프롬프트에 주입
        scope_instruction = f"""
## 관련 코드 경로 (이 경로들만 집중적으로 읽으세요)
```
{relevant_paths}
```

위 경로의 코드를 읽고 설계하세요. 나머지 경로는 무시해도 됩니다.
"""
    else:
        _emit_log("Phase 1-1: 경로 추출 실패, 전체 프로젝트 스캔으로 폴백")
        scope_instruction = ""

    # Step 2: 설계 생성 (Console — scoped)
    if not template:
        template = """# 요구사항 분석 + 통합 설계

## 요구사항
{requirements}

{scope}

## 작업
프로젝트 코드를 확인하고, 아래를 순서대로 수행하세요:

### 1단계: 요구사항 분석
- 기존 코드를 읽고 영향받는 레이어/모듈 파악
- 필요한 API 엔드포인트 정리
- DB 스키마 변경 사항 파악
- 주요 비즈니스 로직 정리

### 2단계: 상세 설계
- API 설계 (엔드포인트, 요청/응답 스키마, 인증/권한)
- DB 스키마 변경 (테이블, 컬럼, 관계, 마이그레이션)
- 클래스/모듈 설계 (생성/수정할 파일 목록, 각 파일의 역할)

## 규칙
- 기존 프로젝트의 아키텍처, 네이밍, 패턴을 100% 따를 것
- 기존 코드를 직접 읽고 패턴을 파악한 뒤 설계할 것
- 구체적인 파일 경로, 클래스명, 메서드명까지 명시할 것
- **절대로 코드를 작성하거나 파일을 생성/수정하지 말 것 — 설계 문서만 출력할 것**
- **코드 구현은 다음 단계에서 별도로 수행됨**
"""
    else:
        # 기존 템플릿에 scope 삽입 — "## 작업" 앞에 넣기
        marker = "## 작업"
        idx = template.find(marker)
        if idx > 0 and scope_instruction:
            template = template[:idx] + scope_instruction + "\n" + template[idx:]

    prompt = render_prompt(template, {
        "requirements": state["requirements"],
        "analysis_result": state.get("requirements_analysis", ""),
        "scope": scope_instruction,
    })

    _emit_log("Phase 1-2: 설계 생성 시작 (Console, scoped)")
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

    _emit_log(f"Phase 1: 설계 완료 ({result.duration_sec:.0f}초)")
    return {
        "design_spec": result.output,
        "current_phase": "design",
        "current_step": "설계 완료",
        "progress": 20,
        "messages": [f"설계 완료 ({result.duration_sec:.0f}초, 경로 스코핑 {'적용' if relevant_paths else '미적용'})"],
    }
