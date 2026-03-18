"""분석 결과를 기반으로 Auto-Pipe 설정 파일을 생성"""

import os
import yaml
from pathlib import Path


def generate_config(analysis: dict, output_dir: str, deep_analysis: dict = None) -> dict:
    """분석 결과로 pipeline.yaml + 프롬프트 템플릿 생성 → output_dir에 저장"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "prompts").mkdir(exist_ok=True)

    # 1. project_analysis.yaml 저장
    analysis_path = out / "project_analysis.yaml"
    with open(analysis_path, "w", encoding="utf-8") as f:
        yaml.dump(analysis, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # 2. pipeline.yaml 생성
    pipeline = _build_pipeline_config(analysis)
    pipeline_path = out / "pipeline.yaml"
    with open(pipeline_path, "w", encoding="utf-8") as f:
        yaml.dump(pipeline, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # 3. 프롬프트 템플릿 생성 (Deep Analysis 결과 반영)
    prompts = _build_prompt_templates(analysis, deep_analysis)
    for name, content in prompts.items():
        prompt_path = out / "prompts" / f"{name}.md"
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "output_dir": str(out),
        "files": {
            "analysis": str(analysis_path),
            "pipeline": str(pipeline_path),
            "prompts": [f"{name}.md" for name in prompts],
        },
    }


def _build_pipeline_config(analysis: dict) -> dict:
    """pipeline.yaml 내용 생성"""
    project = analysis.get("project", {})
    languages = analysis.get("languages", {})
    build = analysis.get("build", {})
    frameworks = analysis.get("frameworks", [])
    primary_fw = frameworks[0]["name"] if frameworks else "unknown"

    return {
        "project": {
            "name": project.get("name", "unknown"),
            "path": project.get("path", ""),
            "language": languages.get("primary", "unknown"),
            "framework": primary_fw,
            "build_command": build.get("commands", {}).get("build", ""),
            "test_command": build.get("commands", {}).get("test", ""),
        },
        "nodes": {
            # Phase 1: 설계
            "analyze_requirements": {
                "executor": "api",
                "prompt_template": "prompts/analyze_requirements.md",
            },
            "generate_design": {
                "executor": "console",
                "prompt_template": "prompts/generate_design.md",
            },
            # Phase 2: 개발
            "develop_code": {
                "executor": "console",
                "prompt_template": "prompts/develop_code.md",
            },
            "write_tests": {
                "executor": "console",
                "prompt_template": "prompts/write_tests.md",
            },
            # Phase 3: 빌드/테스트
            "build": {
                "executor": "tool",
                "command": build.get("commands", {}).get("build", "echo 'no build command'"),
            },
            "run_tests": {
                "executor": "tool",
                "command": build.get("commands", {}).get("test", "echo 'no test command'"),
            },
            "fix_code": {
                "executor": "console",
                "prompt_template": "prompts/develop_code.md",
            },
            # Phase 4: 리뷰
            "code_review": {
                "executor": "api",
                "prompt_template": "prompts/code_review.md",
            },
            "review_quality": {
                "executor": "api",
                "prompt_template": "prompts/code_review.md",
            },
            "review_security": {
                "executor": "api",
                "prompt_template": "prompts/code_review.md",
            },
            "apply_review_fixes": {
                "executor": "console",
                "prompt_template": "prompts/develop_code.md",
            },
            # Phase 5: 문서
            "generate_docs": {
                "executor": "api",
                "prompt_template": "prompts/generate_docs.md",
            },
            "generate_api_doc": {
                "executor": "api",
                "prompt_template": "prompts/generate_docs.md",
            },
            "generate_ops_manual": {
                "executor": "api",
                "prompt_template": "prompts/generate_docs.md",
            },
            "generate_changelog": {
                "executor": "api",
                "prompt_template": "prompts/generate_docs.md",
            },
        },
        "cycles": {
            "build_test": {"max_retries": 5},
            "code_review": {"max_retries": 3},
        },
        "human_checkpoints": [
            {"after": "generate_design"},
            {"after": "code_review"},
        ],
    }


def _build_prompt_templates(analysis: dict, deep_analysis: dict = None) -> dict[str, str]:
    """프로젝트 맞춤 프롬프트 템플릿 생성 (Deep Analysis 결과 반영)"""
    project = analysis.get("project", {})
    languages = analysis.get("languages", {})
    frameworks = analysis.get("frameworks", [])
    conventions = analysis.get("conventions", {})
    testing = analysis.get("testing", {})

    primary_lang = languages.get("primary", "unknown")
    primary_fw = frameworks[0]["name"] if frameworks else "unknown"
    arch = conventions.get("architecture", "unknown")
    layers = ", ".join(conventions.get("layers", [])) or "N/A"
    test_fws = ", ".join(testing.get("frameworks", [])) or "N/A"

    ctx = f"""## 프로젝트 컨텍스트
