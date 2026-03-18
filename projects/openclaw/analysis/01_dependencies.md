# OpenClaw 프로젝트 빌드/의존성 분석

## 1. 의존성 분석

### 핵심 의존성 및 역할

**메시징 채널 통합 (핵심 도메인)**
| 패키지 | 용도 |
|---------|------|
| `grammy` + `@grammyjs/*` | Telegram 봇 |
| `@buape/carbon` | Discord 봇 (고정 버전, 업데이트 금지 정책) |
| `discord-api-types`, `@discordjs/voice` | Discord API 타입 + 음성 |
| `@slack/bolt`, `@slack/web-api` | Slack 통합 |
| `@whiskeysockets/baileys` | WhatsApp (비공식 Web API) |
| `@line/bot-sdk` | LINE 메신저 |
| `@larksuiteoapi/node-sdk` | Feishu/Lark |

**AI/LLM 통합**
| 패키지 | 용도 |
|---------|------|
| `@mariozechner/pi-*` (4개) | Pi AI 에이전트 코어/코딩/TUI |
| `@aws-sdk/client-bedrock` | AWS Bedrock LLM |
| `@modelcontextprotocol/sdk` | MCP 프로토콜 연동 |
| `node-llama-cpp` (peer, optional) | 로컬 LLM 실행 |
| `@agentclientprotocol/sdk` | ACP 에이전트 프로토콜 |

**웹/서버**
| 패키지 | 용도 |
|---------|------|
| `express` (v5) | HTTP 서버 (게이트웨이) |
| `hono` | 경량 HTTP 프레임워크 (오버라이드로 `4.12.7` 고정) |
| `ws` | WebSocket |
| `undici` | HTTP 클라이언트 |
| `playwright-core` | 브라우저 자동화/웹 스크래핑 |

**미디어/데이터 처리**
| 패키지 | 용도 |
|---------|------|
| `sharp` | 이미지 처리 |
| `pdfjs-dist` | PDF 파싱 |
| `@lancedb/lancedb` + `sqlite-vec` | 벡터 DB (메모리/RAG) |
| `opusscript` | 음성 코덱 (Discord voice) |
| `node-edge-tts` | TTS (텍스트→음성) |

**CLI/터미널**
| 패키지 | 용도 |
|---------|------|
| `commander` | CLI 커맨드 파싱 |
| `@clack/prompts` | 인터랙티브 CLI 프롬프트 |
| `chalk` | 터미널 색상 |
| `qrcode-terminal` | QR 코드 (WhatsApp 페어링 등) |
| `@lydell/node-pty` | 의사 터미널 (에이전트 실행) |

### 버전 상태 및 보안 이슈 가능성

**고정 버전 (오버라이드 강제)**  
`package.json:269-282`에서 pnpm overrides로 보안 취약 패키지를 강제 교체:
- `request` → `@cypress/request@3.0.10` (deprecated 패키지 대체)
- `request-promise` → `@cypress/request-promise@5.0.0`
- `node-domexception` → `@nolyfill/domexception` (polyfill 교체)
- `fast-xml-parser` → `5.3.8`, `tough-cookie` → `4.1.3`, `yauzl` → `3.2.1` (보안 패치 고정)
- `tar` → `7.5.11` (CVE 대응으로 추정)

**주의 필요 항목:**
- `@whiskeysockets/baileys: 7.0.0-rc.9` — RC 버전 사용 중, 비공식 WhatsApp 라이브러리라 API 변경/차단 리스크
- `@buape/carbon: 0.0.0-beta-20260216184201` — 베타 프리릴리스, 업데이트 금지 정책 명시
- `sqlite-vec: 0.1.7-alpha.2` — 알파 버전
- `@lydell/node-pty: 1.2.0-beta.3` — 베타, 네이티브 바인딩
- `@sinclair/typebox: 0.34.48` — overrides에도 동일 버전 고정 (호환성 문제 방지)

### 불필요/중복 가능성

- `express` (v5) + `hono` — 두 HTTP 프레임워크 공존. Express는 게이트웨이 메인, Hono는 경량 라우팅용으로 분리 사용 추정. 장기적으로 통합 검토 가능.
- `zod` (v4) + `@sinclair/typebox` — 두 스키마 검증 라이브러리 공존. Typebox는 MCP/프로토콜 스키마, Zod는 일반 검증용으로 분리된 것으로 보이나 중복 영역 존재 가능.
- `linkedom` + `jsdom` (dev) — DOM 파싱 라이브러리 2개. linkedom은 프로덕션(경량), jsdom은 테스트용.

---

## 2. 빌드 구조

### 빌드 파이프라인 (`package.json:48-50`)

```
build = canvas:a2ui:bundle
      → tsdown-build.mjs          (번들링)
      → runtime-postbuild.mjs     (런타임 후처리)
      → build:plugin-sdk:dts      (플러그인 SDK 타입 생성, tsc)
      → write-plugin-sdk-entry-dts
      → canvas-a2ui-copy
      → copy-hook-metadata
      → copy-export-html-templates
      → write-build-info
      → write-cli-startup-metadata
      → write-cli-compat
```

