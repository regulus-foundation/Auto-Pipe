"""프로젝트 분석기

Phase 1: 파일 기반 빠른 스캔 (구조, 언어, 프레임워크, 빌드, 인프라)
Phase 2: LLM 다단계 Deep Analysis
  - Step 1: 의존성 & 빌드 분석 (빌드 파일 전체 읽기)
  - Step 2: 아키텍처 & 코드 패턴 분석 (레이어별 대표 파일)
  - Step 3: 테스트 전략 분석 (테스트 코드 + 소스 대비)
  - Step 4: 종합 평가 & Auto-Pipe 설정 가이드
"""

import os
import re
import json
from pathlib import Path
from collections import Counter

# ──────────────────────────────────────────
# 상수
# ──────────────────────────────────────────

IGNORE_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "vendor", "venv", ".venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    "build", "dist", "out", "target", ".gradle",
    ".idea", ".vscode", ".settings",
    ".next", ".nuxt", ".output",
    "coverage", ".nyc_output",
}

EXT_LANG = {
    ".java": "java", ".kt": "kotlin", ".scala": "scala",
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".cs": "csharp", ".swift": "swift", ".dart": "dart", ".vue": "vue",
    ".sql": "sql",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".yaml": "yaml", ".yml": "yaml",
    ".json": "json", ".xml": "xml",
    ".tf": "terraform", ".proto": "protobuf",
}

# primary 언어 판별에 사용할 프로그래밍/IaC 언어 확장자 (마크업/설정 제외)
PRIMARY_LANG_EXTS = {
    ".java", ".kt", ".scala", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".rb", ".php", ".cs", ".swift", ".dart",
    ".tf",  # Terraform (HCL)
}

SOURCE_EXTS = {".java", ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs",
               ".kt", ".scala", ".rb", ".php", ".cs", ".swift", ".dart", ".vue",
               ".tf", ".tfvars"}  # Terraform도 소스

CONFIG_EXTS = {".yaml", ".yml", ".json", ".xml", ".toml", ".ini", ".cfg", ".properties", ".env"}

# ──────────────────────────────────────────
# 프레임워크/도구 감지 규칙
# ──────────────────────────────────────────

DETECTION_RULES = {
    # ─── Application ───
    "spring-boot": {"files": ["build.gradle", "pom.xml"], "markers": ["spring-boot-starter", "org.springframework.boot"], "language": "java"},
    "nestjs": {"files": ["package.json", "nest-cli.json"], "markers": ["@nestjs/core"], "language": "typescript"},
    "express": {"files": ["package.json"], "markers": ["express"], "language": "javascript"},
    "django": {"files": ["manage.py"], "markers": ["django"], "language": "python"},
    "fastapi": {"files": ["requirements.txt", "pyproject.toml"], "markers": ["fastapi"], "language": "python"},
    "flask": {"files": ["requirements.txt", "pyproject.toml"], "markers": ["flask"], "language": "python"},
    "react": {"files": ["package.json"], "markers": ["react", "react-dom"], "language": "typescript"},
    "vue": {"files": ["package.json"], "markers": ["vue"], "language": "typescript"},
    "nextjs": {"files": ["package.json", "next.config.js", "next.config.mjs", "next.config.ts"], "markers": ["next"], "language": "typescript"},
    "flutter": {"files": ["pubspec.yaml"], "markers": ["flutter"], "language": "dart"},
    # ─── Infrastructure / IaC ───
    "terraform": {"files": ["main.tf", "variables.tf", "provider.tf", "terraform.tf"], "markers": [], "language": "terraform"},
    "helm": {"files": ["Chart.yaml"], "markers": [], "language": "yaml"},
    "kustomize": {"files": ["kustomization.yaml", "kustomization.yml"], "markers": [], "language": "yaml"},
    "ansible": {"files": ["ansible.cfg", "playbook.yml", "site.yml"], "markers": [], "language": "yaml"},
    "argocd": {"files": ["application.yaml", "applicationset.yaml"], "markers": ["argoproj.io"], "language": "yaml"},
}

TEST_FRAMEWORKS = {
    "java": {"junit5": "junit-jupiter", "junit4": "junit:junit", "testng": "testng"},
    "python": {"pytest": "pytest", "unittest": "unittest"},
    "typescript": {"jest": "jest", "vitest": "vitest", "mocha": "mocha"},
    "javascript": {"jest": "jest", "vitest": "vitest", "mocha": "mocha"},
    "go": {"go-test": "testing"},
    "terraform": {"terratest": "terratest"},
}

