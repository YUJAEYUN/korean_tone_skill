# 평가 하네스 사용법

이 하네스는 특정 LLM 업체에 묶이지 않는다. 모델 실행 결과를 공통 JSONL 형식으로 모은 뒤
결정적 검사, 블라인드 비교, 승격 판정을 재현한다. 개선 AI는 `dev` 사례만 볼 수 있고,
최종 비공개 테스트와 승격 정책은 수정할 수 없게 운영한다.

## 네 비교군

모든 사례를 같은 모델·추론 설정·실행 횟수로 생성한다.

- `source`: 원문 그대로
- `naive`: 스킬 없이 짧은 일반 윤문 프롬프트만 적용
- `champion`: 현재 배포 중인 스킬
- `challenger`: 개선 후보 스킬

모델과 스킬을 동시에 바꾸지 않는다. 모델을 비교할 때는 스킬을 고정하고, 스킬을 비교할 때는
모델 ID와 추론 설정을 고정한다.

## 데이터 분리

- `cases/dev.jsonl`: 개선자가 읽고 실패를 분석할 수 있다.
- `cases/validation.jsonl`: 후보 선택에 사용한다. 결과를 본 뒤 이 데이터에 맞춰 다시 고치면
  다음 후보부터는 개발 데이터로 강등한다.
- 비공개 테스트: 저장소 밖의 별도 경로에 둔다. `private-template.jsonl`은 형식 예시일 뿐
  실제 평가 사례가 아니다. 개선자에게 원문, 결과, 점수를 노출하지 않는다.
- `holdout/`: 기존 1차 실험 기록이다. 이미 결과가 공개됐으므로 더 이상 비공개 테스트가 아니다.

## 사례 형식

한 줄에 JSON 객체 하나를 둔다.

```json
{
  "id": "val-policy-01",
  "split": "validation",
  "genre": "notice",
  "register": "formal",
  "source_quality": "mixed",
  "instruction": "예외 조건을 빠뜨리지 말고 간결하게 다듬어 주세요.",
  "input": "원문",
  "must_preserve": ["반드시 그대로 남아야 하는 문자열"],
  "max_change_ratio": 0.25,
  "risk_tags": ["condition", "number"]
}
```

`max_change_ratio`는 이미 자연스러운 문장의 과잉 수정을 찾는 보조 경보다. 이것만으로 결과를
탈락시키지 않는다. 의미와 문체를 읽고 판단하는 평가가 따로 필요하다.

## 실행

아래 명령은 저장소 루트에서 실행한다.

```bash
HARNESS=skills/korean-plain-writer/scripts/eval_harness.py
EVAL=skills/korean-plain-writer/eval

python3 "$HARNESS" validate "$EVAL/cases/dev.jsonl" "$EVAL/cases/validation.jsonl"

python3 "$HARNESS" scaffold \
  --cases "$EVAL/cases/validation.jsonl" \
  --policy "$EVAL/policy.json" \
  --skill-root skills/korean-plain-writer \
  --out "$EVAL/runs/2026-09-13-v0.2.0" \
  --trials 4 \
  --model exact-model-id \
  --reasoning-effort medium \
  --artifact naive="$EVAL/baselines/naive.md" \
  --artifact champion=/별도/현재버전/스냅샷 \
  --artifact challenger=/별도/후보버전/스냅샷
```

Champion과 challenger는 평가 중 바뀌지 않는 별도 스냅샷이어야 한다. 같은 파일을 차례로
덮어쓰면서 생성하면 비교를 재현할 수 없다. `--artifact`는 각 스냅샷이나 프롬프트의 SHA-256을
manifest에 남긴다.

`outputs.template.jsonl`의 `null`을 실제 결과로 채우고 파일명을 `outputs.jsonl`로 바꾼다.
각 행의 형식은 다음과 같다.

```json
{"case_id":"val-info-01","system":"challenger","trial":1,"output":"실제 출력","metadata":{"latency_ms":820,"input_tokens":410,"output_tokens":95,"cost_usd":0.0021}}
```

`metadata`는 선택 사항이다. 제공하면 보고서가 시스템별 평균 지연, 토큰, 총비용을 함께
집계한다. 품질이 좋아도 실제 사용 비용과 응답 시간이 지나치게 늘어난 후보를 사람이 확인할
수 있다.

결정적 검사와 블라인드 용지를 만든다.

