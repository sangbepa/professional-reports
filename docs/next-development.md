# professional reports 다음 개발계획

기준은 main `dd676c0d6453015d00c7efd485549f34895c1664`, 공개 릴리스 `0.4.0-dev.2`다. 이벤트 원장·상태 복원·입력 무효화·작업별 인계·독립 검토는 이미 구현돼 있다. 다음 목표는 공식 공시·웹 원문·대체 데이터를 활용하는 조사 조직으로 이 계약을 실제 보고서 완성까지 연결하고 측정된 반복 작업을 줄이는 것이다.

## 이번 변경과 확인 범위

`package/`와 기존 설치본은 변경하지 않는다. 공개 회귀시험과 기존 `pr.performance`를 고정 설치본에서 실행하는 저장소 런처를 추가한다. 새 시험은 과거 822개 시험의 복사가 아니라 공개 코드와 합성 입력으로 작성한 계약 시험이다. 네 라이브러리·디자인·보호된 기준·기존 원장과 판정은 유지한다.

| 영역 | 기존 구현 | 이번 추가 | 다음 증거 |
|---|---|---|---|
| 실행 | `package/pr/engine.py` | `tests/contracts/check_engine.py` | 실제 정상·실패·재개 흐름 |
| 호스트 | `package/pr/native.py` | `tests/contracts/check_native.py` | 실제 worker와 reviewer 영수증 |
| 맥락과 종료 | `package/pr/sessions.py` | `tests/contracts/check_sessions.py` | 실제 읽기량과 종료 관측 |
| 병목 | `package/pr/performance.py` | `scripts/profile-run.py`, `tests/contracts/check_performance.py`, `tests/test_profile_run.py` | 원래 원장 및 당시 릴리스 |
| 인수 | 기존 평가·시간 계약 | 변경 없음 | 경제적 품질·전체 시각 검토·전달·600초 동시 통과 |

합성 영수증은 fixture에 명시되며 실제 모델이나 독립 전문가를 실행하지 않는다. 부분 개발 계획은 전체 보고서 의무를 충족하지 않는다. 시험 pass는 전문적 판단이나 보고서 인수가 아니며 공개 시험은 비공개 holdout이 아니다.

## 공개 회귀시험

기존 setup 이후 저장소 루트에서 실행한다.

```bash
PYTHONDONTWRITEBYTECODE=1 .runtime/python/bin/python -m unittest discover -s tests -v
```

`tests/test_contracts.py`는 임시 state에 immutable 릴리스를 새로 설치하고 활성화 없이 각 suite를 별도 interpreter로 실행한다. 내부 시험은 `tests/contracts/check_*.py`에 있다. CI도 같은 명령을 사용한다. 고정 문서 `native-handoff.md`와 `performance-profiler.md`가 가리키는 예전 시험 파일은 공개판에 없으므로 위 명령을 사용한다. 고정 문서를 덮어쓰지 않는다.

시험은 이벤트 복원·변조 거부, 입력 변경 후 과거 승인 재사용 거부, 자기 승인 거부, 중대 지적이 남은 pass 거부, 일반 pass로 지적 자동 종결 거부, 명시적 종결과 반증에 의한 재개방, timeout으로 실행 점유 해제 거부, 오래된 hash·경로 탈출·필수 검사 누락·중복 제출 거부와 기한 뒤 성공 선언 차단을 검사한다.

`Run.outstanding_attempts()`의 실행 점유와 `close_session()`의 실제 종료 관측은 별개다. 결과 제출이나 wait 완료로 엔진 점유가 끝나도 호스트 슬롯이 닫힌 것으로 간주하지 않는다. 호스트는 종료 미확인 worker까지 별도로 세어야 한다.

## 실제 호스트 최소 시험

먼저 작은 텍스트 산출물로 실제 host schema를 확인한다. 현재 환경은 `collaboration.spawn_agent/send_message/wait_agent/interrupt_agent/list_agents`를 제공하지만 `multi_agent_v1` transport와 실제 close 도구는 제공하지 않는다. `fork_turns="none"`의 존재만으로 `fork_context=false`와 종료 계약의 호환성을 입증하지 않는다. 설치본 `pr.native`는 `multi_agent_v1.spawn_agent` 또는 bridge 별칭 영수증만 허용한다. 이름을 바꾼 영수증으로 통과시키지 않는다. 현재 실제 최소 시험은 capability insufficient이며 not run이다.

