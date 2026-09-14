# 2026-09-14 개선 라운드 1: 시제·상(相) 체크리스트 항목 추가

`eval/improvement-protocol.md` 형식을 따른 첫 개선 라운드다. 가설 → challenger
스냅샷 → champion과 실제 블라인드 비교까지 실행했다. 자세한 가설/근거/예상 효과는
`experiment.yaml`, 실제 변경분은 `challenger.diff` 참고. `challenger.diff`는
현재 `skills/korean-plain-writer/SKILL.md`(champion) 기준 patch라서, 평가에
실제로 쓴 challenger 스냅샷은 `git apply challenger.diff` 후의 `SKILL.md`와
동일하다. 스냅샷 디렉터리 전체를 커밋에 중복 보관하지 않고 diff만 남긴다
(HARNESS.md가 요구하는 SHA-256 스냅샷 원칙과 같은 취지 — 실행 당시
`skill_tree_sha256`은 `report.json`이 아니라 이 diff로 재현 가능하다).

## 이 라운드를 시작하며 먼저 한 일: validation 회전

`eval/runs/2026-09-14-champion-vs-naive/`에서 이미 `validation.jsonl` 6개 사례의
결과를 직접 만들고 읽었다. `improvement-protocol.md`는 "validation 결과로 한 번
수정한 뒤에는 해당 validation 사례를 dev로 옮기고 새 validation을 확보한다"고
규정하므로, 이번 라운드를 시작하기 전에:

- 기존 `validation.jsonl` 6개(`val-*`)를 `dev.jsonl`로 옮겼다(`split` 필드를
  `dev`로 변경).
- `validation.jsonl`에 이번에 본 적 없는 새 사례 6개(`val2-*`)를 채웠다. 이 중
  `val2-tense-01`, `val2-casual-01`는 이번 가설(시제·상)을 직접 겨냥해 새로
  만든 사례다.

## 가설의 근거

지난 파일럿에서 champion이 `val-casual-01`(이제 dev로 이동)의 "충분히 이해하고
있어"(진행 중)를 "이해했어"(완료)로 바꿨다. 당시 8항 의미 게이트 어디에도 걸리지
않아 통과 처리됐지만, 시제·상이 실제로 바뀐 것은 맞다. 이번 라운드는 이 사각지대를
메우는 최소 변경 하나만 시험한다: 체크리스트에 9번째 항목(시제·상 보존)을 추가.

## 결과

`report.md` 원문 그대로:

- 유효 비교 2건(무승부 4건): challenger 2승 0패, 0건 중대 실패.
  - `val2-tense-01`("운영되고 있다" 유지 vs "운영한다"로 축소): challenger 승.
  - `val2-casual-01`("생각하고 있어" 유지 vs "생각해봤어"로 축소): challenger 승.
  - 나머지 4개 사례(이미 자연스럽거나 인용·조건이 핵심인 글)는 champion과
    challenger가 완전히 동일한 출력을 냈다. 새 체크리스트 항목이 관련 없는
    사례에는 아무 영향을 주지 않는다는 뜻이라 회귀 없음의 첫 신호로 본다.
- 판정은 `insufficient_evidence`다. 유효 비교 2건(정책 기준 20건), 사례 2개
  (기준 6개), 장르별 최소 표본에 다 못 미쳐 자동으로 이렇게 나왔다. 이건
  정상이다. `HARNESS.md`도 "초기 seed처럼 표본이 작을 때는
  `insufficient_evidence`가 정상적인 결과다. 점수를 본 뒤 기준을 낮추지 말고
  사례와 trial을 늘린다"고 못 박아 뒀다.

## 이 라운드의 한계 (지난 파일럿과 동일)

- 가설 수립, challenger 편집, champion/challenger 출력 생성, 블라인드 채점을
  전부 같은 세션이 했다. 독립적인 사람/다른 모델 채점이 아니다.
- 표본 6사례·trial 1회. `val2-tense-01`/`val2-casual-01`는 가설을 직접 겨냥해
  만든 사례라 "우연히 이겼다"일 위험도 있다 — 가설과 무관한 사례로 더 검증해야
  한다.
- 아직 `skills/korean-plain-writer/SKILL.md`(실제 champion)는 고치지 않았다.
  `challenger-skill/`은 독립된 스냅샷일 뿐이다. `improvement-protocol.md`가
  요구하는 사람의 최종 승격 판단이 없으면 절대 라이브 스킬에 반영하지 않는다.

## 사람이 확인할 것 (승격 여부 결정)

1. `challenger.diff` — 가설과 무관한 변경이 섞이지 않았는지.
2. 장르별 결과 표 — 평균에 가려진 회귀가 없는지(이번엔 4개 장르가 전부
   무승부라 판단할 근거 자체가 적다).
3. `val2-tense-01`/`val2-casual-01` 두 사례의 실제 문장 — challenger의 판단이
   정말 더 나은지 직접 읽고 동의하는지.
4. 동의하면 다음 라운드에서 (a) 가설과 무관한 사례를 더 채우고, (b) 독립
   채점자로 반복한 뒤 승격을 최종 확정한다. 지금 승격을 확정하기엔 표본이
   너무 작다.

## 승격 결정 (2026-09-14)

사람(20211072@edu.hanbat.ac.kr)이 위 diff와 사례를 직접 검토하고 승격을
승인했다. `skills/korean-plain-writer/SKILL.md`는 v0.2.0에서 v0.2.1로
올라갔고, 이 라운드의 challenger 변경(9번째 체크리스트 항목)이 그대로
반영됐다.

다만 `report.json`의 자동 판정은 여전히 `insufficient_evidence`다. 정책
임계값(유효 비교 20건 이상, 사례 6개 이상)을 낮추거나 우회해서 통과시킨 게
아니라, 표본이 작다는 걸 알면서도 diff가 최소하고 가설을 겨냥한 2개 사례를
모두 이겼으며 무관한 4개 사례에 회귀가 없다는 근거로 사람이 수동으로
승격을 결정했다. 자세한 근거는 `promotion-manifest.json`에 남겼다.

`eval/product-contract.md`의 "평가 결과 없이 후보 스킬을 현재 버전 위에
덮어쓰지 않는다"는 원칙은 지켰다. 평가 자체는 했기 때문이다. 다만 표본이
정책 기준에 못 미친 채로 승격했다는 점은 다음 라운드 회고에서 계속
추적해야 한다. 다음 라운드부터는 v0.2.1이 새 champion이다.
