# 로컬 설치와 복구

개인 Codex 플러그인에는 루트 `plugin.json`과 `skills/professional-reports/`를 포함합니다. OpenAI 공식 포맷은 루트의 `skills/`를 자동 발견합니다. 설치 시 원본과 별도의 캐시 사본을 사용하므로 원본 수정만으로 이미 설치된 플러그인이 갱신되지 않습니다.

공식 근거: https://developers.openai.com/plugins/build/plugins

1. 패키지의 `pack`·`verify`로 새 릴리스를 만들고 `install`로 사용자 상태 저장소의 불변 릴리스 폴더에 배치합니다.
2. `activate`로 다음 실행부터 사용할 릴리스를 전환합니다. 개발 버전은 `--development`가 필요합니다. 진행 중인 실행의 핀은 바뀌지 않습니다.
3. `marketplace --release <release> --out <새 marketplace 경로>`로 얇은 진입 플러그인과 카탈로그를 만듭니다. `.agents/plugins/marketplace.json`의 `source.path`는 marketplace root 기준 상대 경로입니다. 이 명령은 설치를 주장하지 않으며 실제 Codex 설치 명령을 반환합니다.
4. 현재 설치된 Codex CLI의 `codex plugin marketplace add <root>`와 `codex plugin add --help`가 제공하는 설치 경로를 사용합니다. 수동 캐시나 비공개 API를 쓰지 않습니다.
5. 설치 후 새 컨텍스트에서 진입 스킬을 읽고 `load`가 반환하는 버전과 해시를 확인합니다. 현재 대화가 새 플러그인 목록을 자동 갱신했다고 가정하지 않습니다.

부트스트랩은 사용자 상태 저장소의 `active.json`을 읽고 해당 릴리스를 검증합니다. 사용자의 다른 플러그인이나 글로벌 AGENTS.md를 덮어쓰지 않습니다. 라이브러리 릴리스 갱신과 부트스트랩 코드 갱신은 별개의 설치 작업입니다.

`rollback`은 이전 활성 릴리스를 재검증한 뒤 되돌립니다. 실행 원장·원문·실험은 삭제하지 않습니다. 설치 디렉터리 이동, 변조, 잘못된 경로와 이전 버전 복구는 별도 테스트로 확인합니다.
