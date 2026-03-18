# 테스트 작성

## 프로젝트 컨텍스트
- 프로젝트: openclaw
- 언어: javascript
- 프레임워크: express
- 아키텍처: unknown
- 레이어: N/A
- 테스트 프레임워크: vitest

- 테스트 프레임워크: vitest

## Deep Analysis: 테스트 전략
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
- `audit.test.ts`의 `hasFinding()`, `expectFinding()`, `expectNoFinding()` 같은 도메인 특화 asser


## 작업
아래 요구사항에 대한 테스트를 작성하세요:
- 단위 테스트 (핵심 비즈니스 로직)
- 통합 테스트 (API 엔드포인트)

{requirements}
