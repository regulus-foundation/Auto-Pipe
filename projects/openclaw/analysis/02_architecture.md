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
   ```typescript
   // extensions/telegram/src/bot-handlers.ts
   export const registerTelegramHandlers = ({
     cfg, accountId, bot, opts, telegramTransport, runtime, ...
   }: RegisterTelegramHandlerParams) => {
   ```

**Swift:** **Protocol + Init 주입** 패턴
```swift
// apps/ios/Sources/Model/NodeAppModel.swift
init(
    screen: ScreenController = ScreenController(),
    camera: any CameraServicing = CameraController(),
    locationService: any LocationServicing = LocationService(),
    notificationCenter: NotificationCentering = LiveNotificationCenter(),
    // ... 10개 이상의 프로토콜 기반 주입
)
```

### 응답/공통 패턴

- **Gateway 프로토콜:** `RequestFrame`, `ResponseFrame`, `EventFrame` 구조 (`GatewayModels.swift`)
  - `ResponseFrame.ok: Bool` + `payload/error` 패턴
  - 프로토콜 버전 관리: `GATEWAY_PROTOCOL_VERSION = 3`
- **에러 코드 열거형:** `ErrorCode` enum (`NOT_LINKED`, `NOT_PAIRED`, `AGENT_TIMEOUT` 등)
- **JSON RPC 스타일:** `{ type: "request", id, method, params }` → `{ type: "response", id, ok, payload }`

### 예외 처리 방식

**글로벌 핸들러:**
```typescript
// src/index.ts
installUnhandledRejectionHandler();
process.on("uncaughtException", (error) => {
  console.error("[openclaw] Uncaught exception:", formatUncaughtError(error));
  process.exit(1);
});
```

**Per-function 가드 패턴 (지배적):**
```typescript
// src/cron/service/timer.ts — 에러를 문자열로 변환하여 상태에 기록
function isTransientCronError(error: string | undefined, retryOn?: CronRetryOn[]): boolean {
  // 정규식 기반 에러 분류
  const keys = retryOn?.length ? retryOn : (Object.keys(TRANSIENT_PATTERNS) as CronRetryOn[]);
  return keys.some((k) => TRANSIENT_PATTERNS[k]?.test(error));
}
```

**Swift:** `do/catch` + 로거 조합, 실패 시 `nil` 반환 또는 `Result<T, Error>` 사용

### 검증/유효성 검사 방식

- **런타임 타입 가드 함수:** `isSessionStoreRecord()`, `isFiniteTimestamp()`, `isRecoverableMediaGroupError()`
- **TypeBox 스키마:** 도구 정의에 `Type.Object({ query: Type.String(), ... })` 사용 (`web-search-core.ts`)
- **Assert 함수:** `assertSupportedJobSpec()`, `assertDeliverySupport()`, `assertMainSessionAgentId()` — 유효하지 않으면 `throw new Error`
- **Normalize 패턴:** 입력을 정규화하는 함수가 매우 많음 — `normalizeAllowEntry()`, `normalizeStoreSessionKey()`, `normalizeCronMessageChannel()`, `normalizeHttpWebhookUrl()`

---

## 3. 코드 품질

### 강점

1. **방어적 프로그래밍이 철저함:** `clampPositiveInt()`, `clampNonNegativeInt()`, `coerceFiniteScheduleNumber()` 등 모든 숫자 입력에 대해 NaN/Infinity/음수 가드가 적용됨. Windows 파일 시스템의 비원자적 쓰기까지 고려한 재시도 로직 (`store.ts:171-189`)

2. **멀티 플랫폼 일관성:** TypeScript 서버와 Swift 클라이언트 간 프로토콜을 코드 생성으로 동기화 (`GatewayModels.swift` 상단의 "Generated by scripts/protocol-gen-swift.ts — do not edit by hand"). `ConnectParams`, `HelloOk`, `ResponseFrame` 등이 양쪽에서 동일 구조

