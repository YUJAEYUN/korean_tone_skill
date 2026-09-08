# korean-plain-writer

AI 티 나는 한국어(번역투·명사화·상투어·어려운 한자어)를 없애고, 어떤 주제든 쉬운
표준 한국어로 읽히게 만드는 Claude Code 스킬입니다.

스킬 본체는 [`skills/korean-plain-writer/`](./skills/korean-plain-writer/)에
있습니다. `skills/<이름>/SKILL.md` 하위에 스킬 하나를 통째로 담는 구조는
DaleSeo/korean-skills와 DietrichGebert/ponytail 등 여러 Claude Code 스킬 레포가
공통으로 쓰는 방식을 따른 것입니다. `.claude-plugin/`은 이 레포를 Claude Code
플러그인/마켓플레이스로 바로 설치할 수 있게 하는 최소 매니페스트입니다.

- 스킬 정의: [`skills/korean-plain-writer/SKILL.md`](./skills/korean-plain-writer/SKILL.md)
- 진단 카탈로그: [`references/ai-tell-catalog.md`](./skills/korean-plain-writer/references/ai-tell-catalog.md) (요약),
  [`vendor/humanizer/`](./skills/korean-plain-writer/vendor/humanizer/) (전문, [DaleSeo/korean-skills](https://github.com/DaleSeo/korean-skills)의 humanizer를 그대로 복사)
- 목표 문체 모듈:
  - [`references/plain-vocabulary-map.md`](./skills/korean-plain-writer/references/plain-vocabulary-map.md): 어휘 순화 매핑표
  - [`references/structure-patterns.md`](./skills/korean-plain-writer/references/structure-patterns.md): 정보 전달 글 구조 템플릿
  - [`references/genre-rules.md`](./skills/korean-plain-writer/references/genre-rules.md): 장르별 톤 규칙
  - [`references/fabricated-terms.md`](./skills/korean-plain-writer/references/fabricated-terms.md): 조어형 추상 개념어 판별법
- 예문 뱅크: [`examples/pairs/`](./skills/korean-plain-writer/examples/pairs/) (Before/After, 100~200쌍이 목표이고 지금은 45쌍)
- 변경률 확인 스크립트: [`scripts/change_rate_check.py`](./skills/korean-plain-writer/scripts/change_rate_check.py)
- 참조 무결성 검사: [`scripts/check_references.py`](./scripts/check_references.py) (레포 루트, 스킬 파일들이 서로 가리키는 경로가 실제로 존재하는지 확인)
- 평가: [`eval/`](./skills/korean-plain-writer/eval/) (예문 뱅크와 겹치지 않는 held-out
  텍스트로 블라인드 A/B + 의미 보존 게이트를 따로 채점. `eval/change-rate-baseline.md`는
  변경률 임계값을 재조정한 실측 근거)

## 설계 원칙

1. 바퀴를 다시 만들지 않습니다. AI체 진단은 검증된 외부 카탈로그를 그대로 씁니다.
2. 직접 만들 가치가 있는 부분("그럼 어떻게 써야 하는가")에만 집중합니다.
3. 구조와 표현을 분리합니다. 수능 비문학은 논리 구조 학습용으로만 쓰고, 문장 표현의
   모범으로는 쓰지 않습니다.
4. 의미 보존이 최우선입니다. 사실관계·수치·주장 방향은 절대 바꾸지 않습니다.
5. 남이 이미 잘 만든 구조도 필요한 만큼만 가져옵니다. 우리 규모에 안 맞는 부분(여러
   에이전트 지원, npm 배포, 벤치마크 스위트 같은 것)까지 통째로 베끼지 않습니다.

자세한 파이프라인(진단 → 장르 판별 → 목표 문체 적용 → 의미 보존 검증 → 변경률 확인)은
[`SKILL.md`](./skills/korean-plain-writer/SKILL.md)를 참고하세요.

## 현재 상태 / 다음 단계

- [x] `skills/korean-plain-writer/` 구조로 스킬 본체(SKILL.md, references, examples,
      scripts, vendor) 정리, `.claude-plugin/` 매니페스트 추가
- [x] `references/` 5개 파일(어휘 매핑표, 구조 템플릿, 장르 규칙, 조어형 개념어 판별,
      진단 카탈로그 요약)
- [x] `examples/pairs/` 45쌍 (장르별 15쌍)
- [x] 변경률 확인 스크립트, 참조 무결성 검사 스크립트
- [x] `vendor/humanizer/`에 DaleSeo/korean-skills의 humanizer 스킬 전문 로컬 복사
- [x] `eval/`: held-out 텍스트 3개(장르별 1개)로 첫 평가 실행, 변경률 임계값이
      korean-plain-writer에는 안 맞는다는 것을 발견하고 재조정(30~50% → 150%,
      가드가 아니라 참고 수치로 성격 변경)
- [ ] 예문 뱅크를 100~200쌍으로 마저 확장 (최우선, 현재 45/100~200. 실제 수집된
      사례 비중을 늘리는 게 개수보다 중요)
- [ ] 어휘 매핑표를 실제 작업에서 나온 항목으로 계속 누적
- [ ] `fabricated-terms.md`의 구성 예시를 실제 겪은 사례로 교체·보강
- [x] `eval/holdout/` 3개 블라인드 A/B 1차 결과 기록 (`eval/results.md`, 평가자 1명,
      3/3 재작성본 선택. 표본이 작아 참고 수준)
- [ ] 평가자 2명 이상, 이미 자연스러운 원문도 포함해서 2차 라운드 진행
- [ ] "스킬 미적용 재작성"(naive baseline) 비교군 추가해 스킬 자체의 기여분 측정
