# Project Bootstrap Pipeline -- LangGraph Design

One-time pipeline that analyzes a project path and generates Auto-Pipe configuration.
After Bootstrap, only `AUTO_PIPE_DESIGN.md` pipeline runs repeatedly.

---

## 1. Overall Flow (Current Implementation)

```
Project path input (e.g. /path/to/my-project)
     |
     v
+--------------------------------------------------------------+
|  Phase B1. File Scan (tool -- local, free)                    |
|                                                               |
|  core/analyzer.py functions:                                  |
|    _scan_structure   --> file counts, language stats           |
|    _detect_frameworks --> spring-boot, nestjs, terraform, etc  |
|    _detect_build     --> build/test commands                   |
|    _analyze_tests    --> test framework detection              |
|    _detect_infra     --> CI/CD, Docker                        |
|    _detect_conventions --> architecture, layers                |
|    _collect_all_files --> categorized file list for LLM        |
|                                                               |
|  Output: scan_result + collected_files                        |
+------------------------------+--------------------------------+
                               |
                               v
+--------------------------------------------------------------+
|  Phase B2. Deep Analysis (console -- 4 sequential steps)      |
|                                                               |
|  Step 1: analyze_deps    --> Dependencies & build analysis    |
|  Step 2: analyze_arch    --> Architecture & code patterns     |
|  Step 3: analyze_tests   --> Test strategy analysis           |
|  Step 4: analyze_summary --> Overall assessment +             |
|                              Auto-Pipe usage guide            |
|                                                               |
|  Each step: Claude CLI reads project files directly           |
|  Output: deep_analysis.steps (4 markdown documents)           |
+------------------------------+--------------------------------+
                               |
                               v
              [Human Review] -- interrupt_before
              "Review analysis results"
                               |
                               v
+--------------------------------------------------------------+
|  Phase B3. Config Generator (api -- lightweight)              |
|                                                               |
|  core/config_generator.py:                                    |
|    generate_config(scan_result, output_dir, deep_analysis)    |
|                                                               |
|  Generates:                                                   |
|    1. pipeline.yaml      (node config, executor selection)    |
|    2. prompts/*.md       (project context + Deep Analysis     |
|                           results injected)                   |
|    3. project_analysis.yaml (scan results preserved)          |
|    4. analysis/*.md      (deep analysis documents saved)      |
|                                                               |
+------------------------------+--------------------------------+
                               |
                               v
     Output: projects/{name}/
             +-- project_analysis.yaml
             +-- pipeline.yaml
             +-- prompts/
             |   +-- analyze_requirements.md
             |   +-- generate_design.md
             |   +-- develop_code.md
             |   +-- write_tests.md
             |   +-- code_review.md
             |   +-- generate_docs.md
             +-- analysis/
                 +-- 01_dependencies.md
                 +-- 02_architecture.md
                 +-- 03_testing.md
                 +-- 04_summary.md
                 +-- meta.json
```

---

## 2. Supported Project Types

### Application Detection

| Type | Detection Files | Markers | Language | Build | Test |
|------|----------------|---------|----------|-------|------|
| Spring Boot | build.gradle, pom.xml | spring-boot-starter | java | ./gradlew build | ./gradlew test |
| NestJS | package.json, nest-cli.json | @nestjs/core | typescript | npm run build | npm test |
| Express | package.json | express | javascript | npm run build | npm test |
| Django | manage.py | django | python | pip install | pytest |
| FastAPI | requirements.txt | fastapi | python | pip install | pytest |
| Flask | requirements.txt | flask | python | pip install | pytest |
| React | package.json | react, react-dom | typescript | npm run build | npm test |
| Vue | package.json | vue | typescript | npm run build | npm test |
| Next.js | package.json, next.config.* | next | typescript | npm run build | npm test |
| Flutter | pubspec.yaml | flutter | dart | flutter build | flutter test |

### Infrastructure / IaC Detection

| Type | Detection Files | Markers | Build (validate) | Test (dry-run) |
|------|----------------|---------|-------------------|----------------|
| Terraform | main.tf, variables.tf, provider.tf | (file-based) | terraform validate | terraform plan |
| Helm | Chart.yaml | (file-based) | helm lint | helm template --dry-run |
| Kustomize | kustomization.yaml | (file-based) | kustomize build | kubectl --dry-run |
| Ansible | ansible.cfg, site.yml, playbook.yml | (file-based) | ansible-lint | ansible-playbook --check |
| ArgoCD | application.yaml | argoproj.io | -- | -- |

### Language Detection Priority

1. **Programming languages only** for primary detection (.java, .py, .js, .ts, .go, .rs, .tf, etc.)
   - Excludes markup/config (.html, .css, .json, .yaml, .xml, .sql)
2. **Framework-based override** -- if Spring Boot detected, primary = java regardless of file count

---

## 3. State Definition (Current)

