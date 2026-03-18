# 코드 개발

## 프로젝트 컨텍스트
- 프로젝트: openclaw
- 언어: javascript
- 프레임워크: express
- 아키텍처: unknown
- 레이어: N/A
- 테스트 프레임워크: vitest


## Deep Analysis: 아키텍처 & 코드 패턴
# OpenClaw 프로젝트 핵심 소스 코드 분석

## 1. 아키텍처 패턴

### 사용 패턴: **Plugin-based Modular Monolith + Gateway 패턴**

전통적인 레이어드/클린 아키텍처가 아닌, **게이트웨이 중심의 플러그인 아키텍처**를 채택하고 있습니다.

**핵심 구조:**

```
[Channels/Extensions]  →  [Gateway Server]  →  [Agent Runtime]
  (telegram, discord,       (WebSocket,         (pi-agent-core,
   signal, iOS, web)         HTTP, RPC)          pi-coding-agent)
        ↓                       ↓                     ↓
  [Config/Sessions]        [Auth/Pairing]        [Tools/Skills]
   (JSON file store)       (Device identity,     (web-search, browser,
                            TLS fingerprint)      file ops)
```

**레이어 간 의존 방향:**

- **Controller 레이어** (`extensions/telegram/src/bot-handlers.ts`, `src/gateway/server/ws-connection/message-handler.ts`): 인바운드 메시지를 수신하고 라우팅. 내부 서비스 모듈을 직접 import
- **Service 레이어** (`src/cron/service/timer.ts`, `src/cron/service/jobs.ts`): 비즈니스 로직 수행. State 객체를 통한 의존성 주입
- **Repository 레이어** (`src/config/sessions/store.ts`, `src/pairing/pairing-store.ts`): JSON 파일 기반 영속화. 파일 잠금(`withFileLock`) 기반 동시성 제어
- **Middleware 레이어** (`src/agents/pi-extensions/compaction-safeguard.ts`, `src/agents/session-tool-result-guard.ts`): 세션 전사(transcript) 변환, 도구 결과 가드

**의존 방향 문제점:** Controller가 서비스/유틸을 직접 import하는 flat한 구조입니다. `bot-handlers.ts`가 20개 이상의 내부 모듈을 직접 import하는 것이 대표적 (`bot-handlers.ts:1-68`). Hexagonal이나 Clean Architecture의 포트/어댑터 경계가 명확하지 않습니다.