3. **보안 의식 높음:** 프록시 헤더 스푸핑 방지 (`message-handler.ts:143-157`), 브라우저 오리진 체크, 디바이스 서명 검증, TLS 핑거프린트 TOFU, Rate limiting, SSRF 정책 등이 게이트웨이 레벨에서 체계적으로 구현

4. **Cron 엔진의 복원력:** 지수 백오프 (`DEFAULT_BACKOFF_SCHEDULE_MS`), 일시적 오류 감지 (`TRANSIENT_PATTERNS`), 연속 실패 알림 (`emitFailureAlert`), 재시작 시 missed job catch-up 등 운영 환경을 깊이 고려

5. **테스트 가능한 설계 (Swift):** `any CameraServicing`, `any LocationServicing` 등 모든 외부 의존을 프로토콜로 추상화하여 테스트 시 mock 주입이 용이

### 약점

1. **파일/함수 크기 과대:** `bot-handlers.ts`의 import만 68줄이고, `registerTelegramHandlers`는 하나의 클로저 내에 debounce, media group buffering, text fragment buffering, callback query handling 등이 모두 밀집. `NodeAppModel.swift`는 `type_body_length file_length` swiftlint 규칙을 비활성화할 정도로 거대. 분리 지점이 명확함에도 단일 파일에 유지

2. **타입 안전성 우회:** `as` 캐스팅과 `Record<string, unknown>` 사용이 빈번
   ```typescript
   // bot-handlers.ts
   const forwardMeta = msg as {
     forward_origin?: unknown;
     forward_from?: unknown;
     // ...
   };
   ```
   ```typescript
   // session-tool-result-guard.ts
   sessionManager.appendMessage = guardedAppend as SessionManager["appendMessage"];
   // Monkey-patch
   ```

3. **횡단 관심사의 명시적 경계 부재:** `bot-handlers.ts`가 `config`, `sessions`, `pairing`, `routing`, `plugins`, `auto-reply`, `media` 등 거의 모든 내부 모듈을 직접 import. 중간 서비스 계층(facade)이 없어서 변경 영향 범위가 넓음

4. **Magic number/string 산재:** `1500`(텍스트 프래그먼트 갭), `4000`(프래그먼트 시작 임계), `50_000`(최대 총 문자), `2 * 60 * 60 * 1000`(stuck run) 등이 상수로 추출되었으나, 연관 상수 간의 관계나 의미가 주석 없이는 파악하기 어려움

### 보안 우려사항

- `monkey-patch` 패턴(`sessionManager.appendMessage = guardedAppend`)은 타입 시스템을 우회하며, 다른 코드가 원본 참조를 보유할 경우 가드를 건너뛸 수 있음
- `SHELL_ENV_EXPECTED_KEYS` (`config/io.ts`)에 API 키 목록이 하드코딩되어 있어, 새 프로바이더 추가 시 누락 가능
- Keychain 저장소(`GatewaySettingsStore.swift`)에서 실패 시 반환값을 `@discardableResult`로 무시하는 경우가 있어 자격증명 저장 실패를 감지하지 못할 수 있음

### SOLID 원칙

| 원칙 | 준수 수준 | 근거 |
|------|----------|------|
| **S** (단일 책임) | **낮음** | `NodeAppModel`이 게이트웨이 연결, 카메라, 음성, 딥링크, 푸시 알림, 화면 녹화 등 모든 것을 관리 |
| **O** (개방-폐쇄) | **높음** | 플러그인/확장 시스템이 잘 설계됨. `extensions/*`로 새 채널 추가 시 코어 변경 최소화 |
| **L** (리스코프) | **해당없음** | 상속보다 합성 위주 설계로 위반 기회 자체가 적음 |
| **I** (인터페이스 분리) | **높음 (Swift)** | `CameraServicing`, `LocationServicing` 등 역할별 프로토콜 잘 분리 |
| **D** (의존성 역전) | **낮음 (TS)** / **높음 (Swift)** | TS는 구체 모듈 직접 import, Swift는 프로토콜 기반 추상화 |

---

