# 작문 품질 채점표 (구조·논리·설득력)

의미 보존과 문법·유창성은 여기서 다루지 않는다 — 그건
`../../../korean-writing-validator/references/validation-gates.md`와
`../../../korean-plain-writer/eval/fluency-rubric.md`가 맡는다. 여기서는 "잘 쓴
글인가"의 나머지 축만 본다. `../product-contract.md`의 "겨냥하는 문제: AI 슬롭"
절을 먼저 읽는다.

## 시작하기 전에: 이 사례의 우선순위 확인

`../../references/priority-matrix.md`에서 이 글의 상황(장르·목적)에 맞는 행을
찾는다. 그 행의 "높은 우선순위" 축을 먼저 채점하고, 나머지는 참고로만 본다. 예를
들어 제안·설득 글이면 4번(반론 처리)이 핵심이고, 에세이·칼럼이면 2번(논지의 흐름)과
글쓴이 목소리가 핵심이다.

## 채점 항목

| 항목 | 통과 기준 |
|---|---|
| 1. 구조가 내용에 봉사하는가 | 서론-본론-결론 같은 형식을 "균형을 맞추려고" 강제로 채우지 않았는가. 이 소재에 필요 없는 항목을 형식상 추가하지 않았는가 |
| 2. 논지에 진짜 흐름이 있는가 | 문단들이 겉보기엔 앞뒤로 이어지지만 실은 각자 따로 도는 "표면적 정합성"만 있는 게 아니라, 글 전체를 관통하는 하나의 생각이 있는가 |
| 3. 확신과 구체성이 일치하는가 | 단정적으로 말하는 부분에 그걸 뒷받침할 구체적 근거·디테일이 있는가, 아니면 어조만 그럴듯하고 속이 비었는가(confidently hollow) |
| 4. 반론을 다뤘는가 (설득·제안 장르에만, 그 외 장르는 `na`) | 예상 가능한 반박이나 예외를 무시하지 않고 최소한 인지는 했는가 |
| 5. 독자가 실제로 목적을 달성할 수 있는가 | `../../references/priority-matrix.md` 해당 행의 기준(행동 가능성, 명료성, 탐색성 등)으로 확인 |

각 항목은 `pass`/`fail`/`na`로 판정한다. `na`는 이 장르·상황에 해당 항목 자체가
적용되지 않을 때만 쓴다("확신과 구체성" 같은 항목은 거의 항상 적용된다).

## 판단 기준 참고

- 항목 1: "필요 없는데도 구조를 채웠다"의 신호는 각 문단이 앞 문단의 결론을 그대로
  반복하거나, 서론이 결론을 미리 다 말해버리는 것.
- 항목 2: "표면적 정합성"의 신호는 접속어("따라서", "이처럼")를 빼면 문단 순서를
  바꿔도 전혀 이상하지 않은 글. 진짜 흐름이 있는 글은 순서를 바꾸면 논리가 깨진다.
- 항목 3: "confidently hollow"의 신호는 감각적·구체적 디테일 없이 결론만 단정하는
  문장이 이어지는 것("효과적이다", "중요하다" 같은 판단어만 반복되고 근거가 없음).
- 항목 4: 반론을 완전히 반박할 필요는 없다. 존재를 인지하고 대응 방향만 밝혀도
  통과로 본다. 반론 자체를 언급하지 않으면 실패.

## 기록 형식

```json
{
  "case_id": "val-persuade-01",
  "system": "challenger",
  "trial": 1,
  "checks": {
    "structure_serves_content": "pass",
    "genuine_throughline": "pass",
    "confidence_matches_specificity": "fail",
    "counterargument_handled": "pass",
    "reader_can_act": "pass"
  },
  "priority_axis": "설득력",
  "notes": "짧은 근거"
}
```

## 다른 채점표와의 관계

- 사실·수치·인용 보존: `../../../korean-writing-validator/references/validation-gates.md`
  "1. 불변 조건"
- 문법·유창성: `../../../korean-plain-writer/eval/fluency-rubric.md`
- AI체(번역투·명사화 등): `../../../korean-plain-writer/references/ai-tell-catalog.md`,
  결정론적 부분은 `../../../korean-plain-writer/scripts/eval_harness.py`의
  `scan_grammar_patterns`가 코드로도 확인
- 리듬(문장 길이 변동)·상투적 도입/마무리: 같은 스크립트의 `rhythm_stats`,
  `scan_composition_cliches`가 코드로 확인(임계값 미정, `../product-contract.md` 참고)
