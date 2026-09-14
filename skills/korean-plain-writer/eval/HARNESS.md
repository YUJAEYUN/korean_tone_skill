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

모델이 `schemas/batch-output.schema.json` 형식으로 사례 묶음을 생성했다면 직접 편집하지 않고
가져올 수 있다.

```bash
python3 "$HARNESS" import-batch \
  --cases "$EVAL/cases/validation.jsonl" \
  --batch naive=/tmp/naive.json \
  --batch champion=/tmp/champion.json \
  --batch challenger=/tmp/challenger.json \
  --trial 1 \
  --out "$EVAL/runs/pilot/outputs.jsonl"
```

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

## 독립 채점자 확보 (Agent 툴)

**2026-09-14까지의 모든 실행 기록에 반복해서 남아 있던 캐비어트**: 같은 세션이
생성과 채점을 모두 해서 자기채점이라는 것. 이건 몰라서가 아니라 매번 "일단 하나
돌아가는 결과부터"를 우선하느라 실제로 고치지 않고 미뤄온 것이었다(자세한 경위는
`eval/runs/2026-09-14-round1-tense-aspect/README.md`의 "독립 재채점" 절 참고). 이
섹션은 그 미루는 패턴을 끊기 위해 절차로 못박아 둔 것이다 — **개선 라운드마다
최소 1회는 아래 방식으로 독립 채점을 한다.**

Claude Code의 `Agent` 툴로 이 대화 맥락이 전혀 없는 별도 에이전트를 띄워서
`ballots.jsonl`을 다시 채점시킨다.

- `model` 파라미터를 이 세션과 다른 모델로 지정한다(예: 개선 세션이 sonnet이면
  판정은 opus나 haiku로). 같은 Anthropic 계열이라는 한계는 있지만, 최소한 같은
  세션의 자기 편향과는 분리된다.
- 프롬프트에는 **`judges/pairwise-naturalness.md`(또는 해당 스킬의 채점표) 규칙과
  `ballots.jsonl`의 좌/우/input/instruction만** 준다. 가설(`experiment.yaml`),
  diff, 이전 판정 결과, "이게 champion 개선 시도다" 같은 맥락은 절대 주지 않는다
  — 그 정보가 새어 들어가면 애초에 독립 채점을 하는 의미가 없다.
- 에이전트가 반환한 JSON을 `votes-independent-<모델명>.jsonl`처럼 원래
  `votes.jsonl`과 구분되는 이름으로 저장한다. 원래 자기채점 투표를 덮어쓰지
  않는다 — 두 결과를 나란히 남겨서 일치/불일치 자체가 기록이 되게 한다.
- `report` 명령을 이 새 투표 파일로 한 번 더 돌려서 원래 판정과 비교한다.
  일치하면 그 사실을, 불일치하면 어느 쪽이 더 근거 있는지 사람이 판단해야 한다는
  것을 README에 남긴다.

이건 `HARNESS.md`가 원래 요구하는 "다른 계열 LLM 채점자"(다른 회사 모델)의 완전한
대체가 아니다 — 그건 여전히 열려 있는 TODO다. 하지만 아무 독립 검증도 없는 것보다는
훨씬 낫고, 지금 이 세션에서 바로 할 수 있는 일이다(네트워크나 외부 API가 필요 없다).

## 채점 데이터를 다룰 때 반드시 지킬 것

`ballots.jsonl`의 `left`/`right` 텍스트를 **눈으로 보고** 어느 쪽이 champion인지
challenger인지 짐작해서 투표를 적지 않는다. 2026-09-14 orchestrator 파일럿에서
실제로 이렇게 하다가 한 사례의 좌우를 착각해서 투표가 뒤집힌 적이 있다(그 경위도
같은 파일럿의 README에 남아 있다). 투표를 만들 때는 항상:

1. `private-key.jsonl`을 읽어서 `pair_id → {left_system, right_system}` 매핑을
   코드로 만든다.
2. 시스템 단위로 "어느 쪽이 이겨야 하는가"를 먼저 정한다(사람이든 LLM이든, 판단은
   내용을 보고 하되 투표는 시스템 이름 기준으로 한다).
3. 그 매핑을 이용해 `pair_id`별로 `left`/`right`를 프로그램으로 계산한다. 텍스트를
   다시 읽고 눈대중으로 좌우를 맞히지 않는다.

## 결정론적 문법·AI체 패턴 검사

`static-grade`는 must_preserve·숫자·인용 보존과 별도로 `checks.ai_grammar_patterns`도
채점한다. `vendor/humanizer/references/translation-ese-patterns.md`와
`punctuation-patterns.md`에서 검증된 패턴 중 예외가 좁고 정규식으로 안전하게 잡을 수
있는 것들(이중 피동, "에 있어서", "가지고 있다", "에 대해" 남발 등)만 코드로 옮긴
것이다(`scripts/eval_harness.py`의 `GRAMMAR_PATTERNS`). LLM의 1단계 진단을 대체하지
않는다 — 각 패턴은 "자연스러운 경우" 예외가 있어서 정규식이 오탐할 수 있으므로
`advisory: true`로 표시되고 `critical_failures`에 넣지 않는다. 사람이 승격을 검토할 때
어떤 champion/challenger가 이 패턴을 더 자주 쓰는지 참고 신호로 쓴다.

**외부 맞춤법 검사기는 아직 연결 안 됨.** 부산대 맞춤법 검사기(`speller.cs.pusan.ac.kr`)
같은 실제 맞춤법·문법 API를 결정론적 게이트로 추가하는 게 다음 단계인데, 이 저장소
세션의 네트워크 정책이 해당 도메인을 막고 있어(`__agentproxy/status`에
`connect_rejected: 403`으로 기록됨) 이번엔 구현하지 못했다. 네트워크가 열린 환경(사용자
로컬, CI 등)에서 `static-grade`에 `--speller` 같은 선택적 플래그를 추가해 pluggable하게
붙이는 방식을 다음 라운드 후보로 남겨둔다.

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