BUILD_TOOLS = {
    # Application
    "build.gradle": "gradle", "build.gradle.kts": "gradle", "pom.xml": "maven",
    "package.json": "npm", "yarn.lock": "yarn", "pnpm-lock.yaml": "pnpm",
    "requirements.txt": "pip", "pyproject.toml": "poetry/pip", "Pipfile": "pipenv",
    "go.mod": "go", "Cargo.toml": "cargo", "Gemfile": "bundler",
    "pubspec.yaml": "flutter/dart", "Makefile": "make",
    # Infrastructure
    "main.tf": "terraform",
    "Chart.yaml": "helm",
    "kustomization.yaml": "kustomize", "kustomization.yml": "kustomize",
    "ansible.cfg": "ansible",
}


# ──────────────────────────────────────────
# 메인 분석 함수
# ──────────────────────────────────────────

def analyze_project(project_path: str, progress_callback=None) -> dict:
    """프로젝트 전체 분석 (Phase 1 파일스캔 + Phase 2 다단계 LLM 분석)"""
    root = Path(project_path).resolve()
    if not root.is_dir():
        return {"error": f"경로가 존재하지 않습니다: {project_path}"}

    def _p(step, detail="", pct=0):
        if progress_callback:
            progress_callback(step, detail, pct)

    # ── Phase 1: 파일 기반 스캔 ──
    _p("파일 스캔", "디렉토리 구조 스캔 중...", 5)
    structure = _scan_structure(root)

    _p("언어 분석", "언어 비율 계산 중...", 10)
    lang_stats = structure.pop("_lang_stats", {})
    primary_lang_stats = structure.pop("_primary_lang_stats", {})
    languages = {}
    if lang_stats:
        sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)
        # primary는 프로그래밍 언어만으로 판별
        sorted_primary = sorted(primary_lang_stats.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_primary[0][0] if sorted_primary else sorted_langs[0][0]
        languages = {
            "primary": primary,
            "breakdown": {lang: count for lang, count in sorted_langs if count > 0},
        }

    _p("프레임워크 감지", "빌드 파일 분석 중...", 15)
    frameworks = _detect_frameworks(root)
    build = _detect_build(root)

    # 프레임워크 감지 결과로 primary 언어 보정
    # (프레임워크가 명확하면 그 언어가 primary — 파일 카운트보다 정확)
    if frameworks:
        fw_lang = frameworks[0].get("language", "")
        if fw_lang and fw_lang != languages.get("primary", ""):
            languages["primary"] = fw_lang
            languages["primary_source"] = "framework_detection"

    _p("테스트 분석", "테스트 현황 분석 중...", 18)
    primary_lang = languages.get("primary", "")
    testing = _analyze_tests(root, primary_lang, structure)

    _p("인프라 감지", "CI/CD, Docker 등 확인 중...", 20)
    infra = _detect_infra(root)
    conventions = _detect_conventions(root, primary_lang)

    result = {
        "project": {"name": root.name, "path": str(root)},
        "structure": structure,
        "languages": languages,
        "build": build,
        "frameworks": frameworks,
        "testing": testing,
        "infrastructure": infra,
        "conventions": conventions,
    }

    # ── Phase 2: LLM 다단계 Deep Analysis ──
    _p("소스 코드 수집", "분석할 파일 수집 중...", 25)
    collected = _collect_all_files(root, primary_lang)
    result["_sample_files_count"] = sum(len(v) for v in collected.values())

    deep = {}
    if collected:
        deep = _run_deep_analysis(result, collected, _p)

    result["deep_analysis"] = deep
    _p("완료", "분석 완료", 100)
    return result


# ──────────────────────────────────────────
# Phase 1: 파일 기반 스캔 (기존과 동일, 축약)
# ──────────────────────────────────────────

def _scan_structure(root: Path) -> dict:
    total_files = 0; source_files = 0; test_files = 0; config_files = 0
    lang_counter = Counter(); primary_lang_counter = Counter()
    dir_tree = []; total_lines = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        depth = rel_dir.count(os.sep)
        if depth <= 2 and rel_dir != ".":
            dir_tree.append(rel_dir)

        for fname in filenames:
            if fname.startswith("."):
                continue
            total_files += 1
            ext = Path(fname).suffix.lower()
            if ext in EXT_LANG:
                lang_counter[EXT_LANG[ext]] += 1
            # 프로그래밍 언어만 별도 카운트 (primary 판별용)
            if ext in PRIMARY_LANG_EXTS:
                primary_lang_counter[EXT_LANG[ext]] += 1
            fpath = os.path.join(dirpath, fname)
            is_test = _is_test_file(fpath, fname)
            if ext in SOURCE_EXTS:
                if is_test:
                    test_files += 1
                else:
                    source_files += 1
                try:
                    if os.path.getsize(fpath) < 500_000:
                        with open(fpath, "r", errors="ignore") as f:
                            total_lines += sum(1 for _ in f)
                except OSError:
                    pass
            elif ext in CONFIG_EXTS:
                config_files += 1

    module_type = "single"; modules = []
    for sg_name in ["settings.gradle", "settings.gradle.kts"]:
        sg = root / sg_name
        if sg.exists():
            try:
                includes = re.findall(r"include\s*['\"]:([\w-]+)['\"]", sg.read_text(errors="ignore"))
                if includes:
                    module_type = "multi-module"; modules = includes
            except OSError:
                pass
            break

    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(errors="ignore"))
            if "workspaces" in data:
                module_type = "monorepo"
                ws = data["workspaces"]
                modules = ws if isinstance(ws, list) else ws.get("packages", [])
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "type": module_type, "modules": modules,
        "total_files": total_files, "source_files": source_files,
        "test_files": test_files, "config_files": config_files,
        "lines_of_code": total_lines,
        "directories": sorted(dir_tree[:50]),
        "_lang_stats": dict(lang_counter),
        "_primary_lang_stats": dict(primary_lang_counter),
    }