**특이사항:**
- **tsdown** (`tsdown: 0.21.2`)을 번들러로 사용 — esbuild 기반이지만 rolldown으로 전환 중인 도구
- **build:docker** — `canvas:a2ui:bundle` 스킵 (Docker에서는 A2UI 프론트엔드 번들 불필요)
- **build:plugin-sdk:dts** — `tsc -p tsconfig.plugin-sdk.dts.json || true`로 타입 생성 실패를 무시 (`package.json:51`)
- **prepack** — `pnpm build && pnpm ui:build`로 npm publish 전 자동 빌드

### 모듈 구조

**플러그인 아키텍처:**  
`package.json:14-165`의 `exports` 맵이 핵심. `openclaw/plugin-sdk/*` 경로로 40개+ 서브 모듈을 노출:
- 각 채널별 SDK (`telegram`, `discord`, `slack`, `signal`, `imessage`, `whatsapp`, `line`, `msteams`, `matrix` 등)
- 기능별 SDK (`voice-call`, `memory-core`, `memory-lancedb`, `diffs`, `llm-task`, `thread-ownership` 등)
- 플러그인은 `extensions/` 디렉토리에 워크스페이스 패키지로 존재

**TypeScript 설정 (`tsconfig.json`):**
- `module: NodeNext` + `moduleResolution: NodeNext` — ESM 네이티브
- `target: es2023` — 최신 JS 타겟 (Node 22+ 요구와 일치)
- `paths` 매핑으로 `openclaw/plugin-sdk` → `src/plugin-sdk/`로 개발 시 해석
- `noEmit: true` — tsc는 타입 체크 전용, 실제 빌드는 tsdown 담당

### 프로파일/환경 설정

- **테스트 프로파일:** `OPENCLAW_TEST_PROFILE=low`, `OPENCLAW_TEST_SERIAL_GATEWAY=1` (메모리 제한 환경)
- **채널 스킵:** `OPENCLAW_SKIP_CHANNELS=1` (게이트웨이 개발 시 채널 로드 생략)
- **라이브 테스트:** `OPENCLAW_LIVE_TEST=1` + `LIVE=1` (실제 API 키 필요)
- **타입 체커:** `pnpm tsgo` — `@typescript/native-preview` (Go로 작성된 실험적 TS 컴파일러) 사용

---

## 3. 외부 연동

### 데이터베이스/저장소

| 기술 | 근거 | 용도 |
|------|------|------|
| **SQLite** (+ sqlite-vec) | `dependencies: "sqlite-vec"` | 로컬 데이터 저장 + 벡터 검색 |
| **LanceDB** | `dependencies: "@lancedb/lancedb"` | 벡터 DB (메모리/RAG 파이프라인) |

순수 로컬 임베디드 DB만 사용 — PostgreSQL/MySQL 등 외부 RDBMS 의존 없음.

### 외부 API/서비스

| 서비스 | 패키지/근거 |
|--------|-------------|
| **AWS Bedrock** | `@aws-sdk/client-bedrock` |
| **Telegram API** | `grammy` |
| **Discord API** | `@buape/carbon`, `discord-api-types` |
| **Slack API** | `@slack/bolt`, `@slack/web-api` |
| **WhatsApp (비공식)** | `@whiskeysockets/baileys` |
| **LINE API** | `@line/bot-sdk` |
| **Feishu/Lark API** | `@larksuiteoapi/node-sdk` |
| **MCP 서버** | `@modelcontextprotocol/sdk` |
| **mDNS (로컬 디스커버리)** | `@homebridge/ciao` |
| **Microsoft Edge TTS** | `node-edge-tts` |

### 네트워크/프록시

- `https-proxy-agent` — 프록시 환경 지원
- `ipaddr.js` — IP 주소 파싱/검증 (보안 바인딩 관련)

### 환경별 설정 차이

CLAUDE.md에서 확인되는 구분:
- **로컬 개발:** `gateway.mode=local`, `~/.openclaw/credentials/`에 인증 정보 저장
- **Docker:** `build:docker` 스크립트 별도, A2UI 번들 생략
- **CI:** `deadcode:ci`, `test:sectriage` 등 CI 전용 스크립트
- **Parallels VM 테스트:** macOS/Windows/Linux 각각 별도 smoke 테스트 하네스
- **Fly.io 배포:** CLAUDE.md에 `fly ssh console -a flawd-bot` 배포 명령 기록

### Python 설정 (`pyproject.toml`)

- `skills/` 디렉토리의 Python 스킬 테스트용 (Ruff linter + pytest)
- 메인 프로젝트와 별도 — 보조적 스킬 스크립트 용도

---

## 요약 판단

**강점:** 플러그인 SDK 아키텍처가 잘 설계되어 40개+ 채널/기능을 독립적으로 확장 가능. pnpm overrides로 보안 취약 의존성을 적극 관리.

**리스크:** RC/alpha/beta 네이티브 패키지 다수(`baileys`, `node-pty`, `sqlite-vec`, `carbon`) — 프로덕션 안정성 주의. Express v5 + Hono 이중 프레임워크, Zod + Typebox 이중 스키마 검증은 장기적 통합 후보.