호환 호스트에서 다음을 관측한다.

1. 설치본 verify, 실제 tool metadata·worker 한도·요청 model/effort를 보존한다.
2. 부분 개발 요청과 텍스트 계획을 등록한다. dispatch의 attempt·brief hash·result directory를 그대로 사용한다.
3. task packet으로 실제 worker를 생성하고 원본 spawn 응답·요청·시각을 저장한다. `pr.native.bind_spawn()`으로 연결한다.
4. 실제 완료 대기 후 worker의 파일·검사만 `submit_template()`로 제출한다. timeout은 완료나 종료가 아니다.
5. 현재 대상 hash를 의존관계에 포함한 별도 reviewer를 새로 생성·연결·대기·제출한 뒤 `review_template()`로 기록한다.
6. 실제 close를 각각 호출하고 원본 성공 영수증을 `pr.sessions.close_session()`에 연결한다. 오류와 미확인 종료는 그대로 기록한다.

잘못된 대상 hash 거부, 실제 wait timeout 후 동일 작업 재대기, 실제 close 실패·도구 부재도 확인한다. 합성 fault injection과 실제 host 실패를 분리한다. 호환성 수정이 필요하면 새 버전·hash의 후보를 만들어 미래 실행에만 사용한다. 기존 설치본과 run pin은 고치지 않는다.

## 기존 원장으로 병목 측정

`package/docs/package-status.json`은 종료 위치 요약과 원래 기록의 경로·hash를 제공한다. 현재 환경에는 원래 `events.jsonl`이 없어 단계별 병목·입력량·실제 추론시간·검토 단축 효과는 unknown이다. 종료 위치 집계는 소요시간이나 실패확률이 아니다.

원장과 당시 릴리스에 접근할 수 있을 때 실행한다.

```bash
python3 scripts/profile-run.py --run /absolute/existing-run --out outputs/profile-new.json
```

런처는 `run.json`의 `package_root`를 선택하고 별도 interpreter에서 verify와 `_check_pin()` 후 기존 `profile_run()`을 실행한다. 원래 릴리스나 profiler가 없으면 실패로 반환하며 오늘의 활성 버전으로 대체하지 않는다. Python 의존성과 당시 릴리스의 호환성도 별도로 확인해야 한다. 출력은 새 파일로 run·package·고정 릴리스 바깥에 둔다. header/ledger hash, release hash, 관측 event prefix를 보존한다. 분석 도중 header/ledger가 바뀌면 저장하지 않고 안정된 snapshot에서 다시 실행한다.

dispatch→결과, binding→결과, 검토 대기, 검토 worker 실행, 재시도와 실패를 분리한다. 경과시간은 모델 compute가 아니며 interval union과 duration sum도 다르다. 후보마다 원장 hash·attempt·관측 구간·반증 조건을 연결한다. 모델·원문·cutoff·cache·동시성이 다른 실행은 효과 비교로 해석하지 않는다. 계측 없는 token·반복 읽기량은 unknown이다.

## 반복 처리와 검토 개선

기존 `pr.native`의 준비 함수와 `pr.sessions`의 원문·인계 helpers를 재사용한다. 코드가 ID·hash·경로·필수 필드·제출 형식을 연결하고 에이전트는 원문 선택·경제적 가정·과업 계획·반증을 판단한다. 전체 설치본 검증이나 원장 재읽기를 줄이는 변경은 측정 근거와 무결성 시험을 먼저 확보한다. 이번 변경은 무결성 cache나 새 framework를 도입하지 않는다.

통과 검토는 scope·현재 target hashes·실제 required checks·evidence references를 남긴다. 문제가 있으면 stable finding ID·severity·위치·근거·필요한 수정·종결 조건을 남긴다. `resolutions`와 `reopenings`를 생략하지 않는다. 이 표현은 앞으로 비교할 후보이며 입력·출력·재작업·경과시간 개선 효과는 미입증이다. 다수결 UI는 protected quality gate를 대신하지 않는다.