def _is_test_file(fpath: str, fname: str) -> bool:
    lower = fname.lower(); lower_path = fpath.lower()
    if any(p in lower for p in ["test", "spec", "_test.", ".test.", ".spec."]):
        return True
    if any(p in lower_path for p in ["/test/", "/tests/", "/__tests__/", "/spec/"]):
        return True
    return False


def _detect_build(root: Path) -> dict:
    result = {"tool": None, "commands": {}}
    for fname, tool in BUILD_TOOLS.items():
        if (root / fname).exists():
            result["tool"] = tool

            # ─── Application ───
            if tool == "gradle":
                prefix = "./gradlew" if (root / "gradlew").exists() else "gradle"
                result["commands"] = {"build": f"{prefix} build", "test": f"{prefix} test", "clean": f"{prefix} clean"}
                result["wrapper"] = (root / "gradlew").exists()
            elif tool == "maven":
                prefix = "./mvnw" if (root / "mvnw").exists() else "mvn"
                result["commands"] = {"build": f"{prefix} package", "test": f"{prefix} test", "clean": f"{prefix} clean"}
            elif tool in ("npm", "yarn", "pnpm"):
                result["commands"] = {"build": f"{tool} run build", "test": f"{tool} test", "install": f"{tool} install"}
            elif tool in ("pip", "poetry/pip"):
                result["commands"] = {"install": "pip install -r requirements.txt", "test": "pytest"}
            elif tool == "go":
                result["commands"] = {"build": "go build ./...", "test": "go test ./...", "clean": "go clean"}
            elif tool == "cargo":
                result["commands"] = {"build": "cargo build", "test": "cargo test", "clean": "cargo clean"}

            # ─── Infrastructure / IaC ───
            elif tool == "terraform":
                result["commands"] = {"build": "terraform init -backend=false && terraform validate", "test": "terraform plan -no-color -input=false"}
            elif tool == "helm":
                # Chart.yaml 위치에 따라 경로 결정
                chart_dir = "." if (root / "Chart.yaml").exists() else "charts"
                result["commands"] = {"build": f"helm lint {chart_dir}", "test": f"helm template {chart_dir} --dry-run"}
            elif tool == "kustomize":
                result["commands"] = {"build": "kustomize build .", "test": "kubectl apply --dry-run=client -k ."}
            elif tool == "ansible":
                # site.yml 또는 playbook.yml 중 존재하는 것 사용
                playbook = "site.yml" if (root / "site.yml").exists() else "playbook.yml"
                result["commands"] = {"build": "ansible-lint", "test": f"ansible-playbook {playbook} --check --diff"}

            break
    return result


