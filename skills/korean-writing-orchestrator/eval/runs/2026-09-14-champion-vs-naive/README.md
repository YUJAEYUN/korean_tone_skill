# 2026-09-14 첫 정식 하네스 실행 (champion vs naive, 파일럿)

`korean-writing-orchestrator/eval/`을 만든 뒤 처음 실행한 기록이다. `cases/dev.jsonl`
4개 사례(제안서·에세이·공지·보고)로 champion(오케스트레이터 프로세스를 실제로 적용해
쓴 글)과 naive(지시문만 보고 별다른 설계 없이 쓴 글)를 비교했다.

**갱신 이력**: 처음엔 `rhythm_stats`가 문장 길이를 글자 수·단순 변동계수(CV)로만
쟀다. 이 파일럿 직후 실제 AI 텍스트 탐지 연구를 찾아보고 단어(어절) 수 기준과
Goh-Barabási burstiness 공식(B)으로 `eval_harness.py`를 고친 뒤, 아래 수치를 새
공식으로 다시 계산해 반영했다. 원래 분석 중 일부(제안서 champion 문장이 "짧아서"
균일하다는 부분)는 단위를 바꾸자 틀린 것으로 드러나 정정했다 — 아래 "리듬" 항목
참고.

## 이 실행의 한계

`korean-plain-writer/eval/runs/2026-09-14-champion-vs-naive/README.md`와 같은
한계다 — 생성과 채점(자연스러움·작문 품질)을 전부 같은 세션이 했고, 표본은 4사례
1trial뿐이다. `insufficient_evidence`/`eligible_for_human_review` 판정 대상이
아니라 `comparison_only`로 기록된다(challenger가 아직 없다).

**추가로, 이번엔 실제 실수를 하나 하고 고쳤다.** `votes.jsonl`을 처음 작성할 때
`ballots.jsonl`의 좌우 텍스트를 눈으로 보고 champion/naive를 짐작해서 투표를
적었는데, 제안서 사례에서 좌우를 착각해 실제로는 naive에 투표해 버렸다.
`private-key.jsonl`의 `left_system`/`right_system`과 대조해서 발견했고, 키를 기준으로
다시 만들어 고쳤다(`report.md`의 첫 버전은 제안서에서 champion 0승으로 잘못
나왔었다). 이게 정확히 `HARNESS.md`가 `private-key.jsonl`을 따로 두고 채점 형식을
지키라고 하는 이유다 — 사람이든 LLM이든 블라인드 판정은 눈으로 텍스트를 훑는 것만으로
좌우를 안전하게 매칭하기 어렵다.

## 결과

- 유효 비교 4건 중 champion 4승 0패, 무승부 없음. 장르별로도 4개 전부 champion 승.
- **후보 중대 실패 1건**: `orch-notice-01`에서 champion이 "오전 2시부터 4시까지"라고
  썼는데 `must_preserve`가 정확한 문자열 "오전 4시"를 요구해서 리터럴 불일치로
  걸렸다. 의미는 명확하다(두 번째 "오전"은 한국어에서 자연스럽게 생략 가능) —
  `korean-plain-writer` 파일럿의 `val-policy-01`("경우에 한해" vs "경우에만")과 같은
  패턴이다. 자연스러운 표현이 리터럴 must_preserve 검사와 부딪힐 수 있다는 걸 다시
  보여준다.
- **리듬 지표는 예상과 다르게 나왔다.** 처음엔 문장을 글자 수로 재고 변동계수(CV)만
  봤는데, 이 문서를 쓰고 나서 실제 AI 텍스트 탐지 연구를 찾아보니 (a) 문장 길이는
  글자 수가 아니라 **단어(어절) 수**로 재는 게 표준이고, (b) CV보다 Goh·Barabási
  (2008)의 정식 burstiness 공식 `B = (stdev-mean)/(stdev+mean)`(범위 [-1, 1])이
  더 널리 쓰인다는 걸 확인했다. `eval_harness.py`를 그에 맞게 고치고 다시 쟀다
  (아래는 단어 수 기준, "champion이 항상 문장 길이가 더 들쭉날쭉할 것"이라는
  예상과 비교):
  - 에세이: naive 평균 9.6단어/CV 0.334/B -0.499, champion 평균 5.7단어/CV
    0.597/B -0.253 (예상대로 champion이 덜 균일)
  - 제안서: naive 평균 7.6단어/CV 0.831/B -0.092, champion 평균 **12.2단어**/CV
    0.407/B -0.421 (**반대** — champion 문장이 더 길면서도 더 균일하다)
  - 공지: naive 평균 8.3단어/CV 0.858/B -0.077, champion 평균 7.7단어/CV
    0.272/B -0.573 (**반대**)
  - 보고: naive 평균 10.8단어/CV 0.233/B -0.623, champion 문장 2개뿐이라
    측정 불가(`None`)

  단위를 글자에서 단어로 바꾸니 처음 분석의 일부는 틀렸다는 것도 드러났다 —
  제안서에서 champion 문장이 "더 짧아서" 균일한 게 아니라 **오히려 naive보다
  길면서도 균일**했다(글자 수 기준 분석 때는 이걸 놓쳤다). 그래도 핵심 결론은
  똑같다: **"메트로놈처럼 균일한 리듬"이라는 AI체 불만은 CV나 B 하나만으로는
  "고르게 잘 쓴 글"과 구분되지 않는다.** `product-contract.md`에 이미 "임계값
  미정, 진단 지표로만 쓴다"고 적어 둔 게 정확히 이 이유 때문이었고, 실측이 그
  판단을 뒷받침한다. 참고로 Goh-Barabási 공식은 원래 사건 간 시간 간격을 재는
  공식이라 문장 길이에 적용하는 건 이 프로젝트의 자체 응용이지, 그 자체로
  검증된 한국어 AI체 신호는 아니다(`vendor/humanizer`의 94.88% AUC 수치 같은
  근거는 없음) — `rhythm_stats`의 docstring에도 그렇게 적어 뒀다.
- 상투적 마무리 탐지(`composition_cliches`)는 정확히 작동했다 — `orch-essay-01`의
  naive 버전에서 "이처럼 ~다는 것을 알 수 있었다"를 정확히 잡아냈고, 다른 7개
  출력에서는 오탐이 없었다.

## 사람이 확인할 것

1. `orch-notice-01`의 champion 출력이 정말 문제없는지(리터럴 불일치는 진짜
   문제인지, 아니면 seed 사례의 `must_preserve`를 너무 엄격하게 적었는지).
2. 제안서 사례의 투표를 다시 검토 — 한 번 실수했던 사례라 특히 더 확인이 필요하다.
3. CV 지표를 이대로 방치할지, 평균 문장 길이를 추가할지.
