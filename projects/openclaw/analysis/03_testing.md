# OpenClaw 프로젝트 테스트 전략 분석 및 개선안

---

## 1. 현재 테스트 평가

### 1.1 테스트 커버리지 수준

**커버리지 임계값 (vitest.config.ts 기준):**
- Lines/Functions/Statements: 70%, Branches: 55% (V8 provider)

**레이어별 분포:**

| 레이어 | 테스트 파일 수 | 평가 |
|--------|-------------|------|
| `src/agents/` | ~442 | 충분 |
| `src/infra/` | ~253 | 충분 |
| `src/gateway/` | ~146 | 보통 (E2E 보완 필요) |
| `src/config/` | ~100 | 충분 |
| `extensions/` | ~573 | 플러그인별 편차 큼 |
| `apps/` (iOS/Android/macOS) | **0** | **심각한 공백** |
| `src/cron/service/` | 존재하나 제한적 | timer/jobs 핵심 로직 커버리지 불명확 |

**주요 관찰:**
- 커버리지 측정에서 `src/agents/`, `src/gateway/`, `src/channels/`, `src/cli/`, `src/commands/` 등이 **의도적으로 제외**되어 있어, 실질 커버리지가 수치보다 낮을 가능성이 높음
- Swift/Kotlin 네이티브 앱 코드(`apps/ios/`, `apps/android/`, `apps/macos/`)는 Vitest 범위 밖이며, 별도 테스트 프레임워크도 확인되지 않음

### 1.2 테스트 코드 품질

**Mocking 패턴 — 강점:**
- `vi.mock()`을 모듈 단위로 일관되게 사용
- `extensions/test-utils/plugin-runtime-mock.ts`로 플러그인 런타임을 표준화된 방식으로 모킹
- `src/test-utils/`에 36개의 공유 유틸리티 (env, fetch-mock, frozen-time 등) — 재사용성 높음
- `test/setup.ts`에서 OAuth 누출 방지, 환경변수 격리, 플러그인 레지스트리 리셋 등 철저한 격리

**Mocking 패턴 — 개선 필요:**

```typescript
// audit.test.ts — stubChannelPlugin이 100줄 이상의 반복적 boilerplate
const discordPlugin = stubChannelPlugin({
  id: "discord",
  label: "Discord",
  listAccountIds: (cfg) => { /* 동일 패턴 반복 */ },
  resolveAccount: (cfg, accountId) => { /* 동일 패턴 반복 */ },
});
// slack, telegram, zalouser 전부 거의 동일한 구조 복사
```

→ `discordPlugin`, `slackPlugin`, `telegramPlugin`, `zalouserPlugin` 모두 `listAccountIds`와 `resolveAccount`의 구현이 채널 ID만 다르고 로직이 동일. **팩토리 함수로 추출 가능**.

```typescript
// monitor.test.ts — mock 함수가 40개 이상 개별 선언
const mockEnqueueSystemEvent = vi.fn();
const mockBuildPairingReply = vi.fn(() => "Pairing code: TESTCODE");
const mockReadAllowFromStore = vi.fn().mockResolvedValue([]);
// ... 30줄 이상 계속
```

→ mock이 테스트 파일 상단에 flat하게 나열되어 가독성 저하. **mock fixture object로 그룹화** 필요.

**Assertion 패턴 — 강점:**
- `audit.test.ts`의 `hasFinding()`, `expectFinding()`, `expectNoFinding()` 같은 도메인 특화 assertion 헬퍼가 잘 정의됨
- E2E 테스트에서 contract 기반 검증 패턴 사용

**Assertion 패턴 — 개선 필요:**
- `subagent-announce.format.e2e.test.ts`의 `getSingleAgentCallParams()` 같은 헬퍼가 파일 내부에 inline 정의 — 여러 테스트에서 공유될 수 있는 패턴임에도 전역 유틸로 추출되지 않음

### 1.3 테스트 네이밍/구조 규칙

**잘 지켜지는 규칙:**
- `*.test.ts` (unit), `*.e2e.test.ts` (E2E), `*.live.test.ts` (live) 구분 명확
- 소스와 동일 디렉토리에 colocated — 파일 찾기 용이
- `describe` 블록으로 기능 단위 그룹핑 일관적

