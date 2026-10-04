# professional-reports

**Codex가 전문 업무를 수행하도록 조직·전문가·스킬·실행환경을 제공하는 개발 패키지.** 이 저장소를 내려받아 실행환경을 준비하면 Codex가 설치본을 고정하고 자료 조사, 분석, 보고서 작성과 검토를 수행할 수 있습니다.

현재 공개판은 **`0.4.0-dev.2`**입니다. 설치·계산 기능의 검증과 전문 보고서 전체 품질·600초 달성은 구분합니다. 전체 보고서 인수는 아직 미통과입니다.

## 빠른 시작

Python **3.11 이상**이 필요합니다. PDF에는 Node.js **20 이상**, npm, Chromium이 필요하고 Excel 재계산에는 LibreOffice가 필요합니다.

```bash
git clone https://github.com/sangbepa/professional-reports.git
cd professional-reports
python3 scripts/setup.py --activate-development
python3 scripts/verify.py
python3 scripts/pr.py catalog
python3 scripts/pr.py doctor
```

설치 스크립트는 `.runtime/`에 의존성, `.state/`에 불변 설치본과 실행 상태를 만듭니다. `package/` 안에 가상환경이나 결과 파일을 만들지 않습니다. 다른 프로젝트의 Codex 설정·활성 버전은 변경하지 않습니다. `--activate-development`는 이 프로젝트의 개발 버전을 선택하는 명시적 옵션입니다. 설치만 하려면 해당 옵션을 빼세요.

그다음 이 저장소를 **Codex 작업공간으로 열고** 다음과 같이 요청합니다.

> 루트 AGENTS.md를 읽고 설치된 professional-reports의 버전과 해시를 확인해. LG전자 valuation 보고서를 만들어줘. 평가 기준일은 내가 지정한 날로 하고, 원문과 가정을 구분해서 검토해. 제공된 기존 디자인을 사용해.

평가기준일은 실제 요청에서 명확히 지정해야 합니다. CLI는 로딩·검증·계산·기록을 담당하고, 업무 선택·조사·경제적 판단·집필은 Codex 에이전트가 수행합니다.

## Codex Cloud에서 사용하기

1. Codex의 **Work in → Cloud → Create environment**에서 이 GitHub 저장소를 선택합니다.
2. 환경 준비 대화에 아래 지침을 전달합니다.

   > 이 저장소의 README와 AGENTS.md를 읽어. Python 3.11 이상과 Node 20 이상을 준비하고 `bash scripts/cloud-setup.sh`를 실행해. `python3 scripts/verify.py`와 합성 Excel/PDF smoke 시험을 통과시켜. 필요한 네트워크·공시 API 접근을 설정하고 환경을 Publish할 준비 상태를 보고해.

3. 준비 결과를 확인하고 **Publish**합니다. 새 클라우드 작업에서 패키지를 호출합니다. 저장소 업로드만으로 사용자 계정의 클라우드 환경이 생성되지는 않습니다.

Ubuntu/Debian 기반 준비 환경에서는 다음 명령이 LibreOffice, Python 의존성, Playwright·Chromium을 준비합니다. 시스템 설치에는 root 또는 sudo 권한이 필요합니다.

```bash
bash scripts/cloud-setup.sh
python3 scripts/smoke.py --render --out outputs/setup-smoke
```

