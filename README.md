# korean-plain-writer

AI 티 나는 한국어(번역투·명사화·상투어·어려운 한자어)를 없애고, 어떤 주제든 쉬운
표준 한국어로 읽히게 만드는 Claude Code 스킬입니다.

- 스킬 정의: [`SKILL.md`](./SKILL.md)
- 진단 카탈로그: [`references/ai-tell-catalog.md`](./references/ai-tell-catalog.md)
  (원본: [DaleSeo/korean-skills](https://github.com/DaleSeo/korean-skills)의 humanizer)
- 목표 문체 모듈:
  - [`references/plain-vocabulary-map.md`](./references/plain-vocabulary-map.md): 어휘 순화 매핑표
  - [`references/structure-patterns.md`](./references/structure-patterns.md): 정보 전달 글 구조 템플릿
  - [`references/genre-rules.md`](./references/genre-rules.md): 장르별 톤 규칙
- 예문 뱅크: [`examples/pairs/`](./examples/pairs/) (Before/After, 100~200쌍이 목표이고 지금은 45쌍)
- 변경률 가드 스크립트: [`scripts/change_rate_check.py`](./scripts/change_rate_check.py)

## 설계 원칙

1. 바퀴를 다시 만들지 않습니다. AI체 진단은 검증된 외부 카탈로그를 그대로 씁니다.
2. 직접 만들 가치가 있는 부분("그럼 어떻게 써야 하는가")에만 집중합니다.
3. 구조와 표현을 분리합니다. 수능 비문학은 논리 구조 학습용으로만 쓰고, 문장 표현의
   모범으로는 쓰지 않습니다.
4. 의미 보존이 최우선입니다. 사실관계·수치·주장 방향은 절대 바꾸지 않습니다.

자세한 파이프라인(진단 → 장르 판별 → 목표 문체 적용 → 의미 보존 검증 → 변경률 가드)은
[`SKILL.md`](./SKILL.md)를 참고하세요.

## 현재 상태 / 다음 단계

- [x] 디렉토리 구조, `SKILL.md` 오케스트레이션 초안
- [x] `references/` 4개 파일 초안 (어휘 매핑표 시드 55개, 구조 템플릿 4종, 장르 규칙 3종)
- [x] `examples/pairs/` 45쌍 (장르별 15쌍)
- [x] 변경률 가드 스크립트
- [ ] 예문 뱅크를 100~200쌍으로 마저 확장 (최우선, 현재 45/100~200)
- [ ] 어휘 매핑표를 실제 작업에서 나온 항목으로 계속 누적
- [ ] 서로 다른 장르 텍스트로 반복 eval
