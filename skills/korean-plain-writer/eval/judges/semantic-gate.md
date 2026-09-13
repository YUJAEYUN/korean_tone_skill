# 의미 보존 게이트 지침

원문과 편집본을 비교한다. 더 자연스러운지를 채점하지 말고 의미 보존만 확인한다.

다음을 각각 독립적으로 검사한다.

- 숫자, 날짜, 인명, 기관명, 제품명
- 직접 인용
- 핵심 주장과 결론
- 부정/긍정, 가능/불가능
- 인과, 조건, 예외, 비교, 시간 순서
- 확실함/가능성/추측 등 확신의 강도
- 중요한 정보의 누락
- 원문에 없던 사실, 사례, 이유, 감정의 추가

다음 JSON 한 개만 출력한다.

```json
{
  "pass": true,
  "checks": {
    "entities_and_numbers": "pass | fail | na",
    "quotes": "pass | fail | na",
    "claim_and_conclusion": "pass | fail",
    "polarity_and_modality": "pass | fail",
    "logical_relations": "pass | fail | na",
    "omission": "pass | fail",
    "addition": "pass | fail"
  },
  "critical_issues": [],
  "notes": "짧은 근거"
}
```

