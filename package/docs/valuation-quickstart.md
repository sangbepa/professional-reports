# 개발 패키지 빠른 시작

Python 3.11 이상. 설치 전 `package-status.md`를 읽는다. 설치·활성화는 전문 보고서 인수를 뜻하지 않는다.

## 정의와 계산 도구 확인

압축을 푼 폴더의 `release/`에서 아래 명령을 실행한다.

```sh
python3 -m venv ../environment
../environment/bin/python -m pip install -r requirements-runtime.lock.txt
../environment/bin/python -m pr verify --release .
../environment/bin/python -m pr catalog
../environment/bin/python -m pr doctor
```

환경은 불변 릴리스 디렉터리 밖 `../environment`에 만든다. 릴리스에 새 파일을 넣으면 해시 검증이 실패한다. lock 파일은 이번 Python 검증 환경의 직접·간접 버전을 고정하며 실행환경 바이너리나 원격 다운로드를 동봉하지 않는다. 필요한 영역만 설치하려면 core `requirements.txt`, `adapters/valuation/requirements.txt`, `requirements-review.txt`를 구분해서 사용할 수 있다.

## 별도 상태 저장소에 설치

```sh
../environment/bin/python -m pr install --release . --state ../state
```

설치는 활성 버전을 바꾸지 않는다. 개발 버전을 사용하기로 명시적으로 선택한 경우 출력의 release_id로 아래 명령을 실행한다.

```sh
../environment/bin/python -m pr activate --state ../state --release-id RELEASE_HASH --development
../environment/bin/python skills/professional-reports/scripts/bootstrap.py --state ../state
../environment/bin/python -m pr load --state ../state
```

`load`와 bootstrap의 release_id·버전·root가 동일해야 한다. 실행 중에는 해당 root를 고정한다. 이전 활성 버전이 있으면 `../environment/bin/python -m pr rollback --state ../state`로 복구할 수 있다.

## 수식·산출물 작동 확인

```sh
../environment/bin/python adapters/valuation/build.py \
  --input adapters/valuation/examples/synthetic-stub.json \
  --out ../synthetic-smoke --xlsx-engine openpyxl --recalc required --pdf required
```

위 입력은 합성 시험용이며 LG전자나 현대차 평가가 아니다. LibreOffice의 실제 재계산·저장·재열기, Node·Playwright와 브라우저가 준비돼야 required 옵션이 통과한다. 렌더러는 기존 디자인과 동봉한 폰트를 사용한다. 현재 호스트 환경 탐색은 `adapters/valuation/README.md`에 설명돼 있다.

## 실제 전문 보고서 호출

Codex에서 진입 스킬에 선택한 상태 저장소를 지정하고 `LG전자 valuation 만들어줘` 같은 요청을 전달한다. 진입 스킬은 설치본을 검증하고 필요한 정의를 로드한다. 에이전트가 실제 자료 조사·판단·호스트 호출을 수행해야 한다. CLI가 보고서를 독립적으로 작성하는 시스템이 아니다. 국내 공시 수집에는 OPENDART_API_KEY를 실행 환경에 별도로 설정하며 키는 원문·패키지·영수증에 기록하지 않는다.

공식 로컬 플러그인 구조에 맞춘 진입점은 배포물의 `marketplace/`에 있다. 설치 경로와 새로운 대화에서의 발견은 호스트의 설치·재시작 절차에 따른다. 현재 대화가 새 버전을 읽었다고 가정하지 않는다. [공식 패키징 문서](https://developers.openai.com/plugins/build/plugins).