[현재 Codex Cloud 환경 안내](https://learn.chatgpt.com/docs/environments/cloud-environments)에 따른 절차입니다. 다른 Linux나 macOS 환경에서는 해당 운영체제에 LibreOffice를 먼저 설치하고 아래 명령을 사용합니다.

```bash
python3 scripts/setup.py --activate-development --with-browser
python3 scripts/smoke.py --render --out outputs/native-smoke
```

### 자료 조사 접근과 키

- Python 설치: `pypi.org`, `files.pythonhosted.org`.
- Node 설치: `registry.npmjs.org`, Playwright가 사용하는 Chromium 다운로드 호스트.
- 국내 공시: `opendart.fss.or.kr`, `dart.fss.or.kr`; 시장·기업 자료는 실제 선택한 원문 도메인.
- `OPENDART_API_KEY`는 클라우드 환경의 개인 변수 또는 해당 HTTPS 서비스용 network secret으로 공급합니다. network secret의 placeholder를 사용하는 경우 실제 OpenDART HTTPS 요청이 프록시에서 치환되는지 확인해야 합니다. 키를 파일·프롬프트·Git에 넣지 않습니다.

[클라우드의 변수·network secret 및 네트워크 설정](https://learn.chatgpt.com/docs/environments/cloud-environments#configure-environment-variables-and-network-secrets)을 확인하세요. 설치 성공만으로 원문 API 접근을 확인했다고 기록하지 않습니다.

## 작동 확인

```bash
# Python만으로 조건부 모델·HTML·수식 Excel 확인
python3 scripts/smoke.py --out outputs/basic-smoke

# 실제 Excel 재계산·저장·재열기와 PDF 생성
python3 scripts/smoke.py --render --out outputs/full-smoke

# 설치한 CLI의 실제 인터페이스
python3 scripts/pr.py --help
```

smoke는 **합성 시험 입력**입니다. 실제 기업 가치평가나 금융적 타당성 검토를 뜻하지 않습니다. 출력 폴더는 매번 새 경로를 사용합니다. [GitHub Actions](https://github.com/sangbepa/professional-reports/actions)는 Ubuntu에서 설치·런처 검사·native smoke를 수행합니다.

전문 보고서는 실제 Codex 서브에이전트 생성·대기·종료 도구와 독립 검토가 필요합니다. 해당 클라우드 호스트가 이를 제공하는지 확인하고, 없으면 능력 부족으로 기록합니다. 메인 세션의 자기 검토를 독립 검토로 표시하지 않습니다.

## 패키지 구성

| 라이브러리 | 개수 | 역할 |
|---|---:|---|
| 오케스트레이션 | 8 | 업무 체계 선택·합성, 계약·정책·검사 규칙 |
| 전문가 페르소나 | 13 | 역할·판단·협업·검토 책임 |
| 스킬 | 31 | 작업 방법·입출력·수락 조건 |
| 실행환경 | 2 | 지원 능력·호스트 연결·세션 정책 |

```text
AGENTS.md                   Codex의 클라우드/로컬 진입 지침
scripts/                    설치·검증·고정된 설치본 실행
package/                    해시로 고정된 공개 개발 릴리스
  libraries/                네 라이브러리
  pr/                       계획·원장·패키지·실험 관리
  adapters/valuation/       기업 독립 계산·Excel·HTML·PDF
  protected/                사용자 공개 승인한 평가 기준·검토 프로필
marketplace/                선택적으로 설치할 로컬 플러그인 진입점
runtime-node/               Playwright 의존성·lock 파일
.github/workflows/          Ubuntu 설치·native 산출물 smoke
.runtime/ .state/ outputs/   생성되는 로컬 상태; Git 제외
```

플러그인 UI 설치 없이도 루트 `AGENTS.md`와 스크립트로 설치본을 로드할 수 있습니다. [공식 로컬 플러그인 구조](https://developers.openai.com/plugins/build/plugins)를 사용하는 진입점도 `marketplace/`에 있습니다.

## 현재 검증 수준과 다음 과제

- 로컬 원래 스냅샷: 전체 **822개 시험 통과**, 이동 설치·활성화·복구·변조 차단, 합성 Excel 재계산 및 PDF 생성 확인. [원래 검증 요약](docs/local-verification.json).
- 공개판은 회사별 기존 모델·원문·개인 경로를 제외한 별도 해시입니다. 이 공개판의 실행 증거는 [cloud-readiness.json](docs/cloud-readiness.json)과 GitHub Actions 결과로 확인합니다.
- 과거 LG전자 31회 실행은 모두 incomplete입니다. 27회는 단계별 시간 제한으로 중단됐고, 완성 시간 기준선은 아직 없습니다.
- valuation의 전체 품질·600초 인수는 미통과입니다. FDD는 계획 능력, 일반 ESG orchestration도 계획 능력입니다. 별도 ESG 학습 어댑터를 전문 ESG 전체 업무로 표시하지 않습니다.
- 공개 시험 사례는 비공개 holdout의 대체물이 아닙니다. 다음 과제는 경제적 중대 지적을 해결한 전체 보고서 완성과 실제 완성 시간·반복 편차 측정입니다.

상세 상태: [package-status](package/docs/package-status.md), [세션 계약](package/docs/session-workflow.md), [위험·비용](package/docs/risk-workflow.md).

## 공개 계약 회귀시험과 다음 개발

이벤트·입력 변경·검토 독립성·지적 종결과 재개방·native 제출·세션 종료·기한·profiler의 공개 합성 회귀시험을 실행합니다. 계약 suite는 임시 state에 릴리스를 새로 설치하고 별도 Python 프로세스로 사용합니다. 기존 프로젝트 활성 버전과 immutable 릴리스는 변경하지 않습니다.

```bash
PYTHONDONTWRITEBYTECODE=1 .runtime/python/bin/python -m unittest discover -s tests -v
python3 scripts/profile-run.py --run /absolute/existing-run --out outputs/profile-new.json
```

profiler는 해당 실행의 `run.json`에 고정된 릴리스를 사용하며 기존 원장을 수정하지 않습니다. 원래 릴리스가 없으면 현재 활성 버전으로 대체하지 않습니다. 합성 영수증 시험은 실제 native worker 실행이나 전문 보고서 인수가 아닙니다.

파일별 변경·실제 host 시험 절차·병목 측정·완료 기준: [다음 개발계획](docs/next-development.md). 실행 결과와 미확인 항목: [공개 계약 검증 요약](docs/public-contract-verification.json). 과거 822개 시험의 재실행이나 전체 품질·600초 통과를 주장하지 않습니다.

## 보호된 평가 자료

사용자가 보호된 평가 사례·검토 프로필·승인 기록 12개 파일의 공개를 명시적으로 승인했습니다. 기존 평가 기준은 그대로 포함합니다. 공개된 평가 자료를 새로운 비공개 holdout으로 취급하지 않습니다. 이 공개 승인은 보고서 품질이나 생산 릴리스의 승인을 뜻하지 않습니다. 관련 범위는 [publication-scope](docs/publication-scope.json)에 기록합니다.

## 업데이트와 복구

새 릴리스는 새 버전·해시로 배포합니다. 진행 중인 실행은 시작한 설치본을 고정합니다. 업데이트 후 `scripts/setup.py --activate-development`를 다시 실행하고 `scripts/verify.py`의 버전·해시를 확인하세요.

```bash
python3 scripts/pr.py rollback --state "$PWD/.state"
python3 scripts/verify.py
```

복구할 이전 활성 버전이 있어야 합니다. 원문·실행·실험 기록을 삭제하지 않습니다. `package/`를 직접 고쳐 기존 릴리스 해시를 덮어쓰지 않습니다. 포함한 상위 스킬·폰트의 라이선스 고지는 해당 디렉터리에 보존돼 있습니다.
