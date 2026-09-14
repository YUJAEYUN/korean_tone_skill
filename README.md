# Korean writing skills

글의 목적·독자·매체·위험도에 맞춰 필요한 단계를 고르고, 한국어 글을 쓰거나 고치는
Claude Code 스킬 모음입니다. 모든 규칙을 무조건 적용하지 않고 큰 구조에서 작은 표현
순서로 고친 뒤 의미와 목적 적합성을 검증합니다.

## 스킬 구성

- `korean-writing-orchestrator`: 전체 작업 순서와 전문 스킬 선택
- `korean-writing-context`: 목적·독자·매체·격식·위험도 분석
- `korean-plain-writer`: 쉬운 한국어, 장르별 구조·톤, AI체 개선
- `korean-writing-validator`: 사실·의미 보존과 목적 적합성 최종 검증

기본 진입점은 [`korean-writing-orchestrator/SKILL.md`](./skills/korean-writing-orchestrator/SKILL.md)입니다.

각 스킬은 [`skills/`](./skills/)에 있습니다. `skills/<이름>/SKILL.md` 하위에 스킬 하나를 통째로 담는 구조는
DaleSeo/korean-skills와 DietrichGebert/ponytail 등 여러 Claude Code 스킬 레포가
공통으로 쓰는 방식을 따른 것입니다. `.claude-plugin/`은 이 레포를 Claude Code
플러그인/마켓플레이스로 바로 설치할 수 있게 하는 최소 매니페스트입니다.