def _detect_frameworks(root: Path) -> list[dict]:
    detected = []; build_contents = {}
    for fname in ["build.gradle", "build.gradle.kts", "pom.xml", "package.json",
                   "requirements.txt", "pyproject.toml", "pubspec.yaml", "go.mod", "Cargo.toml"]:
        fpath = root / fname
        if fpath.exists():
            try:
                build_contents[fname] = fpath.read_text(errors="ignore")
            except OSError:
                pass

    # 인프라 파일도 읽기 (ArgoCD 등 markers 매칭용)
    for fname in ["application.yaml", "applicationset.yaml", "kustomization.yaml"]:
        fpath = root / fname
        if fpath.exists():
            try:
                build_contents[fname] = fpath.read_text(errors="ignore")
            except OSError:
                pass

    all_content = "\n".join(build_contents.values()).lower()
    for framework, rule in DETECTION_RULES.items():
        has_file = any((root / f).exists() for f in rule["files"])
        if not has_file:
            continue
        # markers가 비어있으면 파일 존재만으로 감지 (Terraform, Helm, Ansible 등)
        if not rule["markers"]:
            detected.append({"name": framework, "language": rule["language"], "markers_found": ["(file-based detection)"]})
        else:
            markers_found = [m for m in rule["markers"] if m.lower() in all_content]
            if markers_found:
                detected.append({"name": framework, "language": rule["language"], "markers_found": markers_found})
    return detected


def _analyze_tests(root: Path, primary_lang: str, structure: dict) -> dict:
    result = {
        "has_tests": structure.get("test_files", 0) > 0,
        "test_files": structure.get("test_files", 0),
        "source_files": structure.get("source_files", 0),
        "frameworks": [],
    }
    src = max(structure.get("source_files", 1), 1)
    tst = structure.get("test_files", 0)
    result["estimated_coverage"] = f"~{min(int(tst / src * 100), 100)}%"
    if primary_lang in TEST_FRAMEWORKS:
        all_content = ""
        for fname in ["build.gradle", "build.gradle.kts", "pom.xml", "package.json", "requirements.txt", "pyproject.toml"]:
            fpath = root / fname
            if fpath.exists():
                try:
                    all_content += fpath.read_text(errors="ignore")
                except OSError:
                    pass
        for fw_name, marker in TEST_FRAMEWORKS.get(primary_lang, {}).items():
            if marker.lower() in all_content.lower():
                result["frameworks"].append(fw_name)
    return result