주식 종류별 권리·소유자 현금흐름, 장기 재투자, 투자회사 청구·초과현금 조정은 원문→판단 또는 미해결 사항→모델 위치→독립 검토→종결 조건으로 연결한다. 미통과 경제적 결론을 확정 본문으로 먼저 쓰지 않는다. 안정된 부분은 의존관계가 허용하는 범위에서 진행한다.

## 웹 원문과 대체 데이터 조사 목표

공식 API가 없거나 접근에 실패하면 조사 질문별로 다른 근거를 찾는다. OpenDART 인증 실패는 해당 API 경로의 제약으로 기록하고, 접근 가능한 DART 원문·기업 IR 보고서·거래소·공공통계·기업 및 산업 웹 원문으로 가능한 작업을 이어간다. 실제 수집 경로를 각각 기록한다. HTTP 200만으로 필요한 자료가 확보됐다고 판정하지 않는다.

| 자료 | 활용할 질문 | 적용 한계 |
|---|---|---|
| 공시 원문·감사보고서·기업 IR·거래소 | 재무 실적, 자본구조, 주식 권리, 회사 발표 | 공시·감사·회사 주장 및 문서 범위를 구분한다 |
| 공공통계·산업협회·시장 원문 | 수요, 가격, 산업 규모, 경기와 경쟁 | 정의·기간·지역·통화·발표일을 맞춘다 |
| 제품 가격·유통 재고·채용·무역 통계 등 대체 데이터 | 가격 압력, 공급·수요 변화, 사업 확장 가설 | 모집단·표본 편향·측정 변경과 추정 관계를 설명한다 |
| 뉴스·분석·이용자 리뷰 등 2차 자료 | 원문 발견, 반증 탐색, 보조 정황 | 재인용을 독립 관측으로 세지 않고 사실과 의견을 구분한다 |

기존 `evidence-researcher`, `source-critic`, `accounting-reconciler`, `industry-specialist` 및 `report-research-plan`, `report-source-assess`, `report-evidence-extract`, `report-data-reconcile`을 설치본에서 필요한 범위만 resolve한다. 새 persona·RAG·vector DB·agent framework는 추가하지 않는다. 아래 순서는 조사 인계 기준이며 과업별 계획을 하나의 고정 workflow로 대체하지 않는다.

1. 판단 질문과 뒤집힐 수 있는 경제적 쟁점을 정의한다. 필요한 지표·원문·접근 경로·실패 시 대체 후보를 질문에 연결한다.
2. 실제 원문을 `package/` 밖에 보존한다. URL·발행자·제목·발표일과 증거·수집시각·대상 기간·정확한 위치·실제 byte hash·수집 경로를 연결한다. 검색 snippet과 요약은 탐색 단서이며 원문을 대신하지 않는다.
3. 원문 사실·대체 데이터 관측·해석·모델 가정·미확인 사항을 구분한다. 현재 `source` schema의 `purpose`인 `valuation-input`, `context`, `benchmark`는 유지하고 추가 성격은 metadata나 연결된 evidence packet으로 기록한다. source admissibility와 실제 검토를 거쳐 사용 범위를 정한다.
4. 기준일 뒤에 발표된 자료를 과거 정보집합에 넣지 않는다. 발표 시점 미확인은 현재 cutoff 검사에 따라 적격으로 선언하지 않는다. 원문 충돌·재인용·단위와 연결 범위를 대조한다.
5. 대체 지표를 매출·마진·성장률 등에 반영하려면 측정 방식·표본·경제적 연결·보정이나 추정·반증·민감도·결론의 한계를 제시한다. 채용 증가를 매출 증가로 바로 치환하거나 리뷰 수를 판매량으로 취급하지 않는다. 직접 대체가 성립하지 않으면 맥락이나 교차검증에만 사용한다.
6. 독립 source 및 경제적 검토에 현재 원문과 모델 hash를 전달한다. 대체 자료로 중대 공백을 해결할 수 없으면 해당 결론을 제한하거나 미완료로 남기고 영향 없는 작업은 계속한다. 주식의 법적 권리 등 필요한 직접 근거를 정황으로 확정하지 않는다.

