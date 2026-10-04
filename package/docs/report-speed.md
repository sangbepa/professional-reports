# 보고서 실행 시간과 패키지 개발 시간

사용자 지침: 패키지 개발과 필요한 환경 준비에는 시간을 쓸 수 있다. 준비된 패키지에 보고서를 요청한 뒤에는 600초 이내에 결과가 나와야 하며 300초는 희망 목표일 뿐이다. 품질 조건은 유지한다.

## 현재 구현

- `mode=report`는 항상 시간 제한을 적용한다. 개발·실험 모드로 전체 보고서 성능을 시험할 때도 `report_benchmark.enabled=true`로 같은 제한을 적용한다.
- 요청 접수 시각 `requested_at`부터 기록 생성 전 로딩·계획 시간까지 포함한다. 접수 시각은 호스트의 명시적 기록이며 임의로 재설정하지 않는다.
- 회사별 자료 수집·선별·분석·재작업·검토·렌더링·전달을 포함한다. 기존 엔진에서 허용하는, 모든 보고서 작업이 환경 때문에 대기한 구간만 제외한다.
- 기본 작업 종료 시점은 585초다. 남은 15초는 결과 보존과 전달을 위해 둔다. 300초는 목표이고 완료 기준을 낮추는 근거가 아니다.
- `python3 -m pr.budget watch --run RUN --receipt-out OUTPUT`은 기한 도달 시 실행을 봉인하고 실제 중단 대상 에이전트 목록을 반환한다. 호스트가 해당 에이전트를 중단하고 결과를 전달해야 한다. 감시기는 네이티브 에이전트 취소나 사용자에게 전달했다는 사실을 대신 주장하지 않는다.
- 봉인 뒤의 늦은 제출은 기존 보호 장치에서 거절된다. 미완료 산출물과 실패 기록은 보존된다.
- `pr.performance`는 임의의 계획 그래프, 직렬 경로, 병렬 중첩, 재시도별 경과시간, 인계 공백을 측정한다. 에이전트 경과시간을 실제 추론 연산시간으로 오인하지 않는다. 계획의 시간 추정은 실측 보장이 아니다.

개발 모드는 패키지 개발에 계속 사용한다. 기존 장시간 개발 실행을 사후에 10분 성공 사례로 바꾸지 않는다. 구현 후보는 아직 설치된 활성 릴리스에 반영하지 않았다.

## 재개할 작업

1. 새 기한 처리와 측정 코드를 독립 검토하고, 실제 환경에서 감시기·호스트 취소·전달을 연결한다.
2. 기존 계산·Excel 재계산·PDF 도구로 준비 상태를 고정한다. 불필요한 Docker/RAG 추가 설치를 시간 단축으로 가정하지 않는다.
3. 조사와 분석에 필요한 맥락을 작게 묶고, 독립 작업을 동시에 실행한다. 하나의 전문가가 여러 관련 스킬을 사용하며 실제 작업 그래프는 과업별로 작성한다.
4. 입력·모델·검토를 재사용하지 않는 보고서 시험에서 300/600초와 동일한 품질 기준을 함께 측정한다. 필요한 경제적 가정이나 중대한 자료가 빠지면 미완료로 반환한다.
5. 통제 비교와 개발에 사용하지 않은 과업에서 검증된 변경만 릴리스한다. 이번 구현 및 단위 시험은 보고서 속도나 전문 품질의 달성 증거가 아니다.

## Task-scoped sessions experiment — 0.2.0-dev.1

The approved development experiment has a total budget of 6,000,000 tokens and 1,800 seconds, with exactly three baseline/candidate comparison pairs whose round lengths are `[3, 6, 3]`, respectively. The middle pair runs six rounds; this does not mean six comparison pairs. Record actual aggregate usage and elapsed time across rounds, workers and parent coordination; unknown usage is not zero. Stop at either budget boundary, preserve evidence and report incomplete work honestly. This bounded experiment does not grant a 1,800-second report deadline: every full-report benchmark still enables `report_benchmark.enabled=true`, retains the 600-second ceiling and default 585-second work cutoff/15-second delivery reserve. The 300-second figure is aspirational, never an acceptance claim or permission to reduce quality.

Before measuring, freeze baseline/candidate identities, paired tasks and inputs, model/settings, concurrency, cache-accounting method, quality criteria and timing boundaries. Keep raw per-pair observations and aggregate totals, including retries, handoffs, review and integration. Run the approved round counts in order; do not stop selectively after favorable pairs. Record cached and uncached input separately. The experiment budget covers all rounds, not a fresh allowance per round.

Acceptance requires all of the following:

- At least two of the exactly three baseline/candidate pairs reduce input tokens by **strictly more than 5%**; remaining pairs stay within **±5%** of baseline. Register `min_pairs=3` and assign exactly three pairs; extra pairs require a separately authorized experiment. Use `(baseline - candidate) / baseline` for reduction and disclose undefined/zero-baseline measurements rather than treating them as passes.
- Uncached input tokens increase by no more than **5% in each pair and in the total**. Aggregate savings cannot hide a failing pair; do not replace raw totals with an average of percentages.
- Elapsed time increases by no more than **10%** against the comparable baseline; inspect both pairs and total so an aggregate cannot hide a regression. Report absolute deadline compliance separately.
- Quality, evidence-backed reopening and accepted-decision reversal outcomes show **no regression** under unchanged criteria. Retain all reopen/reversal evidence and distinguish justified counterevidence from avoidable repeated work; never suppress a valid finding to meet a metric.
- A held-out evaluation is required after candidate freezing, independently of development pairs. Keep protected cases/answers outside candidate authoring context. Missing or failing holdout/quality evidence blocks acceptance regardless of speed or token savings.

These are experiment gates, not results. Documentation, helper tests and plan estimates do not demonstrate them. Follow [session-workflow.md](session-workflow.md) for fresh task sessions and [performance-profiler.md](performance-profiler.md) for read-only timing diagnostics. Preserve actual parent-conversation measurements; a new logical role/session does not reset them.