- 쉬운 한국어 전문 스킬: [`skills/korean-plain-writer/SKILL.md`](./skills/korean-plain-writer/SKILL.md)
- 진단 카탈로그: [`references/ai-tell-catalog.md`](./skills/korean-plain-writer/references/ai-tell-catalog.md) (요약),
  [`vendor/humanizer/`](./skills/korean-plain-writer/vendor/humanizer/) (전문, [DaleSeo/korean-skills](https://github.com/DaleSeo/korean-skills)의 humanizer를 그대로 복사)
- 목표 문체 모듈:
  - [`references/plain-vocabulary-map.md`](./skills/korean-plain-writer/references/plain-vocabulary-map.md): 어휘 순화 매핑표
  - [`references/structure-patterns.md`](./skills/korean-plain-writer/references/structure-patterns.md): 정보 전달 글 구조 템플릿
  - [`references/genre-rules.md`](./skills/korean-plain-writer/references/genre-rules.md): 장르별 톤 규칙
  - [`references/fabricated-terms.md`](./skills/korean-plain-writer/references/fabricated-terms.md): 조어형 추상 개념어 판별법
- 예문 뱅크: [`examples/pairs/`](./skills/korean-plain-writer/examples/pairs/) (Before/After, 100~200쌍이 목표이고 지금은 45쌍)
- 변경률 확인 스크립트: [`scripts/change_rate_check.py`](./skills/korean-plain-writer/scripts/change_rate_check.py)
- 평가 하네스: [`eval/HARNESS.md`](./skills/korean-plain-writer/eval/HARNESS.md) 및
  [`scripts/eval_harness.py`](./skills/korean-plain-writer/scripts/eval_harness.py)
- 참조 무결성 검사: [`scripts/check_references.py`](./scripts/check_references.py) (레포 루트, 스킬 파일들이 서로 가리키는 경로가 실제로 존재하는지 확인)
- 평가: [`eval/`](./skills/korean-plain-writer/eval/) (예문 뱅크와 겹치지 않는 held-out
  텍스트로 블라인드 A/B + 의미 보존 게이트를 따로 채점. `eval/change-rate-baseline.md`는
  변경률 임계값을 재조정한 실측 근거)
- 릴리즈 노트: [`CHANGELOG.md`](./skills/korean-plain-writer/CHANGELOG.md) (승격할 때마다
  뭐가·왜 바뀌었는지, 어떤 근거로 검증했는지 기록)
- 작문 품질(구조·논리·설득력) 평가: [`korean-writing-orchestrator/eval/`](./skills/korean-writing-orchestrator/eval/)
  (새 글쓰기 전용, 하네스는 `korean-plain-writer/scripts/eval_harness.py`를 공유.
  첫 파일럿 실행 완료, validation 세트는 아직 없음)

## 설계 원칙

1. 바퀴를 다시 만들지 않습니다. AI체 진단은 검증된 외부 카탈로그를 그대로 씁니다.
2. 직접 만들 가치가 있는 부분("그럼 어떻게 써야 하는가")에만 집중합니다.
3. 목적·독자·매체·위험도를 장르보다 먼저 판단하고 필요한 전문 스킬만 적용합니다.
4. 구조와 표현을 분리합니다. 수능 비문학은 논리 구조 학습용으로만 쓰고, 문장 표현의
   모범으로는 쓰지 않습니다.
5. 의미 보존이 최우선입니다. 사실관계·수치·주장 방향은 절대 바꾸지 않습니다.
6. 이미 자연스러운 글과 글쓴이의 목소리를 불필요하게 평준화하지 않습니다.
7. 성능은 원문·단순 프롬프트·현재 버전·후보 버전의 블라인드 비교와 의미 보존 게이트로
   검증합니다. 개선 AI가 평가 정책이나 비공개 테스트를 바꿀 수 없게 합니다.
8. 사람에게 요구하는 건 언어학적 검증이 아니라 증거 기준 통과 여부·근거의 실재
   여부·위험 감수 여부입니다. 하네스 자신이 충분한 증거로 확신하는 승격은 사람
   승인 없이 진행하고 릴리즈 노트로만 알리되, 하네스가 확신하지 못하는데 강행하는
   경우는 반드시 사람이 결정합니다(`korean-plain-writer/eval/product-contract.md`
   "사람의 역할" 절 참고).

전체 파이프라인(상황 분석 → 우선순위 결정 → 전문 스킬 선택 → 순차 수정 → 최종 검증)은
[`korean-writing-orchestrator/SKILL.md`](./skills/korean-writing-orchestrator/SKILL.md)를 참고하세요.

## 현재 상태 / 다음 단계

- [x] 1차 오케스트레이션 구조: 총괄 스킬, 상황 분석 스킬, 기존 쉬운 한국어 스킬,
      최종 검증 스킬 연결
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
- [ ] 실제 사용에서 나온 익명화 사례와 사용자 A/B 선택을 지속적으로 축적
- [ ] 어휘 매핑표를 실제 작업에서 나온 항목으로 계속 누적
- [ ] `fabricated-terms.md`의 구성 예시를 실제 겪은 사례로 교체·보강
- [x] `eval/holdout/` 3개 블라인드 A/B 1차 결과 기록 (`eval/results.md`, 평가자 1명,
      3/3 재작성본 선택. 표본이 작아 참고 수준)
- [x] 원문·naive·champion·challenger 비교, 결정적 의미 검사, 블라인드 거울쌍,
      승격 판정과 버전 manifest를 지원하는 평가 하네스 구현
- [x] 개발 12개·검증 6개 seed 사례에 이미 자연스러운 원문, 조건, 인용, 숫자,
      불확실성, 반말·존댓말 회귀 범주 포함
- [x] 하네스 파이프라인(validate→scaffold→static-grade→make-blind→report) 첫
      실제 실행 (`eval/runs/2026-09-14-champion-vs-naive/`). champion vs naive
      비교 5건 중 5승, naive 2건 결정적 실패·3건 의미 게이트 실패 관측.
      **단, 생성과 채점을 같은 세션이 해서 자기채점이며 표본도 6개뿐** — 정식
      실행이 아니라 하네스가 실제로 도는지 확인한 파일럿
- [x] 첫 개선 라운드 실행 및 승격 (`eval/runs/2026-09-14-round1-tense-aspect/`):
      시제·상(진행/완료) 보존을 의미 게이트 체크리스트에 9번째 항목으로 추가하는
      challenger를 만들어 champion과 블라인드 비교. 가설 표적 사례 2/2 승,
      무관한 사례는 회귀 없이 동일 출력. 자동 판정은 표본 부족으로
      `insufficient_evidence`였지만 사람이 diff를 직접 검토하고 수동으로
      승격 승인 (`promotion-manifest.json`). `korean-plain-writer` v0.2.0 →
      **v0.2.1**
- [x] 하네스에 결정론적 문법·AI체 패턴 검사 추가(`eval_harness.py`의
      `scan_grammar_patterns`): 이중 피동, "에 있어서", "가지고 있다", "에 대해"
      남발 등 `vendor/humanizer`에서 이미 검증된 패턴 중 정규식으로 안전하게 잡을
      수 있는 것만 코드로 옮김(예외가 좁은 패턴만 선정). LLM 1단계 진단을
      대체하지 않고 advisory로만 씀(`HARNESS.md` 참고)
- [ ] 외부 맞춤법 검사기(부산대 API 등)를 선택적 결정론적 게이트로 연결 —
      이 세션 네트워크 정책이 `speller.cs.pusan.ac.kr`을 막고 있어(403) 이번엔
      구현 못 함. 네트워크가 열린 환경에서 `--speller` 같은 선택적 플래그로
      붙이는 걸 다음 단계로 남김
- [x] `korean-writing-orchestrator`에 작문 품질(구조·논리·설득력) 평가 인프라 신설
      (`korean-writing-orchestrator/eval/`): `korean-plain-writer`와 같은
      하네스 스크립트를 공유하고, 이 스킬만의 `product-contract.md`,
      `judges/composition-quality-rubric.md`(구조가 내용에 봉사하는가/논지의
      진짜 흐름/확신-구체성 일치/반론 처리/독자 행동가능성 5항), 결정론적
      리듬 검사(`rhythm_stats`: 문장 길이 변동계수, `scan_composition_cliches`:
      상투적 도입·마무리)를 갖춤
- [x] 첫 파일럿 실행 (`korean-writing-orchestrator/eval/runs/2026-09-14-champion-vs-naive/`):
      champion(프로세스 적용) vs naive 4사례, champion 4승. 리듬 지표가 예상과
      다르게 나와("균일하게 짧음"과 "메트로놈 리듬"을 CV 하나로 구분 못 함)
      임계값 미설정 결정이 맞았음을 확인. must_preserve 리터럴 불일치로 중대 실패
      1건도 발견(의미는 맞지만 문자열이 정확히 안 맞음, `korean-plain-writer`
      파일럿의 val-policy-01과 같은 패턴). 자기채점 파일럿이라 표본 작음
- [x] 리듬 지표를 실제 연구(Goh·Barabási 2008 burstiness 공식, 단어 수 기준)로
      교체 — 처음 파일럿에서 쓴 글자 수·단순 CV 분석 일부가 단위를 바꾸자 틀린
      것으로 드러나 정정함(`korean-writing-orchestrator/eval/runs/
      2026-09-14-champion-vs-naive/README.md`의 "갱신 이력")
- [x] 첫 독립 재채점: `Agent` 툴로 이 대화 맥락이 없는 별도 opus 모델에게 개선
      라운드 1의 블라인드 쌍을 다시 채점시킴 — 원래 자기채점과 정확히 같은
      결과(challenger 4승, 무승부 8건, 같은 이유)가 나와 승격 판단이 자기
      편향만은 아니었다는 첫 신호를 얻음. 다만 opus도 Claude 계열이라 진짜
      교차 벤더는 아니고, 의미 게이트는 재채점 안 함, 사람 채점자는 아직 0명
      (`korean-plain-writer/eval/runs/2026-09-14-round1-tense-aspect/README.md`)
- [x] 외부 프로젝트 im-not-ai(`epoko77-ai/im-not-ai`) 검토: 이전에 참고된 적이
      없다는 것을 `grep`과 전체 git 이력 검색으로 확인한 뒤, 코퍼스 실측 방법론과
      결과를 정독. vendor 카탈로그 패턴 25·26·40이 통념과 반대(사람이 AI보다
      더 자주 씀)라는 근거를 찾아 개선 라운드 2의 근거로 채택
- [x] 개선 라운드 2 실행, **미승격** (`eval/runs/2026-09-14-round2-corpus-correction/`):
      "에 대해"/"를 통해"/"것이다" 세 패턴을 저빈도에서는 신호로 보지 않는 안내를
      `ai-tell-catalog.md`에 추가하는 challenger를 만들어 비교. 사례 3개 중 실제
      출력이 갈린 건 1개뿐이고, 그 사례에서 자가 채점(sonnet)과 독립 채점(opus)이
      정반대로 갈림 — 원인은 가설이 아니라 **사례 설계 결함**(challenger 출력을
      원문과 완전히 동일하게 만들어 "저빈도 패턴 유지"가 아니라 "편집 안 함"으로
      읽힘)으로 진단. `scan_grammar_patterns`에 "것이다" 종결 탐지 패턴이 아예
      없다는 기존 격차도 발견(이번 범위 밖이라 미수정). 라이브 스킬 미반영
- [ ] 라운드 2 후속: 사례 재설계(챌린저가 저빈도 패턴만 남기고 나머지는 실제 편집)
      후 재시도, 또는 "것이다" 정적 탐지 패턴 추가 — 다음 라운드 시작 전 사람이 방향
      선택
- [ ] 진짜 다른 회사 LLM 채점자와 사람 2명 이상으로 하네스 첫 정식(독립) 실행
- [ ] 저장소 밖 비공개 테스트셋 구축
- [x] 평가·글쓰기 기준 근거 자료 조사 (`eval/related-work.md`): 텍스트 스타일 전이의
      스타일/내용/유창성 3축 평가, 사람 평가 모범 사례(van der Lee 외), LLM 채점자
      선례, 국립국어원 공공언어 자료, 한국어 가독성 공식 연구, 쉬운 글 효과 연구
- [x] 유창성 체크 축 추가 (`eval/fluency-rubric.md`), 자연도·의미보존과 분리해서 채점
- [x] 국립국어원 "쉬운 공문서 쓰기 길잡이" 1장(8~20쪽) 사용자가 직접 캡처해서 확인.
      `plain-vocabulary-map.md`에 어휘 순화 사례 반영, "다듬은 말" 데이터베이스(18,000건+)
      찾아 들어가는 법 기록, `genre-rules.md`에 장르 공통 원칙(고압적·차별적 표현,
      접속어·조사 정확성, 긍정문, 목록화) 추가
- [ ] 같은 자료 3부(60~105쪽, 유형별 실제 문서 쓰기, 특히 96쪽 "누리소통망서비스
      홍보 글 쓰기")도 확인해서 `genre-rules.md` 보강. 로컬 PDF 리더용 추출 프롬프트를
      `eval/pdf-extraction-prompt.md`에 준비해 둠
- [ ] 문장 길이 등 간단한 자체 가독성 지표 추가 (한국어 가독성 공식 원문은 KCI 학술
      DB 안에 있어 이번엔 확인 못 함)
