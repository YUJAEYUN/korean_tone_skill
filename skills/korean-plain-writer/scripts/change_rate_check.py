#!/usr/bin/env python3
"""원문과 재작성본을 비교해 변경률을 계산하는 스크립트.

원래 DaleSeo/korean-skills의 humanizer가 쓰는 30%/50% 임계값을 그대로 가져왔지만,
`eval/`에서 이 스킬 자신의 45개 예문 뱅크로 재검증한 결과 그 임계값이 이 스킬에는
맞지 않았다(중앙값 88%, 45개 중 41개가 "50% 초과"로 잡힘 — 자세한 내용은
`eval/README.md`와 `references/ai-tell-catalog.md`의 "변경률 가드" 절 참고).
humanizer는 이미 완성된 글을 가볍게 손보는 스킬이고, korean-plain-writer는 격식체를
쉬운 말로 통째로 재구성하는 스킬이라 변경 폭 자체가 크다. 그래서 이 스크립트는
변경률을 정보로만 보여주고, 실제 의미 보존 여부는 별도의 6항 체크리스트(사람/모델이
판단)가 담당한다. 이 스크립트가 잡는 건 "이례적으로 큰" 경우, 즉 우리 예문 뱅크의
관측 범위(19~136%)를 크게 벗어나는 경우뿐이다.

사용법:
    python change_rate_check.py original.txt revised.txt
    또는 파이썬에서 직접:
        from change_rate_check import check_change_rate
        result = check_change_rate(original_text, revised_text)
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass

_PUNCT_RE = re.compile(r"[^\w가-힣]")

# 45개 예문 뱅크(informational/essay/practical)를 이 스크립트로 직접 측정한 값:
# 중앙값 88%, 범위 19~136%. 136%를 넘는 경우만 "review"로 표시한다.
REVIEW_THRESHOLD = 1.50


def _normalize(token: str) -> str:
    """비교용으로 문장부호를 제거한 토큰을 반환한다."""
    return _PUNCT_RE.sub("", token)


def _tokenize(text: str) -> list[str]:
    return text.split()


@dataclass
class ChangeRateResult:
    change_rate: float  # 0.0 이상, 상한 없음
    status: str  # "normal" | "review"
    message: str


def check_change_rate(original: str, revised: str) -> ChangeRateResult:
    orig_tokens = _tokenize(original)
    rev_tokens = _tokenize(revised)

    orig_norm = [_normalize(t) for t in orig_tokens]
    rev_norm = [_normalize(t) for t in rev_tokens]

    matcher = difflib.SequenceMatcher(a=orig_norm, b=rev_norm, autojunk=False)

    changed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        # 문장부호 제거 후에도 내용이 같다면(순수 문장부호/띄어쓰기 차이) 변경으로
        # 세지 않는다. get_opcodes는 이미 정규화된 토큰 기준으로 비교하므로
        # 여기 도달한 구간은 실제 내용 차이다.
        changed += max(i2 - i1, j2 - j1)

    total = max(len(orig_norm), 1)
    rate = changed / total

    if rate < REVIEW_THRESHOLD:
        status = "normal"
        message = (
            f"변경률 {rate:.0%}. korean-plain-writer는 격식체를 쉬운 말로 통째로 "
            "재구성하는 경우가 많아 이 정도는 정상 범위입니다(예문 뱅크 45개 기준 "
            "중앙값 88%, 범위 19~136%)."
        )
    else:
        status = "review"
        message = (
            f"변경률이 {rate:.0%}로, 예문 뱅크에서 관측된 범위(최대 136%)를 크게 "
            "벗어났습니다. 의미 보존 체크리스트를 다시 확인하세요."
        )

    return ChangeRateResult(change_rate=rate, status=status, message=message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", help="원문 텍스트 파일 경로")
    parser.add_argument("revised", help="재작성본 텍스트 파일 경로")
    args = parser.parse_args()

    with open(args.original, encoding="utf-8") as f:
        original = f.read()
    with open(args.revised, encoding="utf-8") as f:
        revised = f.read()

    result = check_change_rate(original, revised)
    print(f"변경률: {result.change_rate:.1%}")
    print(f"상태: {result.status}")
    print(result.message)

    return 1 if result.status == "review" else 0


if __name__ == "__main__":
    sys.exit(main())
