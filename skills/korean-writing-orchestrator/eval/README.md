# 작문 품질 평가

`../../korean-plain-writer/eval/`이 "이미 있는 글을 편집하는 성능"을 평가한다면, 여기는
`korean-writing-orchestrator`가 **새 글을 쓰거나 구조를 바꿀 때**의 품질(구조·논리·
설득력)을 평가한다. 왜 이 축을 따로 만들었는지는 `product-contract.md`의 "겨냥하는
문제: AI 슬롭" 절 참고.

## 지금 상태 (정직하게)

**인프라만 있고 한 번도 실행하지 않았습니다.** `korean-plain-writer`가 처음 파일럿을
돌리기 전과 같은 단계입니다.

- [x] `product-contract.md`: 무엇을 측정할지, 무엇을 측정하지 않을지 정의
- [x] `judges/composition-quality-rubric.md`: LLM 채점자용 5항 채점표
- [x] `policy.json`: `korean-plain-writer`와 같은 승격 기준 재사용
- [x] `cases/dev.jsonl`: 제안·에세이·공지·보고 4개 장르, `../references/priority-matrix.md`의
      서로 다른 우선순위 행을 겨냥한 seed 사례
- [x] 결정론적 코드 검사 2종(`rhythm_stats`, `scan_composition_cliches`)을
      `eval_harness.py`에 추가하고 `policy.json`에서 활성화
- [ ] **리듬 변동계수 임계값 미정.** 진단 숫자만 나온다. 실제 사람이 쓴 글과
      AI가 그대로 쓴 글 표본을 모아 실측하기 전까지는 "낮으면 나쁘다"는 기준을
      정하지 않는다(`../../korean-plain-writer/eval/change-rate-baseline.md`가
      했던 방식 그대로).
- [x] 첫 파일럿 실행 (`runs/2026-09-14-champion-vs-naive/`): champion(오케스트레이터
      프로세스 적용) vs naive(지시문만 보고 씀) 4사례 비교, champion 4승 0패.
      다만 champion 결과 1건이 must_preserve 리터럴 불일치로 중대 실패 처리됨(의미는
      명확하나 문자열이 정확히 안 맞음). 리듬 변동계수(CV)는 예상과 달리 champion이
      naive보다 항상 높게 나오지는 않음 — "균일하게 짧은 것"과 "메트로놈처럼
      반복되는 것"을 CV 하나로 구분 못 함을 확인, 임계값을 정하지 않은 결정이
      맞았음을 뒷받침. 자기채점 파일럿이라 표본도 작음(한계 그대로)
- [ ] validation 세트 분리 (지금 4개는 전부 dev, 승격 판단에 쓸 validation은
      아직 없음)
- [x] 리듬 지표를 실제 연구 근거로 교체 — 문장 길이를 글자 수 대신 단어(어절) 수로
      재고, 단순 CV 대신 Goh·Barabási(2008) burstiness 공식(B, [-1,1] 범위)도
      함께 낸다. `mean_length`를 항상 같이 봐야 "고르게 짧음"과 "메트로놈 리듬"을
      구분할 수 있다는 게 파일럿에서 확인됨(여전히 임계값은 없음, 진단 지표)

## 다음에 할 일

1. `cases/dev.jsonl` 4개 사례로 오케스트레이터가 실제로 새 글을 생성하게 하고,
   `judges/composition-quality-rubric.md`로 채점해 지금 상태의 기준선을 잡는다.
   `korean-plain-writer`가 `champion-vs-naive` 파일럿으로 했던 것과 같은 절차.
2. 리듬 변동계수를 이 라운드에서 나온 실제 텍스트로 실측해서, "낮은 CV"가 진짜
   AI체 신호인지 아니면 단순히 이 사례들 특성인지 확인한다.
3. 표본이 쌓이면 validation 세트를 분리하고, 그다음부터
   `../../korean-plain-writer/eval/improvement-protocol.md` 방식의 개선 라운드를
   이 스킬에도 적용한다.
