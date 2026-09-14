# 2026-09-14 첫 정식 하네스 실행 (champion vs naive, 파일럿)

`eval_harness.py`를 실제로 처음부터 끝까지 실행한 기록이다. `validate` →
`scaffold` → (수작업 출력 생성) → `static-grade` → `make-blind` → (수작업 채점) →
`report` 전 과정을 저장소 안에서 실제로 돌렸다.

## 이 실행의 한계 (반드시 읽을 것)

- **challenger가 없다.** 아직 개선 후보 스킬이 없어서 `champion`(현재
  korean-plain-writer v0.2.0)과 `naive`(스킬 없이 `eval/baselines/naive.md`만
  적용) 두 계열만 비교했다. `policy.json`의 `champion_system`/`challenger_system`
  조합이 아니므로 `report`는 자동으로 `comparison_only`로 기록되고, 승격 판정
  (`eligible_for_human_review`/`rejected`)의 대상이 아니다.
- **생성자와 채점자가 같은 세션·같은 모델이다.** `naive`/`champion` 출력, 블라인드
  쌍대 채점(`votes.jsonl`), 의미 보존 채점(`semantic-scores.jsonl`)을 모두 같은
  Claude 세션이 만들었다. `HARNESS.md`가 요구하는 "다른 계열 LLM 채점자와 사람
  2명 이상"이 아니다. 라벨을 실제로 가린 채(`ballots.jsonl`만 보고
  `private-key.jsonl`은 열지 않고) 판정 형식은 지켰지만, 같은 모델이 만든 글을
  같은 모델이 평가하는 구조적 한계는 남는다. 독립적인 사람이나 다른 모델의
  평가가 아니면 진짜 신뢰 구간으로 쓰지 않는다.
- **표본이 매우 작다.** `validation.jsonl` 6개 사례, trial 1회, 장르당 비교
  1건뿐이다. `policy.json` 기준(유효 비교 20건 이상, 장르별 최소 2건)에 크게
  못 미쳐 `report.md`도 스스로 `insufficient_evidence` 사유를 나열한다.
- 이 실행은 "하네스 코드가 실제로 끝까지 동작하는가"와 "지금 스킬이 naive
  프롬프트보다 최소한의 신호에서 나은가"를 처음 확인하는 파일럿이다.
  `README.md`의 "다른 계열 LLM 채점자와 사람 2명 이상으로 하네스 첫 정식 실행"
  TODO를 대체하지 않는다.

## 결과 요약

- 유효 비교 5건(무승부 1건, notice 장르): champion 5승 0패, naive 0승.
  (`report.md` 참고, 표본이 작아 95% 구간이 56.6~100%로 넓다.)
- 결정적 검사(`static-scores.jsonl`): champion은 6개 사례 모두 통과, 과잉 수정
  경보 0건. naive는 2건 중대 실패:
  - `val-policy-01`: must_preserve 문자열 `"서버 장애가 확인된 경우에만"`을
    `"경우에 한해"`로 바꿔 리터럴 보존 실패(의미는 동일).
  - `val-quote-01`: 직접 인용을 간접 화법으로 바꿔 인용 보존 실패.
- 의미 게이트(`semantic-scores.jsonl`): champion 6/6 통과. naive는 3/6 실패
  (`val-natural-01`: 원문에 없는 뉘앙스 "마침" 추가, `val-quote-01`: 인용
  변형, `val-email-01`: 원문에 없는 강조 표현 추가로 감정 강도 과장).
- 이미 자연스러운 사례(`val-natural-01`, `val-email-01`, `val-policy-01`)에서
  champion은 세 건 모두 원문을 그대로 유지했고(과잉 수정 경보 0건),
  naive는 세 건 모두 불필요하게 손을 댔다. 이는 `product-contract.md`의
  "이미 자연스러운 글은 필요한 만큼만 고친다" 원칙이 실제로 작동한다는
  첫 실측 신호다(표본 3건뿐이라 신호일 뿐 증명은 아니다).

## 다음에 할 일

1. 이 실행을 독립적인 사람 평가자(2명 이상) 또는 다른 계열 모델 채점자로
   반복해서 자기채점 편향을 제거한다.
2. `dev.jsonl`까지 포함해 표본을 키우고, 실제 challenger(개선 후보)가 생기면
   4계열 비교로 확장한다.
3. `val-policy-01`처럼 "의미는 같지만 리터럴 must_preserve가 깨지는" 경우가
   naive에서 반복되는지 더 큰 표본으로 확인한다.
