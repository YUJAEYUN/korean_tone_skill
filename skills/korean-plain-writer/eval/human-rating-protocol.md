# 사람 채점자 절차

`self-improvement-prd.md`가 정한 대로 사람(사용자)이 주 채점자다. 이 문서는
그 채점을 실제로 어떻게 하는지 단계별로 적는다. 판단 기준 자체는
`judges/pairwise-naturalness.md`를 그대로 쓴다 — 여기서는 그 기준을 어떻게
받고 어떻게 기록하는지만 다룬다.

## 1. 사례 준비

라운드마다 새 주제로 직접 글(또는 다듬을 원문)을 몇 개 쓴다.

- 과거 라운드에서 이미 본 사례는 다시 쓰지 않는다. 한 번 결과를 보고 나면 그
  사례로는 더 이상 순수한 검증이 안 된다 — `cases/validation.jsonl`의 회전
  규칙과 같은 이유다.
- 주제는 다양하게: 장르(정보 전달/의견·에세이/실용문), 격식(존댓말/반말),
  길이를 섞는다. 한 라운드가 겨냥하는 가설과 무관한 사례도 1~2개 섞어서
  "가설과 무관한 곳에 회귀가 없는가"를 같이 확인한다.
- 작성한 원문은 `cases/dev.jsonl` 또는 `cases/validation.jsonl` 형식(HARNESS.md
  "사례 형식" 참고)으로 등록한다.

## 2. 블라인드 확인

개선 AI가 `make-blind`로 `ballots.jsonl`을 만든다. 사용자는 **이 파일만**
받는다 — champion/challenger 어느 쪽이 왼쪽/오른쪽인지 모르는 상태다. 이건
독립 Agent 채점과 똑같이 적용한다: 자기가 무엇을 만들었는지 아는 상태로
판단하면 선호가 왜곡된다.

받는 것: `input`(원문), `instruction`(요청), `left`/`right`(두 후보 결과).
받지 않는 것: 가설, diff, 어느 게 champion/challenger인지, 이전 라운드의
판정 결과.

## 3. 판단

`judges/pairwise-naturalness.md`의 우선순위를 그대로 따른다.

1. 원문의 사실·주장·논리 관계·불확실성·감정 강도 보존
2. 사용자 요청·장르·독자·격식 부합
3. 글쓴이의 목소리를 획일화하지 않았는가
4. 번역투·상투어·명사화·과잉 구조화 감소
5. 문법적으로 매끄럽고 한 번에 읽히는가
6. 불필요하게 장황하거나 과하게 수정하지 않았는가

둘의 품질 차이를 자신 있게 판단할 수 없을 때만 `tie`를 쓴다.

## 4. 기록

각 판단에 `winner`(left/right/tie)와 `reason_tags`
(`improvement-protocol.md`의 "사람 취향 학습" 절 참고: meaning/voice/
naturalness/fluency/overediting/instruction, 새 이유가 필요하면 자유롭게
추가)를 남긴다.

```json
{"pair_id": "용지의 pair_id", "judge_id": "human-<이름>", "winner": "left", "reason_tags": ["naturalness"]}
```

`votes-human-<이름>.jsonl`에 저장한다(`votes.jsonl`을 덮어쓰지 않는다 —
자가채점·독립 Agent 채점과 나란히 남겨서 일치/불일치 자체가 기록이 되게
한다).

## 5. 집계

```bash
python3 "$HARNESS" report \
  --policy "$EVAL/policy.json" \
  --votes "$EVAL/runs/<라운드>/votes-human-<이름>.jsonl" \
  --key "$EVAL/runs/<라운드>/private-key.jsonl" \
  --static-scores "$EVAL/runs/<라운드>/static-scores.jsonl" \
  --semantic-scores "$EVAL/runs/<라운드>/semantic-scores.jsonl" \
  --out "$EVAL/runs/<라운드>/report-human"
```

독립 Agent 채점(`votes-independent-<모델>.jsonl`)과 나란히 비교한다. 일치하면
그 사실을, 불일치하면 어느 쪽이 더 근거 있는지 사람(승인자로서)이 판단해야
한다는 것을 라운드 README에 남긴다 — 이건 `HARNESS.md`의 기존 규칙과 같다.

## 6. 사람 취향이 반복될 때

같은 `reason_tags`가 여러 라운드에서 반복되면 `improvement-protocol.md`의
"사람 취향 학습" 절 규칙대로 처리한다: 단일 선택을 곧바로 보편 규칙으로
만들지 않고, 반복되는 패턴만 다음 라운드의 가설 후보로 `failure-log.jsonl`에
추가한다.
