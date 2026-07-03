from datetime import datetime

from scripts.session_continuity import build_handoff, numbered_pending_prompt


def test_numbered_pending_prompt_lists_items_and_zero_option():
    prompt = numbered_pending_prompt(["위시켓 로그인 검증", "다음 세션 handoff 확인"])

    assert "1. 위시켓 로그인 검증" in prompt
    assert "2. 다음 세션 handoff 확인" in prompt
    assert "0. 지금은 진행하지 않음" in prompt


def test_handoff_preserves_no_compression_and_next_question():
    content = build_handoff(
        agent="Bucky",
        request="앞 요청과 뒤 수정사항을 합쳐 세션 이관 규칙을 만든다.",
        completed=["권위 문서 업데이트"],
        pending=["사용자에게 다음 진행 번호 질문"],
        blockers=[],
        next_read=["ObsidianVault/00_System/USER_OPERATING_INTENT.md"],
        notes="테스트",
        created=datetime(2026, 6, 20, 10, 0, 0),
    )

    assert "Do Not Compress" in content
    assert "chat compression" in content
    assert "Unfinished Queue" in content
    assert "1. 사용자에게 다음 진행 번호 질문" in content
    assert "ObsidianVault/00_System/USER_OPERATING_INTENT.md" in content
