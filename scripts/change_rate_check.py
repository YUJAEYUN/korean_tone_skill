#!/usr/bin/env python3
"""원문과 재작성본을 비교해 변경률을 계산하는 가드 스크립트.

DaleSeo/korean-skills의 humanizer가 쓰는 변경률 가드(30%/50% 임계값)를 그대로
채택한 구현입니다. 어절(공백 기준 토큰) 단위로 비교하며, 순수 문장부호/공백 차이만
나는 토큰은 변경으로 세지 않습니다.

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


def _normalize(token: str) -> str:
    """비교용으로 문장부호를 제거한 토큰을 반환한다."""
    return _PUNCT_RE.sub("", token)


def _tokenize(text: str) -> list[str]:
    return text.split()


@dataclass
class ChangeRateResult:
    change_rate: float  # 0.0 ~ 1.0
    status: str  # "normal" | "warning" | "stop"
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

    if rate < 0.30:
        status = "normal"
        message = "변경률 정상 범위."
    elif rate <= 0.50:
        status = "warning"
        message = f"변경률 {rate:.0%}로 다소 큼. 의미 보존 재확인 권장."
    else:
        status = "stop"
        message = (
            f"변경률이 {rate:.0%}로 과도합니다. 원본 의미가 변경됐을 가능성이 "
            "있습니다. 더 보수적으로 재작성해드릴까요?"
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

    return 1 if result.status == "stop" else 0


if __name__ == "__main__":
    sys.exit(main())
