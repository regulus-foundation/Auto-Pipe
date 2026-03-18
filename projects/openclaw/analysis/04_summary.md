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
| 보안 | non-root `node` 유저 실행, `cap_drop`, `no-new-privileges` |
| 헬스체크 | HTTP `/healthz` 기반 30초 간격 |

### 배포 전략

```
stable:  npm dist-tag "latest" + GHCR "latest" 태그
beta:    npm dist-tag "beta" + GHCR 버전 태그만
dev:     main 브랜치 → GHCR "main" 태그 (자동)
```

Docker Compose로 gateway + CLI 분리 실행을 지원하며, 샌드박스 격리(Docker-in-Docker CLI)도 옵션으로 제공. Fly.io 배포 경로도 존재(`flawd-bot`).

---

## 3. Auto-Pipe 활용 가이드

### a) 반드시 따라야 할 패턴

| # | 규칙 | 근거 |
|---|------|------|
| 1 | **ESM + strict TypeScript** — `any` 금지, `@ts-nocheck` 금지. `Type.Union` 대신 `stringEnum`/`optionalStringEnum` 사용 | `CLAUDE.md` 명시 + Oxlint 강제 |
| 2 | **동일 모듈에 static + dynamic import 혼용 금지** — lazy loading이 필요하면 `*.runtime.ts` 경계 파일 생성 후 그 파일만 dynamic import | 빌드 시 `[INEFFECTIVE_DYNAMIC_IMPORT]` 경고 발생 |
| 3 | **프로토타입 뮤테이션 금지** — `applyPrototypeMixins`, `Object.defineProperty(prototype, ...)` 대신 명시적 상속/컴포지션 사용 | 타입 안전성 보장 정책 |
| 4 | **CLI progress는 `src/cli/progress.ts`(`osc-progress` + `@clack/prompts` spinner) 사용** — 직접 스피너/프로그레스바 구현 금지 | 터미널 출력 일관성 |
| 5 | **터미널 색상은 `src/terminal/palette.ts` 공유 팔레트 사용** — 하드코딩 금지 | Lobster seam 정책 |
| 6 | **`format` 프로퍼티명을 tool 스키마에 사용하지 않기** — 일부 validator가 예약어로 취급 | 런타임 스키마 검증 실패 방지 |
| 7 | **플러그인 전용 의존성은 해당 extension의 `package.json`에만 추가** — 루트 `package.json`에 넣지 않음 | 플러그인 격리 원칙 |

### b) 파일 생성 위치 규칙

```
새 기능 (코어)
  src/<도메인>/
    ├─ <feature>.ts           ← 메인 로직
    ├─ <feature>.test.ts      ← 단위 테스트 (colocated)
    ├─ <feature>.e2e.test.ts  ← E2E 테스트
    └─ types.ts               ← 도메인 타입 (필요 시)

새 채널/확장
  extensions/<channel-name>/
    ├─ package.json           ← 독립 패키지 (workspace:* 금지)
    ├─ src/
    │   ├─ channel.ts         ← 채널 구현
    │   ├─ index.ts           ← 플러그인 엔트리
    │   └─ *.test.ts
    └─ tsconfig.json

새 CLI 커맨드
  src/commands/<command-name>.ts
  src/commands/<command-name>.test.ts

새 게이트웨이 엔드포인트
  src/gateway/server/<endpoint>/
    ├─ handler.ts
    └─ handler.test.ts

새 에이전트 도구
  src/agents/tools/<tool-name>.ts
  src/agents/tools/<tool-name>.test.ts
```

### c) 네이밍 규칙 요약

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일명 | kebab-case | `session-tool-result-guard.ts` |
| 함수 | camelCase, 동사 접두사 (`resolve`, `build`, `compute`, `normalize`) | `resolveInboundMediaFileId()` |
| Boolean 함수 | `is`/`has`/`should` 접두사 | `isMediaSizeLimitError()` |
| 상수 | UPPER_SNAKE_CASE | `MAX_PREAUTH_PAYLOAD_BYTES` |
| 타입/인터페이스 | PascalCase | `GatewayWsClient` |
| 제품명 | `OpenClaw` (UI/docs), `openclaw` (CLI/패키지/경로) | — |
| 영어 철자 | American English | `color`, `behavior`, `analyze` |

### d) Import/의존성 주입 규칙

```typescript
// 패턴 1: State 객체 주입 (서비스 레이어)
interface MyServiceState {
  deps: {
    log: Logger;
    config: Config;
  };
}
export async function doWork(state: MyServiceState, input: Input) { ... }

// 패턴 2: 매개변수 객체 주입 (핸들러/컨트롤러)
interface HandleMessageParams {
  session: Session;
  config: Config;
  send: (msg: string) => Promise<void>;
}
export async function handleMessage(params: HandleMessageParams) { ... }

// 패턴 3: createDefaultDeps (CLI 진입점)
export function createDefaultDeps(): Deps {
  return { log: createLogger(), config: loadConfig() };
}
```

- `workspace:*`를 `dependencies`에 사용하지 않음 (npm install 깨짐)
- `openclaw`는 플러그인의 `devDependencies` 또는 `peerDependencies`에만 배치
- patchedDependencies가 적용된 패키지는 반드시 exact version 사용 (`^`/`~` 금지)