```python
class BootstrapState(TypedDict):
    project_path: str                           # Project root path

    # Phase B1: File scan result
    scan_result: dict                           # analyzer.py Phase 1 output
    collected_files: dict                       # Categorized files for LLM

    # Phase B2: Deep Analysis (console)
    deep_analysis: dict                         # 4-step LLM analysis results
    # deep_analysis = {
    #   "steps": {
    #     "dependencies": "...",   # Step 1 output
    #     "architecture": "...",   # Step 2 output
    #     "testing": "...",        # Step 3 output
    #     "summary": "...",        # Step 4 output
    #   },
    #   "total_tokens": int,
    #   "total_duration": float,
    #   "files_analyzed": int,
    # }

    # Human Review
    analysis_approved: bool

    # Phase B3: Config generation
    gen_result: dict                            # Generated file info

    # Meta
    steps: Annotated[list[str], operator.add]   # Progress log
    current_step: str
    progress: int                               # 0~100
    errors: list[str]
```

---

## 4. Graph Structure (Current)

```python
def build_bootstrap_graph():
    graph = StateGraph(BootstrapState)

    graph.add_node("scan_files", scan_files_node)         # tool: local scan
    graph.add_node("analyze_deps", analyze_deps_node)     # console: Step 1/4
    graph.add_node("analyze_arch", analyze_arch_node)     # console: Step 2/4
    graph.add_node("analyze_tests", analyze_tests_node)   # console: Step 3/4
    graph.add_node("analyze_summary", analyze_summary_node) # console: Step 4/4
    graph.add_node("generate_config", generate_config_node) # api: config gen
    graph.add_node("done", write_done_node)

    # Sequential flow
    graph.set_entry_point("scan_files")
    graph.add_edge("scan_files", "analyze_deps")
    graph.add_edge("analyze_deps", "analyze_arch")
    graph.add_edge("analyze_arch", "analyze_tests")
    graph.add_edge("analyze_tests", "analyze_summary")
    graph.add_edge("analyze_summary", "generate_config")
    graph.add_edge("generate_config", "done")
    graph.add_edge("done", END)

    return graph.compile(
        interrupt_before=["generate_config"],  # Human review point
        checkpointer=MemorySaver(),
    )
```

```
[Bootstrap Graph]

scan_files (tool)
    |
    v
analyze_deps (console) -- Step 1/4: Dependencies & build
    |
    v
analyze_arch (console) -- Step 2/4: Architecture & code patterns
    |
    v
analyze_tests (console) -- Step 3/4: Test strategy
    |
    v
analyze_summary (console) -- Step 4/4: Overall + code gen rules
    |
    v
[Human Review] -- interrupt_before
    |
    v
generate_config (api) -- pipeline.yaml + prompts (Deep Analysis injected)
    |
    v
done
    |
    v
END
```

---

## 5. Key Design Decisions

### 5.1 Deep Analysis -> Prompt Templates

The 4-step Deep Analysis results are injected into prompt templates during config generation:

- **Architecture analysis** -> `develop_code.md`, `generate_design.md`, `code_review.md`
- **Test strategy** -> `write_tests.md`
- **Summary / code gen rules** -> `develop_code.md`, `analyze_requirements.md`

This ensures that when the pipeline runs, LLM prompts contain project-specific conventions,
patterns, and rules discovered during Bootstrap.

### 5.2 File Collection Strategy

`_collect_all_files()` categorizes project files for the Console executor:

| Category | Purpose | Files |
|----------|---------|-------|
| `build_config` | Dependencies & build | build.gradle, package.json, etc. |
| `app_config` | Application settings | application.yml, .env, etc. |
| `entrypoints` | Main entry files | Application.java, main.ts, etc. |
| `core_source` | Representative source | Top files per layer |
| `tests` | Existing test code | Test files |
| `infra` | Infrastructure | Dockerfile, docker-compose, CI configs |

### 5.3 Console Executor for Deep Analysis

Console (Claude CLI) is used for all 4 analysis steps because:
- Needs to read hundreds of source files
- API would cost thousands of tokens per file
- Subscription makes unlimited reading free
- Project path is passed to CLI for direct file access

---

## 6. Output Structure

```
projects/{name}/
+-- project_analysis.yaml     # Structured scan results (languages, frameworks, build)
+-- pipeline.yaml             # Pipeline config (executor per node, commands, cycles)
+-- prompts/                  # Project-specific prompt templates
|   +-- analyze_requirements.md   # With project context + Deep Analysis
|   +-- generate_design.md
|   +-- develop_code.md           # Includes architecture rules, conventions
|   +-- write_tests.md            # Includes test strategy from Deep Analysis
|   +-- code_review.md
|   +-- generate_docs.md
+-- analysis/                 # Deep Analysis documents (human-readable)
|   +-- 01_dependencies.md
|   +-- 02_architecture.md
|   +-- 03_testing.md
|   +-- 04_summary.md
|   +-- meta.json             # Analysis metadata (duration, tokens, file count)
+-- log/                      # Execution logs (created during pipeline runs)
+-- output/                   # Generated artifacts (created during pipeline runs)
```

---

## 7. Web UI Integration

Bootstrap page (`web/pages/bootstrap.py`) phases:

```
input -> analyzing -> review -> generating -> done

[input]     Project path input + existing project list
[analyzing] LangGraph streaming with live log display
[review]    Analysis results with metric cards and tabs
[generating] Config generation (after Human approval)
[done]      Generated files summary + link to Pipeline page
```

File logger (`core/file_logger.py`) creates:
`projects/{name}/log/bootstrap-{YYYYMMDD_HHmmss}.log`