**개선 필요:**
- `it` 설명이 때로 구현 디테일을 기술 (`"sends instructional message to main agent with status and findings"`) — 행위/의도 중심으로 전환하면 리팩토링 내성 향상
- 일부 테스트 파일이 500줄 이상 (audit.test.ts, monitor.test.ts, loader.test.ts) — setup/fixture 분리로 본문 축소 가능

---

## 2. 테스트 부족 영역 (리스크 순)

### P0 — 즉시 보강 필요 (보안/안정성 직결)

| 영역 | 현황 | 리스크 |
|------|------|--------|
| `src/gateway/server/ws-connection/message-handler.ts` | 700줄+ 핸들러, 인증·권한·rate limit·TLS 검증 로직 포함. 커버리지 측정 제외 대상 | 인증 우회, 권한 상승 취약점 미탐지 |
| `apps/ios/` (GatewayConnectionController 등) | Vitest 범위 밖, XCTest 미확인 | TLS fingerprint 검증, 디바이스 페어링 로직 무검증 |
| `src/security/` | audit.test.ts 존재하나 filesystem audit, channel security 플래그가 `false`로 비활성화된 채 테스트 | 실제 파일시스템/채널 보안 감사 경로 미검증 |

### P1 — 단기 보강 권장 (핵심 비즈니스 로직)

| 영역 | 현황 | 리스크 |
|------|------|--------|
| `src/cron/service/timer.ts` | `applyJobResult`, `executeJobCoreWithTimeout`, backoff/retry 로직 등 복잡한 상태 머신 포함. 전용 테스트 확인 불가 | 크론 작업 실패 시 무한 루프, 재시도 폭주 |
| `extensions/bluebubbles/` | monitor.test.ts 존재하나 webhook 인증 검증, attachment 다운로드 에러 경로 부족 | 악성 webhook 주입, 미디어 처리 장애 |
| `src/routing/` | 라우팅 해석 오류 시 메시지가 잘못된 에이전트로 전달 | 메시지 유실/오배달 |
| `src/plugins/loader.ts` | loader.test.ts 존재하나 500줄+의 setup, 경로 해석 edge case 부족 | 악성 플러그인 로딩, 경로 주입 |

### P2 — 중기 개선 (유지보수성)

| 영역 | 현황 |
|------|------|
| `extensions/` 전반의 에러 핸들링 경로 | happy path 위주 테스트, 네트워크 실패·타임아웃·부분 응답 시나리오 부족 |
| `src/agents/subagent-*` | announce flow 테스트 존재하나 동시성 경합, 세션 정리 실패 시나리오 부족 |
| `src/infra/device-pairing.ts`, `device-identity.ts` | message-handler.ts에서 호출되나 통합 테스트 부족 |

---

## 3. 추천 테스트 전략

### 3.1 프레임워크 및 설정

| 테스트 유형 | 프레임워크 | 설정 권장 |
|------------|----------|----------|
| **Unit (TS)** | Vitest (현행 유지) | `pool: "forks"` 유지. 커버리지 제외 대상 축소 — 최소한 `src/gateway/`, `src/agents/`를 측정 범위에 포함 |
| **Integration (TS)** | Vitest + gateway E2E harness (현행 유지) | `test/helpers/gateway-e2e-harness.ts` 활용 확대. WebSocket 프로토콜 레벨 통합 테스트 추가 |
| **E2E (TS)** | Vitest e2e config (현행 유지) | 채널별 end-to-end 시나리오 추가 (현재 35개 → 목표 80개) |
| **iOS/macOS** | **XCTest + Swift Testing** (신규 도입) | `GatewayConnectionController` TLS 검증, 디바이스 페어링 플로우 |
| **Android** | **JUnit5 + Espresso** (신규 도입) | 앱 레벨 UI + 게이트웨이 연결 |
| **성능/부하** | **k6 또는 Artillery** (신규 도입) | WebSocket 동시 접속, 크론 대량 실행 |

### 3.2 데이터/상태 관리 전략

이 프로젝트는 전통적인 DB 중심 앱이 아니라 **파일 기반 상태 + WebSocket + 외부 API** 구조이므로:

| 관심사 | 전략 |
|--------|------|
| **파일시스템 상태** (config, sessions, credentials) | 현행 `tmpdir` 기반 fixture 유지. `test/test-env.ts`의 격리가 잘 동작함 |
| **SQLite** (QMD memory backend) | 현행 `node:sqlite` in-memory 모드 유지. `qmd-manager.test.ts`에서 `spawn` 모킹은 적절하나, **실제 SQLite 파일 기반 통합 테스트 1-2개 추가** 권장 |
| **외부 API** (Telegram, Discord, OpenAI 등) | `src/test-utils/fetch-mock.ts` 활용 유지. Live 테스트는 `LIVE=1`로 분리된 현행 패턴 유지 |
| **WebSocket** | gateway E2E harness 확장 — 현재 contract 기반이나, **악의적 프레임/프로토콜 위반 시나리오** 추가 |
| **크론 스케줄러** | `vi.useFakeTimers()` + `src/test-utils/frozen-time.ts` 활용. timer.ts의 상태 전이 테스트를 **state-machine 기반 property test**로 보강 |

### 3.3 테스트 작성 규칙/패턴

**즉시 적용 가능한 개선:**

**1) Mock fixture 표준화**

```typescript
// ❌ 현재: 40개 mock이 flat하게 나열
const mockA = vi.fn();
const mockB = vi.fn();
// ...

// ✅ 권장: 도메인별 fixture object
function createChannelMocks() {
  return {
    enqueueSystemEvent: vi.fn(),
    buildPairingReply: vi.fn(() => "Pairing code: TESTCODE"),
    readAllowFromStore: vi.fn().mockResolvedValue([]),
    // ...
  };
}
```

**2) 채널 플러그인 stub 팩토리 통합**

```typescript
// ❌ 현재: audit.test.ts에 4개 채널 stub이 100줄+ 복사
// ✅ 권장: src/test-utils/channel-plugins.ts의 기존 유틸 활용
import { createStubChannelPlugin } from "../test-utils/channel-plugins.js";
const discordPlugin = createStubChannelPlugin("discord");
```

**3) 테스트 파일 크기 제한**

- 500줄 초과 시 fixture/setup을 `__fixtures__/` 또는 같은 디렉토리의 `*.test-helpers.ts`로 분리
- `describe` 블록이 3단계 이상 중첩되면 별도 테스트 파일로 분할

**4) 에러 경로 필수 커버리지 규칙**

```typescript
// 모든 public 함수에 대해 최소한:
describe("functionName", () => {
  it("returns expected result on valid input");      // happy path
  it("throws/returns error on invalid input");       // validation
  it("handles upstream failure gracefully");          // dependency failure
});
```

**5) 보안 관련 코드 테스트 필수 체크리스트**

`src/gateway/`, `src/security/`, `src/infra/device-*` 변경 시:
- 인증 없는 요청 → 거부 확인
- 만료된/변조된 토큰 → 거부 확인
- Rate limit 초과 → 429/차단 확인
- 프로토콜 위반 프레임 → 안전한 연결 종료 확인

**6) 커버리지 측정 범위 확대**

`vitest.config.ts`의 coverage exclude에서 점진적으로 제거:

```typescript
// Phase 1: gateway 핵심 로직 포함
// Phase 2: agents 핵심 로직 포함  
// Phase 3: channels 핵심 로직 포함
```

현재 제외 중인 디렉토리들이 프로젝트의 가장 복잡하고 위험한 코드를 포함하고 있어, "커버리지 70%"라는 수치가 실질적 안전망을 과대 표현하고 있습니다.

---

### 요약 우선순위

1. **gateway WebSocket 핸들러** (`message-handler.ts`) 인증/권한 경로 단위 테스트 추가
2. **cron timer** 상태 전이 + backoff/retry 경계값 테스트 추가  
3. **커버리지 측정 범위**에서 `src/gateway/`, `src/agents/` 제외 해제
4. iOS/macOS 앱 코드에 XCTest 도입 (TLS, 디바이스 페어링)
5. Mock fixture 표준화 리팩토링으로 테스트 유지보수 비용 절감