다음 실제 조사 시험은 한 기업의 질문별 evidence packet을 만들어 웹 원문의 locator·발표시점·hash를 확인하고, 대체 데이터 관측 하나의 적용 가능성 또는 거부 이유를 독립 검토로 남긴다. 접근 실패 후 대체 경로, 충돌 원문, 기준일 이후 자료 제외, 모델 입력 연결을 확인해야 완료된다. 실제 기업 조사 및 효과 검증은 아직 not run이다. 부분 조사 시험을 전체 인수나 기존 FDD·ESG 실행 지원 확대라고 표시하지 않는다.

## 작업 순서와 완료 기준

조사 조직의 목표는 공식 공시·웹 원문·대체 데이터를 판단 질문에 맞게 선택하고, 근거와 한계를 검토해 모델과 보고서에 연결하는 것이다. 웹 조사 목표도 실제 호스트 및 전체 인수 검증에 포함한다.

| 순서 | 작업 | 완료 기준 | 이번 상태 |
|---|---|---|---|
| 1 | 공개 회귀시험 | 깨끗한 설치에서 정상·거부·기한 계약 재현 | suite 추가, 검증 요약 참조 |
| 2 | 실제 worker·reviewer·close | 원본 영수증·독립 actor·정확한 대상·종료 연결 | 호스트 capability 부족, not run |
| 3 | 과거 원장 분석 | 중단 위치와 소요 원인 분리, 후보별 관측 근거 | 런처 검증, 원래 원장 분석 not run |
| 4 | 반복 처리 최소 변경 | 측정된 병목만 개선, 핵심 회귀 유지 | 근거 확보 전 최적화 보류 |
| 5 | 간결 검토와 조기 쟁점 검토 | 증거·검사·지적 연속성 유지, 비교 측정 | 후보 정의, 효과 unknown |
| 6 | 전체 보고서 인수 | 기존 품질·600초·실제 전달 동시 통과 | not run, provisional gate 유지 |

요청 접수부터 조사·분석·집필·검토·렌더링·전달까지 600초, 기본 작업 종료 585초와 보존·전달 15초를 유지한다. 300초는 희망 목표다. 개발 모드 전체 benchmark도 `report_benchmark.enabled=true`를 사용한다. 허용된 전역 환경 대기만 원래 규칙으로 제외한다. 후보를 먼저 고정하고 보호 기준·별도 독립 품질평가·finish 조건을 유지한다. 부분 진단이나 smoke를 전체 인수로 재분류하지 않는다.

## Codex에 전달할 Goal

> 기존 네 라이브러리·디자인·독립 검토·보호 기준을 유지하며 공식 공시·웹 원문·대체 데이터를 질문에 맞게 활용하는 조직을 목표로 한다. 사실·관측·추정·가정을 구분하고, API 접근 실패 시 대체 경로로 가능한 작업을 이어가되 cutoff·근거의 적격성·경제적 연결·독립 검토를 유지한다. 실제 실행과 전체 보고서 인수를 연결한다. 공개 회귀시험을 먼저 실행한다. 호환 host에서 worker→reviewer→close의 작은 텍스트 시험과 오류 경로를 관측한다. 접근 가능한 기존 원장은 그 원장의 고정 릴리스로 read-only profiling한다. 관측 근거가 있는 반복 처리만 기존 native/sessions/performance로 최소 변경한다. 검토는 scope·target hashes·증거·필수 검사·중대 지적·지적별 종결을 유지하면서 간결하게 한다. 경제적 중대 쟁점의 원문 확인과 독립 검토를 집필 전에 연결한다. 후보 고정 뒤 기존 품질과 600초로 전체 인수를 측정한다. 기존 설치본·원장·판정은 수정하지 않는다. 실제 실행·속도·품질은 관측한 범위만 보고하고 미완료는 정확한 사유와 함께 보존한다.

실행 결과는 [public-contract-verification.json](public-contract-verification.json)에 요약한다. raw log와 runtime 산출물은 Git 제외 `outputs/`에 두고 자격증명은 환경 secret으로만 공급한다.