def _detect_infra(root: Path) -> dict:
    result = {
        "docker": (root / "Dockerfile").exists(),
        "docker_compose": (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists(),
        "ci_cd": None, "containerized": False,
    }
    if (root / ".github" / "workflows").is_dir():
        result["ci_cd"] = "github-actions"
    elif (root / ".gitlab-ci.yml").exists():
        result["ci_cd"] = "gitlab-ci"
    elif (root / "Jenkinsfile").exists():
        result["ci_cd"] = "jenkins"
    elif (root / ".circleci").is_dir():
        result["ci_cd"] = "circleci"
    result["containerized"] = result["docker"] or result["docker_compose"]
    envs = []
    for pattern in ["application-*.yml", "application-*.yaml", "application-*.properties", ".env.*"]:
        envs.extend([p.name for p in root.glob(pattern)])
    result["environments"] = envs[:10]
    return result


def _detect_conventions(root: Path, primary_lang: str) -> dict:
    result = {"architecture": "unknown", "layers": []}
    if primary_lang in ("java", "kotlin"):
        layer_dirs = {"controller", "service", "repository", "entity", "dto", "domain", "model", "config", "util", "common"}
        found = set()
        for dirpath, dirnames, _ in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for d in dirnames:
                if d.lower() in layer_dirs:
                    found.add(d.lower())
        if found:
            result["layers"] = sorted(found)
            if {"controller", "service", "repository"} <= found:
                result["architecture"] = "layered"
            elif {"domain", "service"} <= found:
                result["architecture"] = "domain-driven"
    elif primary_lang == "python":
        if (root / "manage.py").exists():
            result["architecture"] = "django-mvt"
        elif any(root.glob("**/routers/*.py")) or any(root.glob("**/routes/*.py")):
            result["architecture"] = "router-based"
    elif primary_lang in ("typescript", "javascript"):
        src = root / "src"
        if src.is_dir():
            subdirs = {d.name.lower() for d in src.iterdir() if d.is_dir()}
            if "modules" in subdirs or "module" in subdirs:
                result["architecture"] = "modular (NestJS-style)"
            elif "components" in subdirs:
                result["architecture"] = "component-based (React-style)"
            elif "routes" in subdirs or "controllers" in subdirs:
                result["architecture"] = "MVC/router-based"
    return result


# ──────────────────────────────────────────
# Phase 2: 파일 수집
# ──────────────────────────────────────────

def _safe_read(fpath: Path, max_lines: int = 300) -> str:
    try:
        with open(fpath, "r", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... (이하 생략, 총 라인 수 초과)")
                    break
                lines.append(line)
            return "".join(lines)
    except (OSError, UnicodeDecodeError):
        return ""


def _collect_all_files(root: Path, primary_lang: str) -> dict:
    """분석에 필요한 파일을 카테고리별로 수집"""

    collected = {
        "build_config": [],     # 빌드/의존성 파일 (전체 읽기)
        "app_config": [],       # 애플리케이션 설정 파일
        "entrypoints": [],      # 엔트리포인트/메인 파일
        "core_source": [],      # 핵심 소스 (레이어별 대표)
        "tests": [],            # 테스트 파일
        "infra": [],            # Docker, CI/CD 설정
    }

    # 1. 빌드/의존성 파일 — 전체 읽기 (가장 중요)
    build_files = [
        "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
        "pom.xml", "package.json", "package-lock.json",
        "requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "setup.cfg",
        "go.mod", "go.sum", "Cargo.toml", "pubspec.yaml",
        "Gemfile", "composer.json",
    ]
    for fname in build_files:
        fpath = root / fname
        if fpath.exists():
            content = _safe_read(fpath, max_lines=500)
            if content:
                collected["build_config"].append({"path": fname, "content": content})

    # 서브모듈 빌드 파일
    for sub_build in root.glob("*/build.gradle*"):
        if any(p in str(sub_build) for p in IGNORE_DIRS):
            continue
        rel = os.path.relpath(sub_build, root)
        content = _safe_read(sub_build, max_lines=300)
        if content:
            collected["build_config"].append({"path": rel, "content": content})

    # 2. 애플리케이션 설정 파일
    config_patterns = [
        "application.yml", "application.yaml", "application.properties",
        "application-*.yml", "application-*.yaml", "application-*.properties",
        ".env", ".env.example", ".env.development",
        "config/*.yml", "config/*.yaml", "config/*.json",
        "nest-cli.json", "tsconfig.json", "next.config.*",
        "webpack.config.*", "vite.config.*",
    ]
    for pattern in config_patterns:
        for fpath in root.glob(pattern):
            if any(p in str(fpath) for p in IGNORE_DIRS):
                continue
            rel = os.path.relpath(fpath, root)
            content = _safe_read(fpath, max_lines=200)
            if content:
                collected["app_config"].append({"path": rel, "content": content})
    # 중복 제거 & 최대 15개
    seen = set()
    deduped = []
    for f in collected["app_config"]:
        if f["path"] not in seen:
            seen.add(f["path"])
            deduped.append(f)
    collected["app_config"] = deduped[:15]

    # 3. 엔트리포인트
    entry_patterns = [
        "**/Application.java", "**/Application.kt",
        "src/main.py", "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
        "src/main.ts", "src/main.js", "src/index.ts", "src/index.js",
        "src/app.ts", "src/app.js", "src/server.ts", "src/server.js",
        "src/App.tsx", "src/App.jsx",
        "cmd/main.go", "main.go",
        "lib/main.dart",
    ]
    for pattern in entry_patterns:
        for fpath in root.glob(pattern):
            if any(p in str(fpath) for p in IGNORE_DIRS):
                continue
            rel = os.path.relpath(fpath, root)
            content = _safe_read(fpath, max_lines=300)
            if content:
                collected["entrypoints"].append({"path": rel, "content": content})
    collected["entrypoints"] = collected["entrypoints"][:5]

    # 4. 핵심 소스 — 레이어/모듈별 대표 파일 (가장 큰 파일 = 로직이 많은 파일)
    layer_keywords = {
        "controller": ["controller", "resource", "endpoint", "handler", "api"],
        "service": ["service", "usecase", "interactor"],
        "repository": ["repository", "dao", "store", "mapper"],
        "model": ["entity", "model", "domain", "schema", "dto"],
        "config": ["config", "configuration", "module"],
        "middleware": ["filter", "interceptor", "middleware", "guard", "pipe"],
        "util": ["util", "helper", "common", "shared"],
    }

    all_sources = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in SOURCE_EXTS:
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(fpath)
            except OSError:
                continue
            if size < 100 or size > 300_000:
                continue
            if _is_test_file(fpath, fname):
                continue
            rel = os.path.relpath(fpath, root)
            all_sources.append({"path": rel, "size": size})

    # 레이어별로 분류 → 각 레이어에서 가장 큰 파일 3개씩
    layer_files = {k: [] for k in layer_keywords}
    uncategorized = []
    for f in all_sources:
        path_lower = f["path"].lower()
        matched = False
        for layer, keywords in layer_keywords.items():
            if any(kw in path_lower for kw in keywords):
                layer_files[layer].append(f)
                matched = True
                break
        if not matched:
            uncategorized.append(f)

    for layer, files in layer_files.items():
        files.sort(key=lambda x: x["size"], reverse=True)
        for f in files[:3]:
            content = _safe_read(root / f["path"], max_lines=300)
            if content:
                collected["core_source"].append({
                    "path": f["path"], "layer": layer, "content": content,
                })

    # 분류 안 된 것 중 크기 큰 것 (핵심 로직일 가능성)
    uncategorized.sort(key=lambda x: x["size"], reverse=True)
    for f in uncategorized[:5]:
        content = _safe_read(root / f["path"], max_lines=300)
        if content:
            collected["core_source"].append({
                "path": f["path"], "layer": "other", "content": content,
            })

    # 5. 테스트 파일
    all_tests = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in SOURCE_EXTS:
                continue
            fpath = os.path.join(dirpath, fname)
            if not _is_test_file(fpath, fname):
                continue
            try:
                size = os.path.getsize(fpath)
            except OSError:
                continue
            if size < 100 or size > 300_000:
                continue
            all_tests.append({"path": os.path.relpath(fpath, root), "size": size})

    all_tests.sort(key=lambda x: x["size"], reverse=True)
    for f in all_tests[:5]:
        content = _safe_read(root / f["path"], max_lines=250)
        if content:
            collected["tests"].append({"path": f["path"], "content": content})

    # 6. 인프라 파일
    infra_files = [
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        ".github/workflows/*.yml", ".github/workflows/*.yaml",
        "Jenkinsfile", ".gitlab-ci.yml",
        "k8s/*.yaml", "k8s/*.yml", "helm/**/values.yaml",
        "terraform/*.tf",
    ]
    for pattern in infra_files:
        if "*" in pattern:
            for fpath in root.glob(pattern):
                rel = os.path.relpath(fpath, root)
                content = _safe_read(fpath, max_lines=200)
                if content:
                    collected["infra"].append({"path": rel, "content": content})
        else:
            fpath = root / pattern
            if fpath.exists():
                content = _safe_read(fpath, max_lines=200)
                if content:
                    collected["infra"].append({"path": pattern, "content": content})
    collected["infra"] = collected["infra"][:10]

    return collected


# ──────────────────────────────────────────
# Phase 2: 다단계 LLM Deep Analysis
# ──────────────────────────────────────────

def _format_files(files: list[dict]) -> str:
    """파일 리스트를 프롬프트용 텍스트로 변환"""
    parts = []
    for f in files:
        label = f.get("layer", f.get("type", ""))
        header = f"[{label.upper()}] {f['path']}" if label else f['path']
        parts.append(f"\n{'='*60}\n{header}\n{'='*60}\n{f['content']}")
    return "\n".join(parts)


def _run_deep_analysis(scan_result: dict, collected: dict, progress_fn) -> dict:
    """4단계 LLM 분석"""
    try:
        from core.executor import create_executor
    except ImportError:
        return {"error": "executor 모듈 로드 실패"}

    executor = create_executor("api", model=os.getenv("AUTO_PIPE_MODEL", "gpt-4o-mini"))

    project = scan_result.get("project", {})
    languages = scan_result.get("languages", {})
    frameworks = scan_result.get("frameworks", [])
    structure = scan_result.get("structure", {})
    fw_names = ", ".join(fw["name"] for fw in frameworks) if frameworks else "unknown"

    project_summary = f"""프로젝트: {project.get("name", "unknown")}
언어: {languages.get("primary", "unknown")} (소스 {structure.get("source_files", 0)}개, 테스트 {structure.get("test_files", 0)}개, {structure.get("lines_of_code", 0):,}줄)
프레임워크: {fw_names}
빌드: {scan_result.get("build", {}).get("tool", "unknown")}"""

    deep_result = {
        "steps": {},
        "total_tokens": 0,
        "total_duration": 0,
        "files_analyzed": sum(len(v) for v in collected.values()),
    }

    # ── Step 1: 의존성 & 빌드 구조 분석 ──
    if collected["build_config"]:
        progress_fn("Step 1/4", "의존성 & 빌드 구조 분석 중...", 30)

        prompt = f"""당신은 시니어 소프트웨어 아키텍트입니다. 아래 프로젝트의 빌드/의존성 파일을 분석하세요.

## 프로젝트 정보
{project_summary}

## 빌드/의존성 파일
{_format_files(collected["build_config"])}

{_format_files(collected["app_config"][:5]) if collected["app_config"] else ""}

## 분석 요청 (한국어로 작성)

### 1. 의존성 분석
- 핵심 의존성 목록과 각각의 역할/용도
- 의존성 버전 상태 (최신 여부, 보안 이슈 가능성)
- 불필요하거나 중복되는 의존성

### 2. 빌드 구조
- 빌드 설정의 특이사항
- 멀티모듈이면 모듈 간 의존 관계
- 프로파일/환경 설정 구조

### 3. 외부 연동
- 설정 파일에서 확인되는 DB, 캐시, 메시지큐, 외부 API 등
- 환경별 설정 차이

구체적 파일명과 라인을 근거로 제시하세요."""

        r = executor.run(prompt)
        deep_result["steps"]["dependencies"] = r.output if r.success else f"분석 실패: {r.error}"
        deep_result["total_tokens"] += r.tokens_used
        deep_result["total_duration"] += r.duration_sec

    # ── Step 2: 아키텍처 & 코드 패턴 분석 ──
    if collected["core_source"]:
        progress_fn("Step 2/4", f"아키텍처 & 코드 패턴 분석 중... ({len(collected['core_source'])}개 파일)", 50)

        prompt = f"""당신은 시니어 소프트웨어 아키텍트입니다. 아래 프로젝트의 핵심 소스 코드를 분석하세요.

## 프로젝트 정보
{project_summary}

## 엔트리포인트
{_format_files(collected["entrypoints"])}

## 핵심 소스 코드 (레이어별 대표)
{_format_files(collected["core_source"])}

## 분석 요청 (한국어로 작성)

### 1. 아키텍처 패턴
- 사용 중인 아키텍처 패턴 (layered, hexagonal, clean, MVC 등)
- 레이어 간 의존 방향과 데이터 흐름
- 관심사 분리 수준 평가

### 2. 코드 컨벤션 (매우 구체적으로)
- 네이밍 규칙: 클래스, 메서드, 변수, 패키지/모듈 (실제 예시 포함)
- DI(의존성 주입) 패턴 (constructor, field, setter 등)
- 응답 래퍼/공통 패턴 (ApiResponse, BaseEntity 등)
- 예외 처리 방식 (글로벌 핸들러, per-method 등)
- 검증/유효성 검사 방식

### 3. 코드 품질
- 잘 된 점 (강점 3개 이상)
- 개선 필요한 점 (약점 3개 이상)
- 보안 우려사항
- SOLID 원칙 준수 여부

### 4. 코드 생성 시 반드시 따라야 할 규칙
- 이 프로젝트에 새 코드를 추가할 때 꼭 지켜야 할 패턴/규칙을 구체적으로 나열
- 절대 하면 안 되는 것 (anti-pattern)

구체적 파일명, 클래스명, 메서드명을 근거로 제시하세요."""

        r = executor.run(prompt)
        deep_result["steps"]["architecture"] = r.output if r.success else f"분석 실패: {r.error}"
        deep_result["total_tokens"] += r.tokens_used
        deep_result["total_duration"] += r.duration_sec

    # ── Step 3: 테스트 전략 분석 ──
    progress_fn("Step 3/4", "테스트 전략 분석 중...", 70)

    test_section = ""
    if collected["tests"]:
        test_section = f"""## 기존 테스트 코드
{_format_files(collected["tests"])}"""
    else:
        test_section = "## 기존 테스트 코드\n(테스트 파일이 없거나 감지되지 않음)"

    prompt = f"""당신은 시니어 QA 엔지니어입니다. 아래 프로젝트의 테스트 전략을 분석하고 개선안을 제시하세요.

## 프로젝트 정보
{project_summary}
테스트 파일: {structure.get("test_files", 0)}개 / 소스 파일: {structure.get("source_files", 0)}개

{test_section}

## 핵심 소스 코드 (테스트 대상)
{_format_files(collected["core_source"][:5]) if collected["core_source"] else "(없음)"}

## 분석 요청 (한국어로 작성)

### 1. 현재 테스트 평가
- 테스트 커버리지 수준 평가 (어느 레이어가 부족한지)
- 테스트 코드 품질 (mocking, assertion, fixture 패턴)
- 테스트 네이밍/구조 규칙

### 2. 테스트 부족 영역
- 테스트가 없거나 부족한 구체적 영역/클래스
- 우선적으로 테스트를 추가해야 할 곳 (리스크 순)

### 3. 추천 테스트 전략
- 단위/통합/E2E 각각의 추천 프레임워크와 설정
- 이 프로젝트에 맞는 테스트 DB 전략 (H2, Testcontainers, mock 등)
- 테스트 작성 시 따라야 할 규칙/패턴"""

    r = executor.run(prompt)
    deep_result["steps"]["testing"] = r.output if r.success else f"분석 실패: {r.error}"
    deep_result["total_tokens"] += r.tokens_used
    deep_result["total_duration"] += r.duration_sec

    # ── Step 4: 종합 평가 ──
    progress_fn("Step 4/4", "종합 평가 & Auto-Pipe 가이드 생성 중...", 85)

    infra_section = ""
    if collected["infra"]:
        infra_section = f"""## 인프라 파일
{_format_files(collected["infra"])}"""

    # 이전 3단계 결과를 요약에 포함
    prev_results = ""
    for step_name, step_result in deep_result["steps"].items():
        if isinstance(step_result, str) and len(step_result) > 100:
            prev_results += f"\n### {step_name} 분석 결과 (요약)\n{step_result[:2000]}\n"

    prompt = f"""당신은 시니어 소프트웨어 아키텍트입니다. 지금까지의 분석 결과를 종합하여 최종 평가를 작성하세요.

## 프로젝트 정보
{project_summary}

{infra_section}

## 이전 분석 결과
{prev_results}

## 종합 평가 요청 (한국어로 작성)

### 1. 프로젝트 성숙도 평가
- 전체 점수 (10점 만점)와 근거
- 강점 TOP 3
- 개선 필요 TOP 3

### 2. 인프라 & DevOps 평가
- CI/CD 파이프라인 상태
- 컨테이너화 수준
- 배포 전략

### 3. Auto-Pipe 활용 가이드
- 이 프로젝트에서 Auto-Pipe가 코드를 생성할 때:
  a) 반드시 따라야 할 패턴 (구체적 규칙 5개 이상)
  b) 파일 생성 위치 규칙 (패키지/디렉토리 구조)
  c) 네이밍 규칙 요약
  d) import/의존성 주입 규칙
  e) 에러 처리 규칙
  f) 테스트 작성 규칙

### 4. 추천 개발 순서
- 이 프로젝트에 새 기능을 추가한다면 어떤 순서로 개발하는 것이 가장 효율적인지
- 각 단계에서 생성해야 할 파일 목록"""

    r = executor.run(prompt)
    deep_result["steps"]["summary"] = r.output if r.success else f"분석 실패: {r.error}"
    deep_result["total_tokens"] += r.tokens_used
    deep_result["total_duration"] += r.duration_sec

    return deep_result