### e) 에러 처리 규칙

```typescript
// 내부 코드는 신뢰 — 과도한 방어적 검증 금지
// 시스템 경계(사용자 입력, 외부 API)에서만 검증

// Good: 외부 경계 검증
function handleWebhook(req: Request) {
  const payload = parseAndValidate(req.body); // zod/typebox로 검증
  return processPayload(payload);             // 내부는 신뢰
}

// Bad: 내부 호출에 불필요한 null 체크
function processPayload(payload: ValidatedPayload) {
  if (!payload) throw new Error("impossible"); // 불필요
}
```

- OWASP Top 10 취약점(XSS, SQL injection, command injection 등) 주의
- `withFileLock` 패턴으로 파일 기반 동시성 제어
- 가상의 미래 시나리오를 위한 에러 핸들링/폴백 추가 금지

### f) 테스트 작성 규칙

```typescript
// 프레임워크: Vitest + V8 coverage
// 실행: pnpm test -- src/my-feature.test.ts -t "test name"

// 구조
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("MyFeature", () => {
  // setup/teardown
  beforeEach(() => { vi.clearAllMocks(); });

  it("행위 중심으로 기술한다", async () => {
    // Arrange
    const deps = createTestDeps();  // src/test-utils/ 활용

    // Act
    const result = await doWork(deps, input);

    // Assert
    expect(result).toMatchObject({ ... });
  });
});

// 모킹: vi.mock() 모듈 단위
// 플러그인 테스트: extensions/test-utils/plugin-runtime-mock.ts 활용
// 시간: src/test-utils/frozen-time.ts
// 환경변수: src/test-utils/env.ts
// Workers: 16 초과 금지
```

- 테스트 파일은 소스와 동일 디렉토리에 colocate
- 순수 테스트 추가/수정은 changelog 불필요
- live 테스트는 `*.live.test.ts`로 분리, `LIVE=1`로 실행

---

## 4. 추천 개발 순서

새 기능(예: 새 메시징 채널 `X` 추가)을 개발한다고 가정할 때:

### Phase 1: 탐색 & 설계

```
1. 기존 유사 채널 코드 분석 (extensions/msteams 또는 extensions/matrix 참고)
2. .devflow/features/<feature-name>/requirements.md 작성
3. 아키텍처 결정 (코어 vs 확장 vs 서드파티)
```

### Phase 2: 스캐폴딩

```
생성 파일:
  extensions/<channel>/
    ├─ package.json          ← name: @openclaw/<channel>
    ├─ tsconfig.json         ← extends 루트
    └─ src/
        ├─ index.ts          ← 플러그인 엔트리 (registerPlugin)
        ├─ channel.ts        ← 채널 구현 (sendMessage, onInbound 등)
        └─ types.ts          ← 채널 전용 타입

수정 파일:
  pnpm-workspace.yaml       ← extensions/<channel> 추가
  .github/labeler.yml       ← 채널 라벨 규칙 추가
```

### Phase 3: 핵심 로직 구현

```
생성 파일:
  extensions/<channel>/src/
    ├─ bot-handlers.ts       ← 인바운드 메시지 핸들러
    ├─ auth.ts               ← 인증/온보딩 로직
    └─ media.ts              ← 미디어 처리 (필요 시)

수정 파일:
  src/channels/              ← 채널 레지스트리에 등록 (필요 시)
  docs/channels/<channel>.md ← 사용자 문서
```

### Phase 4: 테스트

```
생성 파일:
  extensions/<channel>/src/
    ├─ channel.test.ts       ← 단위 테스트
    ├─ bot-handlers.test.ts  ← 핸들러 테스트
    └─ auth.test.ts          ← 인증 테스트

실행:
  pnpm test -- extensions/<channel>/
  pnpm build                 ← 빌드 검증
  pnpm check                 ← lint/format 검증
```

### Phase 5: 통합 & 문서

```
수정 파일:
  docs/channels/<channel>.md      ← 설정 가이드
  docs/zh-CN/channels/<channel>.md ← i18n (scripts/docs-i18n)
  CHANGELOG.md                    ← 해당 버전 섹션에 추가

검증:
  pnpm tsgo                  ← 타입 체크
  pnpm build                 ← 최종 빌드
  pnpm test                  ← 전체 테스트
  pnpm release:check         ← 릴리스 메타 검증 (태깅 전)
```

### Phase 6: PR 제출

```
scripts/committer "feat(<channel>): add <channel> messaging channel" <파일들...>
gh pr create --title "feat(<channel>): add <channel> channel" --body ...
```

---

### 최종 요약

OpenClaw은 **프로덕션 수준의 릴리스 인프라**와 **확장 가능한 플러그인 아키텍처**를 갖춘 성숙한 프로젝트입니다. 주요 리스크는 게이트웨이 인증 경로의 테스트 공백과 네이티브 앱 코드의 자동 검증 부재이며, 이 두 영역을 우선 보강하면 전체 신뢰성이 크게 향상될 것입니다. 코드 생성 시에는 기존 플러그인 구조를 100% 따르고, 의존성 격리 원칙을 준수하는 것이 핵심입니다.
