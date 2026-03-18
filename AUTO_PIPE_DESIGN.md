# Auto-Pipe Development Automation Pipeline -- LangGraph Design

---

## 1. Overall Flow

```
Requirements Input
     |
     v
+--------------------------------------------------------------------+
|  Pre-build Check (tool)                                             |
|  Baseline build + test status before any changes                    |
+-------------------------------+------------------------------------+
                                |
                                v
+--------------------------------------------------------------------+
|  Phase 1. Design                                                    |
|                                                                     |
|  analyze_requirements (api) -> generate_design (console)            |
|                                                                     |
|  Console reads project code directly, generates:                    |
|    - API design (endpoints, request/response)                       |
|    - DB schema changes                                              |
|    - Class/module design (file paths, roles)                        |
|    - UI spec (if applicable)                                        |
+-------------------------------+------------------------------------+
                                |
                                v
                  [Human Review] -- Design approval
                                |
                                v
+--------------------------------------------------------------------+
|  Phase 2. Code Development + Test Writing (Parallel)                |
|                                                                     |
|  +---------------------+       +---------------------+             |
|  | develop_code        |       | write_tests          |             |
|  | (console)           |       | (console)            |             |
|  |                     |       |                      |             |
|  | Implement code      |       | Write test cases     |             |
|  | from design         |       | from requirements    |             |
|  +---------------------+       +---------------------+             |
+-------------------------------+------------------------------------+
                                |
                                v
+--------------------------------------------------------------------+
|  Phase 3. Build + Test (Cycle)                                      |
|                                                                     |
|  build (tool) -> run_tests (tool) -> check_test_result              |
|    ^                                     |                          |
|    |   pre-existing error? --> skip fix loop --> package             |
|    +-- fix_code (console) <-- new error--+                          |
|                                   pass --> Phase 4                   |
|                                                                     |
|  Max fix iterations: 5 (configurable in pipeline.yaml)              |
+-------------------------------+------------------------------------+
                                |
                                v
+--------------------------------------------------------------------+
|  Phase 4. Code Review (Parallel + Human-in-the-Loop)                |
|                                                                     |
|  start_review (gateway)                                             |
|    +-- review_quality (api)    -- code quality review               |
|    +-- review_security (api)   -- security check                    |
|         |                                                           |
|         v                                                           |
|  merge_reviews -> review_decision                                   |
|    [Human Review] -- approve / reject / max_retries                 |
|         |                                                           |
|    rejected --> apply_review_fixes (console) --> start_review        |
+-------------------------------+------------------------------------+
                                |
                                v
+--------------------------------------------------------------------+
|  Phase 5. Documentation (Parallel)                                  |
|                                                                     |
|  start_docs (gateway)                                               |
|    +-- generate_api_doc (api)                                       |
|    +-- generate_ops_manual (api)                                    |
|    +-- generate_changelog (api)                                     |
|         |                                                           |
|         v                                                           |
|  package -> done                                                    |
+--------------------------------------------------------------------+
```

---

## 2. Executor Distribution

| Node | Executor | Reason |
|------|----------|--------|
| pre_build_check | tool | Local command execution |
| analyze_requirements | api | Lightweight text analysis |
| generate_design | **console** | Reads project code directly, bulk output |
| develop_code | **console** | Bulk code generation, subscription |
| write_tests | **console** | Bulk test generation, subscription |
| build | tool | Local build command |
| run_tests | tool | Local test command |
| fix_code | **console** | Code modification with project context |
| review_quality | api | Text analysis |
| review_security | api | Text analysis |
| apply_review_fixes | **console** | Code modification |
| generate_api_doc | api | Lightweight doc generation |
| generate_ops_manual | api | Lightweight doc generation |
| generate_changelog | api | Lightweight doc generation |

---

## 3. State Definition (Current)