- 프로젝트: {project.get('name', 'unknown')}
- 언어: {primary_lang}
- 프레임워크: {primary_fw}
- 아키텍처: {arch}
- 레이어: {layers}
- 테스트 프레임워크: {test_fws}
"""

    # Deep Analysis 결과에서 핵심 정보 추출
    deep_ctx = ""
    if deep_analysis and deep_analysis.get("steps"):
        steps = deep_analysis["steps"]

        # 아키텍처 분석 결과 (코드 컨벤션, 패턴 등)
        arch_analysis = steps.get("architecture", "")
        if arch_analysis:
            # 최대 3000자 (프롬프트 크기 제한)
            deep_ctx += f"\n## Deep Analysis: 아키텍처 & 코드 패턴\n{arch_analysis[:3000]}\n"

        # 종합 평가 (Auto-Pipe 활용 가이드 포함)
        summary = steps.get("summary", "")
        if summary:
            deep_ctx += f"\n## Deep Analysis: 종합 평가 & 코드 생성 규칙\n{summary[:3000]}\n"

    # 테스트 분석 결과
    deep_test_ctx = ""
    if deep_analysis and deep_analysis.get("steps"):
        test_analysis = deep_analysis["steps"].get("testing", "")
        if test_analysis:
            deep_test_ctx = f"\n## Deep Analysis: 테스트 전략\n{test_analysis[:2000]}\n"

    return {
        "analyze_requirements": f"""# 요구사항 분석

{ctx}
{deep_ctx}

## 작업
아래 요구사항을 분석하여 구현에 필요한 항목을 정리하세요:
- 영향받는 레이어/모듈
- 필요한 API 엔드포인트
- DB 스키마 변경 사항
- 주요 비즈니스 로직

## 요구사항
{{requirements}}
""",

        "generate_design": f"""# 요구사항 분석 + 설계 생성

{ctx}
{deep_ctx}

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
- 클래스/모듈 설계 (생성/수정할 파일 목록, 각 파일의 역할)

## 규칙
- 기존 프로젝트의 아키텍처, 네이밍, 패턴을 100% 따를 것
- 기존 코드를 직접 읽고 패턴을 파악한 뒤 설계할 것
- 구체적인 파일 경로, 클래스명, 메서드명까지 명시할 것

## 요구사항
{{requirements}}
""",

        "develop_code": f"""# 코드 개발

{ctx}
{deep_ctx}

## 필수 준수 사항
- 기존 프로젝트 패턴을 100% 따를 것
- 아키텍처 레이어 구조 준수: {layers}
- 프레임워크 컨벤션 준수: {primary_fw}

## 작업
아래 설계서를 기반으로 코드를 구현하세요:

{{design_spec}}
""",

        "write_tests": f"""# 테스트 작성

{ctx}
- 테스트 프레임워크: {test_fws}
{deep_test_ctx}

## 작업
아래 요구사항에 대한 테스트를 작성하세요:
- 단위 테스트 (핵심 비즈니스 로직)
- 통합 테스트 (API 엔드포인트)

{{requirements}}
""",

        "code_review": f"""# 코드 리뷰

{ctx}
{deep_ctx}

## 리뷰 기준
1. 기존 프로젝트 패턴과의 일관성
2. 보안 취약점 (OWASP Top 10)
3. 에러 처리 누락
4. 성능 이슈

## 리뷰 대상 코드
{{code}}
""",

        "generate_docs": f"""# 문서 생성

{ctx}

## 작업
구현된 기능에 대한 문서를 작성하세요:
- API 문서 (엔드포인트, 요청/응답)
- 변경 이력
- 운영 가이드 (필요 시)

## 구현 내용
{{implementation}}
""",
    }
