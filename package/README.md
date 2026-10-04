# professional-reports

Codex 위에서 업무 체계·전문가·스킬·실행환경을 선택하고, 실제 수행과 검토를 기록하는 로컬 플러그인입니다. 현재 버전은 **0.4.0-dev.2 개발 스냅샷**입니다. 설치 가능 여부와 전문 보고서의 품질·600초 달성 여부는 별도의 인수 조건입니다. [현재 기능과 실제 검증 상태](docs/package-status.md), [빠른 시작](docs/valuation-quickstart.md)을 먼저 읽으세요.

## 구성

- `libraries/orchestrations`: 메타 선택과 합성, 업무 계약, 정책 조항, 검사 가능한 계획 규칙.
- `libraries/personas`: 책임과 관찰 가능한 판단·협업 행동.
- `libraries/skills`: 작업 방법과 입출력·수락 계약.
- `libraries/runtimes`: 도구 능력, 추론 배정, 호스트 연결 조건.
- `pr`: 패키지 로더, 원장, 계획 검사, 실제 호출 연결, 실험과 도식 생성.
- `protected`: 완료 기준과 독립 평가 자료. 후보 작성자가 변경하지 않습니다.
- `adapters/valuation`: 기업에 종속되지 않는 계산과 수정 가능한 모델·보고서 생성.
- `benchmarks`: 공개 현업 원본과 개발용 원문·출처. 과거 보고서 수치를 새 실행 결과로 취급하지 않습니다.

`benchmarks`, `development`, 사례별 검토 문서와 실행 결과는 소스 작업공간/상태 보관함에 남으며 설치 정의 묶음에 섞이지 않습니다. 배포 묶음에는 일반 사용·설치 안내와 불변 정의·실행 코드·자산을 포함합니다. 실제 검증 증거는 별도 인수 명세가 해시로 연결합니다.

루트 `AGENTS.md`와 진입 스킬은 메타 역할을 안내합니다. Python 명령은 판단을 대신하지 않습니다. 에이전트가 만든 메타 선택과 실행 계획을 검사하고, 실제 Codex 호출의 결과를 기록합니다.

## 실행

```sh
python3 -m pip install -r requirements.txt
python3 -m pr doctor
python3 -m pr catalog
python3 -m pr run --path /absolute/state/runs/new-run --request request.json
python3 -m pr meta --run /absolute/state/runs/new-run --file meta.json
python3 -m pr plan --run /absolute/state/runs/new-run --file plan.json
python3 -m pr next --run /absolute/state/runs/new-run
python3 -m pr dispatch --run /absolute/state/runs/new-run --node task-id --support host-support.json --out brief.json
```

그 다음 Codex가 **실제 native subagent**에 해당 brief를 전달합니다. `spawn_agent` 응답의 ID와 전달한 brief 해시를 `bind`에 기록하고, 해당 작업 디렉터리의 실제 결과만 `submit`으로 제출합니다. 작성자와 다른 실제 에이전트가 정확한 산출물 해시를 대상으로 검토한 뒤 `review`로 기록합니다. `status`, `export`, `finish`는 수행 사실과 미해결 조건을 구분합니다. 인자는 각 명령의 `--help`가 기준입니다.

의존관계상 독립적인 준비 완료 작업만 병렬 발행합니다. 선언한 상한은 6개이고 실제 호스트의 더 낮은 한도도 따릅니다. 지원되지 않는 추론 설정을 자동으로 바꾸지 않습니다. 새 설정이 필요하면 계획을 개정하고 새 호출로 이어갑니다.

## 설치본과 상태

```sh
python3 -m pr pack --out /absolute/build/release --version 0.1.0-dev.1
python3 -m pr verify --release /absolute/build/release
python3 -m pr install --release /absolute/build/release --state /absolute/user-state
python3 -m pr activate --state /absolute/user-state --release-id RELEASE_HASH --development
python3 -m pr load --state /absolute/user-state
python3 -m pr rollback --state /absolute/user-state
```

패키지 파일과 원문·실행·실험 상태를 분리합니다. 실행은 시작할 때 코드·스키마·정의·평가의 정확한 해시를 고정합니다. 원본 수정은 설치본이나 진행 중인 실행에 반영되지 않습니다. 로컬 플러그인으로 설치하는 절차는 [설치 안내](docs/installation.md)를 참조하세요.

공개 원문을 재구성하는 별도 ESG 학습 어댑터의 개발 의존성, 격리 설치와 실행 절차는 [ESG 학습 보고서 안내](docs/esg-learning.md)를 참조하세요.

## 검증 범위

`python3 -m unittest discover -s tests -v`는 조작·변경·중단·잘못된 배정에 대한 기계적 검사입니다. 테스트의 합성 입력과 합성 호출 영수증은 실제 기업 보고서나 실제 모델 호출이 아닙니다. 실제 보고서 인수에는 원문·계산·경제적 판단·문서의 독립 검토, 모든 페이지 검사, Excel 재계산·저장·재열기, 입력 변경 전파, 보정된 평가와 실행 시간을 추가로 확인합니다.

실행 원장은 협력하는 로컬 프로세스의 오류와 우발적 변경을 탐지합니다. 같은 파일 권한을 가진 관리자가 전체 원장과 호출 영수증을 위조하는 행위를 방어하는 보안 시스템은 아닙니다. 실제 호스트가 반환하지 않은 모델·비용·추론 정보는 미확인으로 남깁니다.

개선 후보는 사전 명세, 최소 3쌍 비교, 별도 과업 검증과 독립 승격 판정을 거칩니다. 불확실한 귀속과 효과 없음도 결과로 남깁니다. 현재 버전의 개발 기록 요약은 `docs/package-status.json`에 포함하고 원래 실행·원문 기록은 상태 보관함에 보존합니다. 패키지 전체의 전문 보고서 인수는 아직 미통과입니다.