```python
class AutoPipeState(TypedDict):
    # --- Input ---
    requirements: str
    project_name: str
    project_path: str
    config_path: str                # pipeline.yaml path

    # --- Pre-build Check ---
    pre_build_result: str           # "success" | "fail"
    pre_build_errors: str           # Pre-existing build error log
    pre_test_result: str            # "success" | "fail"
    pre_test_errors: str            # Pre-existing test error log

    # --- Phase 1: Design ---
    requirements_analysis: str
    design_spec: str                # Unified design doc (API + DB + UI + class design)
    api_spec: str                   # Legacy compat
    db_schema: str
    ui_spec: str
    design_approved: bool
    design_feedback: str

    # --- Phase 2: Development ---
    source_code: dict               # {filepath: code_content}
    test_code: dict                 # {filepath: test_content}
    code_files_created: Annotated[list[str], operator.add]

    # --- Phase 3: Build/Test ---
    build_result: str               # "success" | "fail"
    build_log: str
    test_result: str                # "pass" | "fail"
    test_log: str
    test_errors: list[str]
    fix_iteration: int
    max_fix_iterations: int         # default: 5

    # --- Phase 4: Review ---
    review_report: str
    security_report: str
    merged_review: str
    review_approved: bool
    review_feedback: str
    review_iteration: int
    max_review_iterations: int      # default: 3

    # --- Phase 5: Documentation ---
    api_doc: str
    ops_manual: str
    changelog: str
    deliverables: list[str]

    # --- Common (Annotated: parallel node safe) ---
    current_phase: Annotated[str, _last]
    current_step: Annotated[str, _last]
    progress: Annotated[int, _max]
    messages: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
```

---

## 4. Graph Structure (Current)

```python
def build_pipeline_graph():
    graph = StateGraph(AutoPipeState)

    # Pre-build check
    graph.add_node("pre_build_check", pre_build_check_node)

    # Phase 1: Design
    graph.add_node("analyze_requirements", analyze_requirements_node)
    graph.add_node("generate_design", generate_design_node)

    # Phase 2: Development (parallel)
    graph.add_node("develop_code", develop_code_node)
    graph.add_node("write_tests", write_tests_node)

    # Phase 3: Build/Test (cycle)
    graph.add_node("build", build_node)
    graph.add_node("run_tests", run_tests_node)
    graph.add_node("fix_code", fix_code_node)

    # Phase 4: Review (parallel + approval)
    graph.add_node("start_review", start_review_node)
    graph.add_node("review_quality", review_quality_node)
    graph.add_node("review_security", review_security_node)
    graph.add_node("merge_reviews", merge_reviews_node)
    graph.add_node("review_decision", review_decision_node)
    graph.add_node("apply_review_fixes", apply_review_fixes_node)

    # Phase 5: Documentation (parallel)
    graph.add_node("start_docs", start_docs_node)
    graph.add_node("generate_api_doc", generate_api_doc_node)
    graph.add_node("generate_ops_manual", generate_ops_manual_node)
    graph.add_node("generate_changelog", generate_changelog_node)
    graph.add_node("package", package_node)
    graph.add_node("done", done_node)

    # --- Edges ---

    graph.set_entry_point("pre_build_check")
    graph.add_edge("pre_build_check", "analyze_requirements")
    graph.add_edge("analyze_requirements", "generate_design")

    # Design -> Dev (parallel, after Human Review)
    graph.add_edge("generate_design", "develop_code")
    graph.add_edge("generate_design", "write_tests")

    # Dev -> Build (fan-in)
    graph.add_edge("develop_code", "build")
    graph.add_edge("write_tests", "build")

    # Build/Test cycle
    graph.add_edge("build", "run_tests")
    graph.add_conditional_edges("run_tests", check_test_result, {
        "pass": "start_review",
        "fail": "fix_code",
        "max_retries": "package",
    })
    graph.add_edge("fix_code", "build")

    # Review (parallel + approval cycle)
    graph.add_edge("start_review", "review_quality")
    graph.add_edge("start_review", "review_security")
    graph.add_edge("review_quality", "merge_reviews")
    graph.add_edge("review_security", "merge_reviews")
    graph.add_edge("merge_reviews", "review_decision")
    graph.add_conditional_edges("review_decision", check_review_result, {
        "approved": "start_docs",
        "rejected": "apply_review_fixes",
        "max_retries": "start_docs",
    })
    graph.add_edge("apply_review_fixes", "start_review")

    # Documentation (parallel)
    graph.add_edge("start_docs", "generate_api_doc")
    graph.add_edge("start_docs", "generate_ops_manual")
    graph.add_edge("start_docs", "generate_changelog")
    graph.add_edge("generate_api_doc", "package")
    graph.add_edge("generate_ops_manual", "package")
    graph.add_edge("generate_changelog", "package")
    graph.add_edge("package", "done")
    graph.add_edge("done", END)

    return graph.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["develop_code", "review_decision"],
    )
```

---

## 5. Pre-existing Error Detection

The pipeline runs a pre-build check before Phase 1 to establish baseline:

