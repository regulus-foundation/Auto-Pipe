# Auto-Pipe

**Input a project path, get automated design -> code -> test -> review -> docs.**

Auto-Pipe is a development automation pipeline that analyzes your existing codebase, generates designs based on your requirements, writes code following your project's patterns, builds/tests it, reviews for quality/security, and generates documentation -- all through a web UI with human-in-the-loop approvals.

> **Status**: Work in progress. Actively used for personal development, being stabilized for open-source.

---

## How It Works

```
1. Bootstrap (one-time per project)
   Input project path -> Deep analysis -> Config generation

2. Pipeline (repeated per requirement)
   Input requirement -> Design -> [Approve] -> Code + Tests -> Build/Test -> Review -> [Approve] -> Docs
```

### Pipeline Flow

```
pre_build_check -----> generate_design -----> [Human Review]
     (tool)              (console)             Design approval
                                                    |
                                                    v
                                    develop_code + write_tests
                                         (console, parallel)
                                                    |
                                                    v
                                 build -> run_tests -> check_result
                                   ^                      |
                                   |    pre-existing? -> skip
                                   +--- fix_code <--- new error
                                              pass -> review
                                                    |
                                                    v
                                    review_quality + review_security
                                         (api, parallel)
                                                    |
                                                    v
                                            [Human Review]
                                            Review approval
                                                    |
                                                    v
                                    api_doc + ops_manual + changelog
                                         (api, parallel)
                                                    |
                                                    v
                                            package -> done
```

---

## Supported Project Types

### Application

| Type | Detection | Build | Test |
|------|-----------|-------|------|
| Java (Spring Boot) | build.gradle + markers | `./gradlew build` | `./gradlew test` |
| Node.js (NestJS/Express/Next.js) | package.json + markers | `npm run build` | `npm test` |
| Python (Django/FastAPI/Flask) | requirements.txt + markers | `pip install` | `pytest` |
| Go | go.mod | `go build ./...` | `go test ./...` |
| Rust | Cargo.toml | `cargo build` | `cargo test` |
| Flutter | pubspec.yaml | flutter build | flutter test |

### Infrastructure / IaC

| Type | Detection | Validate | Plan/Dry-run |
|------|-----------|----------|--------------|
| Terraform | main.tf | `terraform validate` | `terraform plan` |
| Helm | Chart.yaml | `helm lint` | `helm template --dry-run` |
| Kustomize | kustomization.yaml | `kustomize build` | `kubectl --dry-run` |
| Ansible | ansible.cfg / site.yml | `ansible-lint` | `ansible-playbook --check` |

All project types share the same pipeline flow. Bootstrap auto-detects the type and configures appropriate commands.

---

## Architecture

```
+-------------------------------------------------------------------+
|                       Auto-Pipe System                             |
|                                                                    |
|  [ Bootstrap (one-time) ]                                          |
|  scan_files -> deep_analyze (4 steps) -> [review] -> generate_config|
|                                                                    |
|  [ Pipeline (repeated) ]                                           |
|  pre_check -> design -> [review] -> dev+test -> build/test         |
|  -> review -> [review] -> docs -> package                          |
|                                                                    |
|  [ 3 Executor Types ]                                              |
|  api: OpenAI/Claude API (lightweight analysis, review, docs)       |
|  console: Claude Code CLI (bulk code generation, design)           |
|  tool: subprocess (build, test, local commands)                    |
|                                                                    |
|  [ Web UI: Streamlit ]                                             |
|  Control tower for all flows (input/monitoring/decisions/logs)     |
+-------------------------------------------------------------------+
```

### Cost Optimization

The key insight: **code generation is the most expensive LLM task**. By using Claude Code CLI (subscription, fixed cost) for bulk generation and OpenAI API (pay-per-token) only for lightweight tasks, Auto-Pipe reduces per-execution cost to ~$0.15.

| Phase | Executor | Cost |
|-------|----------|------|
| Design generation | console (subscription) | $0 |
| Code development | console (subscription) | $0 |
| Test writing | console (subscription) | $0 |
| Requirements analysis | api (per-token) | ~$0.03 |
| Code review | api (per-token) | ~$0.05 |
| Documentation | api (per-token) | ~$0.05 |

---

## Quick Start

### Prerequisites

- Python 3.12+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (recommended, for console executor)
- OpenAI API key (for api executor)
- Docker (optional, for Langfuse observability)

### Installation

