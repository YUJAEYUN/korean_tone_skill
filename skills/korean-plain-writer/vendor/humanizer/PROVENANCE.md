# 이 디렉토리에 대해

이 아래 파일들은 우리가 쓴 게 아닙니다. **DaleSeo/korean-skills**의 `humanizer` 스킬을
그대로 가져온 사본입니다.

- 원본 저장소: https://github.com/DaleSeo/korean-skills
- 원본 경로: `skills/humanizer/`
- 가져온 커밋: `ae12ba27982ebeff03b46dc738365aaa34260d9a` (2026-05-04)
- 라이선스: MIT (`LICENSE` 파일 포함)

## 왜 링크 대신 파일을 통째로 넣었나

처음엔 `references/ai-tell-catalog.md`에 요약만 적고 원본 저장소 링크만 걸어 뒀습니다.
그런데 그렇게 하면 실제로 스킬을 돌릴 때(1단계 진단에서 40개 패턴의 정확한 판정 기준이
필요할 때) 매번 외부 저장소를 다시 불러와야 하고, 원본이 옮겨지거나 바뀌면 이 스킬도
같이 깨집니다. `korean-plain-writer`가 실제로 동작하려면 진단 엔진이 로컬에 그대로
있어야 해서, 여기로 옮겨왔습니다.

## 규칙

- 이 안의 파일은 손대지 않습니다. 고치고 싶은 게 있으면 원본 저장소에 제안하거나,
  우리 쪽 판단을 더하고 싶으면 `references/`(우리 스킬의 자체 참조 파일)에 새로
  적습니다.
- 원본이 업데이트되면 위 커밋 해시를 최신 걸로 바꾸고 파일을 다시 복사해 옵니다.
- `references/structure-patterns.md`(우리 것, 문단 배치 순서)와
  `vendor/humanizer/references/structure-patterns.md`(원본 것, 문장 리듬·나열 구조 같은
  AI체 판정 패턴)는 이름은 같지만 완전히 다른 파일입니다. 혼동하지 않습니다.