```
pre_build_check_node:
    1. Run build command (e.g. ./gradlew build)
       -> Store pre_build_result + pre_build_errors
    2. If build passes, run test command (e.g. ./gradlew test)
       -> Store pre_test_result + pre_test_errors

check_test_result:
    If build/test fails in Phase 3:
        Compare current errors with pre-build/pre-test errors
        If 80%+ match -> "pre-existing error" -> skip fix loop
        If different -> "pipeline-caused error" -> run fix_code
```

This prevents wasting fix iterations on errors that existed before the pipeline ran.

---

## 6. pipeline.yaml Structure

```yaml
project:
  name: my-erp
  path: /path/to/my-erp
  language: java              # Detected by Bootstrap
  framework: spring-boot      # Detected by Bootstrap
  build_command: ./gradlew build
  test_command: ./gradlew test

nodes:
  analyze_requirements:
    executor: api
    prompt_template: prompts/analyze_requirements.md
  generate_design:
    executor: console          # Reads project code directly
    prompt_template: prompts/generate_design.md
  develop_code:
    executor: console
    prompt_template: prompts/develop_code.md
  write_tests:
    executor: console
    prompt_template: prompts/write_tests.md
  build:
    executor: tool
    command: ./gradlew build   # Auto-detected, overridable
  run_tests:
    executor: tool
    command: ./gradlew test    # Auto-detected, overridable
  fix_code:
    executor: console
    prompt_template: prompts/develop_code.md
  review_quality:
    executor: api
    prompt_template: prompts/code_review.md
  review_security:
    executor: api
    prompt_template: prompts/code_review.md
  # ... (docs nodes similar)

cycles:
  build_test:
    max_retries: 5
  code_review:
    max_retries: 3
```

### Infrastructure Project Example (Terraform)

```yaml
project:
  name: my-infra
  language: terraform
  framework: terraform
  build_command: terraform init -backend=false && terraform validate
  test_command: terraform plan -no-color -input=false

# Same pipeline flow, different commands
```

---

## 7. Prompt Templates

Prompt templates are generated by Bootstrap with:
1. **Project context** (language, framework, architecture, layers)
2. **Deep Analysis results** (architecture patterns, conventions, test strategy)

Example `prompts/develop_code.md`:
```markdown
# Code Development

## Project Context
- Project: my-erp
- Language: java
- Framework: spring-boot
- Architecture: layered
- Layers: controller, service, repository, entity

## Deep Analysis: Architecture & Code Patterns
(Injected from Bootstrap Step 2/4 analysis - conventions, naming rules, etc.)

## Deep Analysis: Overall Assessment & Code Generation Rules
(Injected from Bootstrap Step 4/4 analysis - specific rules to follow)

## Required
- Follow existing project patterns 100%
- Architecture layer structure: controller, service, repository, entity
- Framework conventions: spring-boot

## Task
Implement code based on the design below:

{design_spec}
```

---

## 8. Cost Structure (Per Execution)

| Phase | Executor | Est. Tokens | Cost |
|-------|----------|-------------|------|
| Requirements analysis | api | ~3,000 | ~W30 |
| Design generation | console | 50K+ | Subscription (W0) |
| Code development | console | 50K+ | Subscription (W0) |
| Test writing | console | 30K+ | Subscription (W0) |
| Build/Test | tool | 0 | W0 |
| Code fix (on failure) | console | 20K+ | Subscription (W0) |
| Code review | api | ~5,000 | ~W50 |
| Security check | api | ~3,000 | ~W30 |
| Documentation | api | ~5,000 | ~W50 |
| **Total** | | | **~W160** |

---

## 9. Error Handling Strategy

| Error Type | Response | Max Retries |
|------------|----------|-------------|
| Pre-existing build/test failure | Skip fix loop | 0 |
| Pipeline-caused build failure | fix_code -> rebuild | 5 |
| Review rejection | apply_review_fixes -> re-review | 3 |
| Console CLI not installed | Fallback to API (gpt-4o) | 1 |
| LLM API timeout | (Planned) Exponential backoff | 3 |

---

## 10. Future Expansion

| Feature | Description | Difficulty |
|---------|-------------|------------|
| **Phase 6: Incident Response** | Separate graph for log analysis + action plan | Medium |
| **SqliteSaver** | Persistent state across restarts | Low |
| **fix_code dedicated prompt** | Better error-focused prompt template | Low |
| **RAG integration** | Vector DB for internal code/wiki reference | Medium |
| **Git integration** | Auto branch + PR creation after pipeline | Medium |
| **Prompt A/B testing** | Compare quality across prompts | Low |
