# 하네스 실행법 (공유 스크립트)

이 평가는 `../../korean-plain-writer/scripts/eval_harness.py`를 그대로 쓴다.
스크립트를 복제하지 않는다 — 그 스크립트는 처음부터 스킬 비의존적으로 짜여
있어서(경로를 전부 인자로 받음), `--skill-root`와 `--cases`/`--policy`만 이
디렉터리로 바꾸면 그대로 동작한다. 전체 명령어·용어 설명은
`../../korean-plain-writer/eval/HARNESS.md`를 먼저 읽는다(여기서는 이 스킬에 맞춘
경로 차이만 적는다).

```bash
HARNESS=skills/korean-plain-writer/scripts/eval_harness.py
EVAL=skills/korean-writing-orchestrator/eval

python3 "$HARNESS" validate "$EVAL/cases/dev.jsonl"

python3 "$HARNESS" scaffold \
  --cases "$EVAL/cases/dev.jsonl" \
  --policy "$EVAL/policy.json" \
  --skill-root skills/korean-writing-orchestrator \
  --out "$EVAL/runs/<날짜-이름>" \
  --trials 1 --model exact-model-id
```

`static-grade`, `make-blind`, `report`는 `../../korean-plain-writer/eval/HARNESS.md`와
명령어가 완전히 같다 — `--cases`/`--outputs`/`--policy` 경로만 이 디렉터리 것으로
바꾸면 된다.

## 이 스킬만의 차이

- **사례 형식**: `korean-plain-writer`의 사례는 "원문을 윤문해 주세요"이지만, 이
  스킬은 새 글쓰기가 많다. `input` 필드는 "고칠 원문"이 아니라 "글감·상황 브리프"로
  쓴다(예: "점검 일시: 10월 5일..."). `must_preserve`는 브리프에 있는 핵심 사실 중
  결과물에도 반드시 남아야 하는 것을 적는다.
- **의미 채점자 대신/추가로**: `judges/composition-quality-rubric.md`를 쓴다.
  `../../korean-plain-writer/eval/judges/semantic-gate.md`(의미 보존)와
  `../../korean-plain-writer/eval/fluency-rubric.md`(유창성)는 그대로 재사용한다 —
  여기서 다시 만들지 않는다.
- **결정론적 검사**: `policy.json`이 `scan_composition_patterns: true`를 켜 둬서
  `static-grade`가 `rhythm`(문장 길이 변동계수)과 `composition_cliches`(상투적
  도입/마무리)도 함께 채점한다. `korean-plain-writer`는 이 플래그가 꺼져 있어서
  영향받지 않는다.

## 현재 상태

이 디렉터리는 인프라만 있고 아직 한 번도 실행하지 않았다(`runs/`가 비어 있다).
`README.md`에 다음 단계를 적어 뒀다.