## 4. 코드 생성 시 반드시 따라야 할 규칙

### 필수 패턴

1. **함수 네이밍 접두사 엄수:**
   - 조회/변환: `resolve*`, `compute*` — `resolveInboundMediaFileId()`, `computeJobNextRunAtMs()`
   - 생성/조합: `build*` — `buildSyntheticTextMessage()`, `buildCommandsMessagePaginated()`
   - 정규화: `normalize*` — `normalizeStoreSessionKey()`, `normalizeAllowEntry()`
   - 검증: `is*/has*/should*` — `isTransientCronError()`, `hasInboundMedia()`, `shouldDebounceTextInbound()`
   - 단언: `assert*` — `assertSupportedJobSpec()`, `assertDeliverySupport()`

2. **숫자 입력은 반드시 가드:**
   ```typescript
   // 이 패턴을 따를 것
   function clampPositiveInt(value: unknown, fallback: number): number {
     if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
     const floored = Math.floor(value);
     return floored >= 1 ? floored : fallback;
   }
   ```

3. **설정 관련 함수는 State/Deps 객체를 통해 의존성 수신:**
   ```typescript
   // CronServiceState 패턴을 따를 것
   function resolveRunConcurrency(state: CronServiceState): number {
     const raw = state.deps.cronConfig?.maxConcurrentRuns;
     // ...
   }
   ```

4. **파일 I/O는 atomic write + file lock:**
   - `writeTextAtomic()` (store.ts), `writeJsonFileAtomically()` (pairing-store.ts)
   - `withFileLock()` 으로 동시 접근 보호

5. **Swift 프로토콜 기반 DI:** 새 서비스 추가 시 반드시 `any XxxServicing` 프로토콜 정의 후 init 주입

6. **캐시에는 반드시 TTL과 무효화 메커니즘:**
   ```typescript
   // store.ts의 패턴: stat 기반 캐시 무효화
   const cached = readSessionStoreCache({
     storePath, ttlMs: getSessionStoreTtl(),
     mtimeMs: currentFileStat?.mtimeMs,
     sizeBytes: currentFileStat?.sizeBytes,
   });
   ```

7. **에러 메시지는 구조화된 문자열:** `"cron: job execution timed out"`, `"unknown cron job id: ${id}"` 형태로 컨텍스트 포함

8. **도구 스키마는 TypeBox, `Type.Union` 금지:**
   ```typescript
   // web-search-core.ts 패턴
   Type.Object({
     query: Type.String({ description: "Search query string." }),
     count: Type.Optional(Type.Number({ minimum: 1, maximum: 10 })),
   })
   ```

### 절대 하면 안 되는 것

1. **`@ts-nocheck` 또는 `no-explicit-any` 비활성화 금지** (CLAUDE.md 명시)

2. **Prototype mutation 금지:** `Class.prototype.method = ...` 대신 명시적 상속/합성 사용. `session-tool-result-guard.ts`의 monkey-patch는 레거시이며 새 코드에서는 허용하지 않음

3. **동일 모듈에 대해 `await import()` + static `import` 혼용 금지:** lazy loading 필요 시 `*.runtime.ts` 경계 파일 생성

4. **`Type.Union` / `anyOf` / `oneOf` / `allOf`를 도구 스키마에 사용 금지:** `stringEnum`/`optionalStringEnum` 사용

5. **`node_modules` 편집 금지**, **Carbon 의존성 업데이트 금지**

6. **하드코딩 색상 금지:** `src/terminal/palette.ts`의 공유 팔레트 사용

7. **스트리밍/부분 응답을 외부 메시징 채널에 전송 금지:** 최종 응답만 전달

8. **`process.env`를 직접 읽는 config 패턴 금지:** `loadConfig()` → `resolveConfigEnvVars()` 파이프라인을 통해야 함

9. **테스트 워커 16 초과 설정 금지** (CLAUDE.md: "tried already")

10. **`git stash`, `git worktree`, 브랜치 전환을 명시적 요청 없이 수행 금지** (멀티 에이전트 안전)