```bash
git clone https://github.com/your-username/auto-pipe.git
cd auto-pipe

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run

```bash
./run.sh
# or
source venv/bin/activate
streamlit run web/app.py --server.port 8502 --server.headless true

# Open http://localhost:8502
```

### Usage

1. **Bootstrap** (first time per project)
   - Go to Bootstrap page
   - Enter project path
   - Review analysis results
   - Approve to generate config

2. **Pipeline** (per requirement)
   - Go to Pipeline page
   - Select project
   - Enter requirements
   - Review and approve design
   - Monitor build/test progress
   - Review and approve code review
   - Done!

---

## Project Structure

```
auto-pipe/
+-- core/                     # Shared modules
|   +-- analyzer.py           # Project analyzer (file scan + detection rules)
|   +-- config_generator.py   # pipeline.yaml + prompt template generator
|   +-- config_loader.py      # Config loader -> Executor mapping
|   +-- executor.py           # Executor abstraction (api/console/tool)
|   +-- llm.py                # Central LLM instance manager
|   +-- file_logger.py        # Per-project file logging
|
+-- bootstrap/                # Bootstrap pipeline (one-time analysis)
|   +-- graph.py              # LangGraph: scan -> analyze -> review -> config
|
+-- pipeline/                 # Main pipeline (repeated execution)
|   +-- graph.py              # LangGraph: 5-phase pipeline
|   +-- state.py              # State definition with reducers
|   +-- utils.py              # Common utilities
|   +-- nodes/                # Phase implementations
|       +-- design.py         # Phase 1: Design (console)
|       +-- develop.py        # Phase 2: Code + tests (console)
|       +-- build_test.py     # Phase 3: Build/test/fix cycle (tool)
|       +-- review.py         # Phase 4: Quality + security review (api)
|       +-- docs.py           # Phase 5: Documentation (api)
|
+-- web/                      # Streamlit Web UI
|   +-- app.py                # Main entry
|   +-- pages/
|       +-- bootstrap.py      # Bootstrap page
|       +-- pipeline.py       # Pipeline execution page
|       +-- examples.py       # LangGraph learning examples
|
+-- projects/                 # Per-project output (gitignored)
|   +-- {name}/
|       +-- pipeline.yaml     # Pipeline config
|       +-- prompts/*.md      # Project-specific prompts
|       +-- analysis/*.md     # Deep analysis documents
|       +-- log/*.log         # Execution logs
|
+-- examples/                 # 9 LangGraph learning patterns
```

---

## Design Documents

| Document | Description |
|----------|-------------|
| [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) | System architecture, tech decisions |
| [BOOTSTRAP_DESIGN.md](BOOTSTRAP_DESIGN.md) | Bootstrap pipeline design |
| [AUTO_PIPE_DESIGN.md](AUTO_PIPE_DESIGN.md) | Main pipeline design |
| [WEB_UI_DESIGN.md](WEB_UI_DESIGN.md) | Web UI structure and integration |
| [CHANNEL_GATEWAY_DESIGN.md](CHANNEL_GATEWAY_DESIGN.md) | Multi-channel interface design (planned) |
| [TODO_LIST.md](TODO_LIST.md) | Current tasks and roadmap |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for api executor |
| `AUTO_PIPE_MODEL` | No | Override default model (default: gpt-4o-mini) |
| `LANGFUSE_SECRET_KEY` | No | Langfuse secret key for observability |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse public key |
| `LANGFUSE_HOST` | No | Langfuse host URL |

### Claude Code CLI (Console Executor)

The console executor uses [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) for bulk code generation. This is optional -- if not installed, it automatically falls back to the API executor (gpt-4o).

Using Claude Code CLI is recommended because:
- Subscription model = unlimited tokens for code generation
- Can read project files directly
- Significantly reduces per-execution cost

---

## Roadmap

See [TODO_LIST.md](TODO_LIST.md) for current status and priorities.

**Near-term:**
- fix_code quality improvements
- Dedicated fix_code prompt template
- Monitor/History web pages

**Mid-term:**
- SqliteSaver for persistent state
- Telegram bot integration (voice + text commands)

**Long-term:**
- Git integration (auto PR creation)
- RAG for internal code/wiki reference
- Multi-user support (PostgresSaver)

---

## Contributing

This project is in early stages. Issues and feedback are welcome!

1. Fork the repository
2. Create a feature branch
3. Read the design documents before making changes
4. Submit a pull request

---

## License

[MIT](LICENSE)