**관심사 분리 수준:** **중간**. 채널별 분리(extensions/*)는 잘 되어 있으나, 각 채널 핸들러 내부에서 config, session, routing, pairing 등 횡단 관심사를 직접 호출합니다.

---

## 2. 코드 컨벤션

### 네이밍 규칙

**TypeScript (서버):**
- **함수:** camelCase, `resolve/build/compute/normalize` 접두사가 지배적
  - `resolveInboundMediaFileId()`, `buildSyntheticTextMessage()`, `computeJobNextRunAtMs()`, `normalizeAllowEntry()`
- **상수:** UPPER_SNAKE_CASE
  - `MEDIA_GROUP_TIMEOUT_MS`, `MAX_PREAUTH_PAYLOAD_BYTES`, `DEFAULT_BACKOFF_SCHEDULE_MS`
- **타입/인터페이스:** PascalCase
  - `TelegramMediaRef`, `CronRunOutcome`, `SessionEntry`, `GatewayWsClient`
- **Boolean 함수:** `is/has/should` 접두사
  - `isMediaSizeLimitError()`, `hasInboundMedia()`, `shouldDebounceTextInbound()`
- **파일명:** kebab-case (`bot-handlers.ts`, `session-tool-result-guard.ts`, `compaction-safeguard.ts`)

**Swift (iOS/macOS):**
- **클래스:** PascalCase with 제품명 접두사 — `GatewayConnectionController`, `NodeAppModel`, `PortGuardian`
- **프로퍼티:** camelCase — `gatewayStatusText`, `pendingTrustPrompt`, `didAutoConnect`
- **Enum:** PascalCase 케이스 — `LastGatewayKind.manual`, `CameraHUDKind.recording`
- **Protocol:** `-ing`/`-able` 접미사 — `WebSocketTasking`, `WebSocketSessioning`, `CameraServicing`, `LocationServicing`

### DI(의존성 주입) 패턴

**TypeScript:** 두 가지 패턴이 공존:

1. **State 객체 주입** (서비스 레이어): `CronServiceState`에 deps를 묶어서 전달
   ```typescript
   // src/cron/service/timer.ts
   export async function executeJobCoreWithTimeout(
     state: CronServiceState,  // deps.log, deps.cronConfig 등 포함
     job: CronJob,
   )
   ```

2. **매개변수 객체 주입** (컨트롤러 레이어): `RegisterTelegramHandlerParams`처럼 named parameter 객체로 전달
  

## Deep Analysis: 종합 평가 & 코드 생성 규칙
# OpenClaw 프로젝트 종합 평가 보고서

---

## 1. 프로젝트 성숙도 평가

### 전체 점수: **7.8 / 10**

| 영역 | 점수 | 근거 |
|------|------|------|
| 코드 품질 | 8.0 | 일관된 네이밍, TypeScript strict, Oxlint/Oxfmt 적용 |
| 아키텍처 | 7.5 | 플러그인 분리 우수, 내부 레이어 경계는 느슨 |
| 테스트 | 7.0 | 70% 임계값 설정, 테스트 유틸 풍부하나 네이티브 앱/게이트웨이 핵심 경로 공백 |
| 인프라/DevOps | 8.5 | 멀티 아키텍처 Docker, trusted publishing, 자동화 높음 |
| 보안 | 8.0 | 의존성 오버라이드로 CVE 대응, CODEOWNERS, GHSA 프로세스 정립 |
| 문서화 | 7.5 | CLAUDE.md 상세, Mintlify 문서 체계, i18n 파이프라인 존재 |

### 강점 TOP 3

**1. 플러그인 아키텍처의 확장성**
`extensions/` 하위에 채널별 독립 패키지로 분리하여, 새 메시징 채널 추가 시 코어를 건드리지 않는 구조. `plugin-runtime-mock.ts` 같은 테스트 인프라까지 표준화되어 있어 서드파티 확장이 실질적으로 가능한 수준.

**2. 릴리스 파이프라인의 성숙도**
npm trusted publishing + GitHub environment 기반 승인 게이트, Docker 멀티 아키텍처(amd64/arm64) 빌드, 베타/stable 채널 분리, `release-check.ts` 자동 검증까지 프로덕션급 릴리스 체계 완비. 수동 백필(`workflow_dispatch`)도 안전하게 설계됨.

**3. 개발자 경험(DX) 인프라**
`prek` pre-commit hooks, `scripts/committer`로 스테이징 스코프 제한, 테스트 프로파일(`OPENCLAW_TEST_PROFILE=low`), Parallels 기반 크로스 OS 스모크 테스트 자동화 등 대규모 오픈소스 프로젝트의 기여 품질을 보장하는 도구가 잘 갖춰져 있음.

### 개선 필요 TOP 3

**1. 게이트웨이 핵심 경로의 테스트 공백 (P0)**
`message-handler.ts`(700줄+)가 인증, 권한, rate limit, TLS 검증을 모두 담당하면서 커버리지 측정에서 **의도적으로 제외**되어 있음. 보안 직결 코드가 자동 검증 밖에 있는 것은 중대한 리스크.

**2. 레이어 경계의 부재**
`bot-handlers.ts`가 20개 이상 내부 모듈을 직접 import하는 flat한 의존 구조. 포트/어댑터 패턴 없이 컨트롤러가 저수준 store, config, routing을 직접 호출하므로, 리팩토링 시 변경 영향 범위가 넓어짐.

**3. 네이티브 앱(iOS/Android/macOS) 테스트 부재**
Swift/Kotlin 코드에 대한 자동화 테스트가 확인되지 않음. `GatewayConnectionController`, TLS fingerprint 검증, 디바이스 페어링 등 보안 민감 로직이 네이티브 레이어에 존재하나 무검증 상태.

---

## 2. 인프라 & DevOps 평가

### CI/CD 파이프라인

```
PR 생성
 ├─ labeler.yml        ← 자동 라벨링 (사이즈, 채널, maintainer 판별)
 ├─ workflow-sanity.yml ← actionlint, 탭 금지, composite input 검증
 ├─ codeql.yml         ← JS/TS, Python, Java, Swift, Actions 정적 분석
 ├─ sandbox-common-smoke.yml ← 샌드박스 이미지 빌드 검증
 └─ (prek hooks)       ← 로컬 pre-commit (lint, format, type-check)

태그 푸시 (v*)
 ├─ openclaw-npm-release.yml
 │   ├─ preview (push) ← 드라이런 + 메타데이터 검증
 │   └─ publish (dispatch) ← npm trusted publishing + provenance
 └─ docker-release.yml
     ├─ build-amd64    ← default + slim 이미지
     ├─ build-arm64    ← default + slim 이미지
     └─ merge-manifests ← 멀티아치 매니페스트 생성 + latest 태깅

스케줄
 ├─ stale.yml (매일 03:17 UTC) ← 이슈/PR 자동 stale + 48h 후 lock
 └─ auto-response.yml ← 라벨 기반 자동 응답/닫기
```

**평가:** 파이프라인 구성이 체계적이며, concurrency 그룹 설정으로 중복 실행 방지, GitHub App 토큰 이중화(primary + fallback) 등 운영 안정성을 고려한 설계. Blacksmith runner 사용으로 빌드 속도 최적화.

**주의점:** CodeQL이 `workflow_dispatch` 전용으로 설정되어 있어, PR마다 자동 실행되지 않음. 보안 분석이 수동 트리거에 의존하는 구조.

### 컨테이너화 수준: **상급**

| 항목 | 상태 |
|------|------|
| 멀티스테이지 빌드 | 4단계 (ext-deps → build → runtime-assets → runtime) |
| 이미지 변형 | default (bookworm) + slim (bookworm-slim) |
| 아키텍처 | amd64 + arm64 네이티브 빌드 |
| 이미지 고정 | SHA256 digest 핀닝 (재현 가능한 빌드) |
| 옵션 기능 | `OPENCLAW_INSTALL_BROWSER`, `OPENCLAW_INSTALL_DOCKER_CLI`, `OPENCLAW_DOCKER_APT_PACKAGES` — 빌드 시 선택적 설치 |
| 캐시 전략 | pnpm store, apt cache에 BuildKit 마운트 캐시 적용 |
| 보안 | non-root `


## 필수 준수 사항
- 기존 프로젝트 패턴을 100% 따를 것
- 아키텍처 레이어 구조 준수: N/A
- 프레임워크 컨벤션 준수: express

## 작업
아래 설계서를 기반으로 코드를 구현하세요:

{design_spec}