```bash
python3 "$HARNESS" static-grade \
  --cases "$EVAL/cases/validation.jsonl" \
  --outputs "$EVAL/runs/2026-09-13-v0.2.0/outputs.jsonl" \
  --policy "$EVAL/policy.json" \
  --out "$EVAL/runs/2026-09-13-v0.2.0/static-scores.jsonl"

python3 "$HARNESS" make-blind \
  --cases "$EVAL/cases/validation.jsonl" \
  --outputs "$EVAL/runs/2026-09-13-v0.2.0/outputs.jsonl" \
  --ballots "$EVAL/runs/2026-09-13-v0.2.0/ballots.jsonl" \
  --key "$EVAL/runs/2026-09-13-v0.2.0/private-key.jsonl"
```

`ballots.jsonl`만 평가자에게 준다. 같은 평가자가 거울쌍을 연달아 보지 않도록 순서를 다시
섞거나 평가자를 나눈다. `private-key.jsonl`은 평가가 끝날 때까지 공개하지 않는다.

평가자는 `judges/pairwise-naturalness.md`에 따라 아래 형식으로 투표한다.

```json
{"pair_id":"용지의 pair_id","judge_id":"human-01","winner":"left"}
```

투표를 `votes.jsonl`에 모은 뒤 보고서를 만든다.

별도의 의미 채점자는 `judges/semantic-gate.md`에 따라 각 후보 결과를 평가하고 다음 필드를
포함한 `semantic-scores.jsonl`을 만든다. `pass`는 문자열이 아닌 JSON 불리언이어야 한다.

```json
{"case_id":"val-info-01","system":"challenger","trial":1,"pass":true,"checks":{},"critical_issues":[]}
```

```bash
python3 "$HARNESS" report \
  --policy "$EVAL/policy.json" \
  --votes "$EVAL/runs/2026-09-13-v0.2.0/votes.jsonl" \
  --key "$EVAL/runs/2026-09-13-v0.2.0/private-key.jsonl" \
  --static-scores "$EVAL/runs/2026-09-13-v0.2.0/static-scores.jsonl" \
  --semantic-scores "$EVAL/runs/2026-09-13-v0.2.0/semantic-scores.jsonl" \
  --out "$EVAL/runs/2026-09-13-v0.2.0/report"
```

단순 프롬프트의 기여분을 따로 보려면 `make-blind`에서 `--system-a naive --system-b
challenger`를 지정하고, `report`에는 `--baseline-system naive --candidate-system
challenger`를 지정한다. 이 결과는 `comparison_only`로 기록되며 현재 버전 승격에는 쓰이지
않는다.

## 판정의 의미

- `rejected`: 중대 실패가 있거나 후보 승률이 기준보다 낮다.
- `insufficient_evidence`: 비교 수나 장르별 표본이 부족하다.
- `eligible_for_human_review`: 자동 기준을 통과했다. 자동 배포 승인이 아니다.

기본 정책은 중대 실패 0건, trial 단위 후보 승률 55% 이상, 사례 단위 승률의 95% Wilson
구간 하한 50% 이상을 요구한다. 같은 문장의 반복 trial을 서로 완전히 독립된 사례처럼 세어
확신을 부풀리지 않기 위해 신뢰구간은 사례 단위로 계산한다. 또한 장르별 최소 표본과 승률
하한을 확인하고, 이미 자연스러운 원문의 과잉 수정
경보율이 현재 버전보다 5%p 넘게 악화하면 탈락시킨다. 초기 seed처럼 표본이 작을 때는
`insufficient_evidence`가 정상적인 결과다. 점수를 본 뒤 기준을 낮추지 말고 사례와 trial을
늘린다.

사람은 마지막 상태에서 변경 diff, 의미 게이트 경계 사례, 채점자 불일치를 확인하고 현재
버전으로 승격한다. 승격 뒤에는 사용 모델·스킬 해시·Git 커밋이 든 `manifest.json`을 결과와
함께 보존한다.

## 자기개선의 경계

개선 AI는 한 번에 하나의 가설만 시험하고 후보 스킬만 편집한다. 평가 사례나 승격 정책을
고쳐 점수를 올리는 변경은 무효다. 실패를 발견하면 실제 사례를 익명화해 회귀 테스트로
추가하되, 정답과 평가 이유를 본 사례는 비공개 테스트로 재사용하지 않는다.
