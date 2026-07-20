#!/usr/bin/env python3
"""
Wishket 이메일 자동 응답 에이전트

클라이언트 문의/응답 이메일 감지 → Claude 초안 생성 → Discord 승인 → 네이버 메일 자동 발송

Usage:
    python wishket_email_responder.py          # 전체 파이프라인 실행
    python wishket_email_responder.py --send [id]   # 승인된 초안 발송
    python wishket_email_responder.py --list        # 대기 중 초안 목록
"""

import asyncio
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

_ROOT = Path(__file__).parent.parent
PENDING_FILE = _ROOT / "ObsidianVault" / "10_AgentBus" / "email_pending_responses.json"
PROFILE_DIR = Path(os.environ.get("USERPROFILE", "~")) / ".playwright-naver-sessions"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
BRIEFING_CHANNEL_ID = os.getenv("BRIEFING_CHANNEL_ID", "")

FREELANCER_NAME = os.getenv("FREELANCER_NAME", "개발자")
FREELANCER_SKILLS = os.getenv(
    "FREELANCER_SKILLS",
    "Python, FastAPI, Discord 봇, AI/Claude API 연동, 자동화, 웹 스크래핑",
)

# 알림 이메일 필터 (이 패턴에 매칭되면 자동 응답 대상 아님)
_NOTIFICATION_PATTERNS = [
    r"wishket\.com",
    r"noreply@",
    r"no-reply@",
    r"알림메일",
    r"자동발송",
    r"admin@",
    r"notification@",
]
_NOTIFICATION_SUBJECTS = [
    "공고가 등록", "새 프로젝트", "결제 안내", "정산 안내",
    "공지사항", "서비스 안내", "회원가입", "비밀번호",
]

REPLY_SYSTEM_PROMPT = f"""당신은 프리랜서 개발자({FREELANCER_NAME})의 이메일 비서입니다.
클라이언트 이메일에 대한 전문적이고 친절한 한국어 답장 초안을 작성합니다.

작성 원칙:
1. 첫 문장: 연락 주셔서 감사하다는 인사
2. 상대방 이메일의 핵심 요청/질문에 구체적으로 답변
3. 기술 스택 언급 시: {FREELANCER_SKILLS}
4. 빠른 답변/미팅 제안으로 마무리
5. 분량: 200~400자
6. 톤: 전문적이고 친근하되 과하지 않게
7. 반드시 완성된 이메일 형식으로 (제목 제외, 본문만)"""

REPLY_USER_TEMPLATE = """다음 이메일에 대한 답장 초안을 작성해주세요.

발신자: {sender}
제목: {subject}
내용:
{body}

위 이메일에 대한 답장을 한국어로 작성해주세요."""


def load_pending() -> dict:
    if PENDING_FILE.exists():
        try:
            return json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"pending": [], "sent": []}


def save_pending(data: dict) -> None:
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_notification_email(sender: str, subject: str) -> bool:
    combined = (sender + " " + subject).lower()
    for pat in _NOTIFICATION_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return True
    for kw in _NOTIFICATION_SUBJECTS:
        if kw in subject:
            return True
    return False


def _get_processed_ids() -> set[str]:
    data = load_pending()
    ids = {r["id"] for r in data.get("pending", [])}
    ids |= {r["id"] for r in data.get("sent", [])}
    return ids


def _make_email_id(sender: str, subject: str) -> str:
    raw = f"{sender}|{subject}"
    return f"resp_{abs(hash(raw)) % 10**8:08d}"


async def scan_client_emails_playwright(limit: int = 20) -> list[dict]:
    """네이버 메일 받은편지함에서 클라이언트 이메일 감지."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Responder] playwright 미설치: pip install playwright && playwright install msedge")
        return []

    if not PROFILE_DIR.exists():
        print("[Responder] 세션 없음 — python wishket_gmail_scraper.py --login 실행")
        return []

    processed = _get_processed_ids()
    found: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="msedge",
            headless=True,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            await page.goto("https://mail.naver.com/", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            if "login" in page.url or "nid.naver.com" in page.url:
                print("[Responder] 세션 만료 — --login 재실행 필요")
                await browser.close()
                return []

            # 받은편지함 (읽지 않은 메일 우선)
            await page.goto("https://mail.naver.com/", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            mail_items = await page.query_selector_all(
                ".mail_item, .item, [class*='mail-item'], [role='row']"
            )
            if not mail_items:
                mail_items = await page.query_selector_all(
                    "a[class*='subject'], .subject a, td.subject"
                )

            print(f"[Responder] 메일 항목: {len(mail_items)}개 검색됨")

            for item in mail_items[:limit]:
                try:
                    await item.click()
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    await asyncio.sleep(0.5)

                    subject_el = await page.query_selector(
                        ".mail_subject, .subject, h2, [class*='subject']"
                    )
                    subject = (await subject_el.inner_text()).strip() if subject_el else ""

                    sender_el = await page.query_selector(
                        ".sender, .from, [class*='sender'], [class*='from']"
                    )
                    sender = (await sender_el.inner_text()).strip() if sender_el else ""

                    body_el = await page.query_selector(
                        ".mail_body, .body, [class*='mail-body'], iframe"
                    )
                    body = ""
                    if body_el:
                        tag = await body_el.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "iframe":
                            frame = await body_el.content_frame()
                            if frame:
                                body = await frame.inner_text()
                        else:
                            body = await body_el.inner_text()

                    # 날짜 추출
                    date_el = await page.query_selector(
                        ".date, .time, [class*='date'], [class*='time']"
                    )
                    received_at = (await date_el.inner_text()).strip() if date_el else ""

                    email_id = _make_email_id(sender, subject)

                    if (
                        subject
                        and sender
                        and not _is_notification_email(sender, subject)
                        and email_id not in processed
                    ):
                        found.append(
                            {
                                "id": email_id,
                                "sender": sender,
                                "subject": subject,
                                "body": body[:1000],
                                "received_at": received_at,
                                "detected_at": datetime.now().isoformat(),
                            }
                        )
                        print(f"[Responder] 클라이언트 메일 감지: {subject[:50]} (from {sender})")

                    await page.go_back()
                    await page.wait_for_load_state("networkidle", timeout=10000)

                except Exception as e:
                    print(f"[Responder] 메일 파싱 오류: {e}")
                    try:
                        await page.go_back()
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass

        except Exception as e:
            print(f"[Responder] 스캔 오류: {e}")
        finally:
            await browser.close()

    return found


def generate_reply_draft(email_data: dict) -> str:
    """Claude CLI로 답장 초안 생성."""
    user_prompt = REPLY_USER_TEMPLATE.format(
        sender=email_data.get("sender", ""),
        subject=email_data.get("subject", ""),
        body=email_data.get("body", "내용 없음"),
    )
    full_prompt = f"{REPLY_SYSTEM_PROMPT}\n\n{user_prompt}"
    env = os.environ.copy()
    env["BUCKY_SUBPROCESS"] = "1"
    # claude.ai 구독 로그인으로 실행되도록 API 키 인증을 제거한다.
    # (.env의 ANTHROPIC_API_KEY는 잔액 부족 → claude -p가 "Credit balance is too low"로 실패)
    for _k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_API_KEY"):
        env.pop(_k, None)

    sys.path.insert(0, str(Path(__file__).parent))
    from wishket_proposal_generator import _resolve_claude_cmd

    try:
        result = subprocess.run(
            [_resolve_claude_cmd(), "--dangerously-skip-permissions", "-p", full_prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return f"[초안 생성 실패] {result.stderr[:200]}"
    except Exception as e:
        return f"[초안 생성 오류] {e}"


def save_draft_pending(email_data: dict, draft: str) -> str:
    """초안을 pending 상태로 저장. 생성된 ID 반환."""
    data = load_pending()
    record = {
        **email_data,
        "draft": draft,
        "status": "pending_approval",
        "draft_at": datetime.now().isoformat(),
        "discord_posted": False,
    }
    data["pending"].append(record)
    save_pending(data)
    return email_data["id"]


def _send_discord(text: str) -> None:
    """Discord 웹훅 또는 Bot API로 메시지 전송."""
    if DISCORD_WEBHOOK:
        try:
            data = json.dumps({"content": text[:2000]}).encode("utf-8")
            req = urllib.request.Request(
                DISCORD_WEBHOOK,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
            return
        except Exception as e:
            print(f"[Responder] 웹훅 전송 실패: {e}")

    if DISCORD_BOT_TOKEN and BRIEFING_CHANNEL_ID:
        try:
            import requests  # type: ignore
            requests.post(
                f"https://discord.com/api/v10/channels/{BRIEFING_CHANNEL_ID}/messages",
                headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
                json={"content": text[:2000]},
                timeout=5,
            )
        except Exception as e:
            print(f"[Responder] Bot API 전송 실패: {e}")


def post_approval_request(email_id: str) -> None:
    """Discord에 승인 요청 메시지 게시."""
    data = load_pending()
    record = next((r for r in data["pending"] if r["id"] == email_id), None)
    if not record:
        print(f"[Responder] ID {email_id} 없음")
        return

    msg = (
        f"📨 **[이메일 자동응답 승인 요청]** ID: `{email_id}`\n"
        f"**발신자**: {record['sender']}\n"
        f"**제목**: {record['subject']}\n"
        f"**수신**: {record.get('received_at', '?')}\n\n"
        f"**초안:**\n```\n{record['draft'][:800]}\n```\n\n"
        f"✅ 발송: `/wishket_reply send {email_id}`\n"
        f"❌ 취소: `/wishket_reply cancel {email_id}`\n"
        f"✏️ 수정 후 발송: `/wishket_reply edit {email_id} [수정내용]`"
    )
    _send_discord(msg)

    # discord_posted 플래그 갱신
    for r in data["pending"]:
        if r["id"] == email_id:
            r["discord_posted"] = True
    save_pending(data)
    print(f"[Responder] Discord 승인 요청 게시: {email_id}")


async def send_reply_playwright(email_id: str) -> bool:
    """네이버 메일 Playwright로 실제 답장 발송."""
    data = load_pending()
    record = next((r for r in data["pending"] if r["id"] == email_id), None)
    if not record:
        print(f"[Responder] ID {email_id} 없음")
        return False

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Responder] playwright 미설치")
        return False

    if not PROFILE_DIR.exists():
        print("[Responder] 세션 없음")
        return False

    success = False
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="msedge",
            headless=True,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            # 네이버 메일 쓰기 페이지로 직접 이동
            await page.goto("https://mail.naver.com/", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            if "login" in page.url or "nid.naver.com" in page.url:
                print("[Responder] 세션 만료")
                await browser.close()
                return False

            # 메일쓰기 클릭
            write_btn = await page.query_selector(
                "a[href*='write'], button[class*='write'], .btn_write, [class*='compose']"
            )
            if write_btn:
                await write_btn.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
            else:
                await page.goto("https://mail.naver.com/write", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=10000)

            # 받는 사람 입력
            to_input = await page.query_selector(
                "input[name='to'], input[placeholder*='받는'], .to_input input"
            )
            if to_input:
                await to_input.fill(record["sender"])
                await to_input.press("Enter")
                await asyncio.sleep(0.5)

            # 제목 입력 (Re: 추가)
            subject_input = await page.query_selector(
                "input[name='subject'], input[placeholder*='제목'], .subject_input"
            )
            if subject_input:
                original_subject = record["subject"]
                reply_subject = (
                    original_subject
                    if original_subject.startswith("Re:")
                    else f"Re: {original_subject}"
                )
                await subject_input.fill(reply_subject)

            # 본문 입력
            body_area = await page.query_selector(
                "div[contenteditable='true'], textarea[name='body'], .editor_area, iframe[name*='editor']"
            )
            if body_area:
                tag = await body_area.evaluate("el => el.tagName.toLowerCase()")
                if tag == "iframe":
                    frame = await body_area.content_frame()
                    if frame:
                        editable = await frame.query_selector(
                            "body, div[contenteditable='true']"
                        )
                        if editable:
                            await editable.fill(record["draft"])
                else:
                    await body_area.fill(record["draft"])

            # 보내기 클릭
            send_btn = await page.query_selector(
                "button[class*='send'], .btn_send, button[type='submit']"
            )
            if send_btn:
                await send_btn.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
                success = True
                print(f"[Responder] 답장 발송 완료: {record['subject'][:50]}")
            else:
                print("[Responder] 보내기 버튼 미발견 — 수동 발송 필요")

        except Exception as e:
            print(f"[Responder] 발송 오류: {e}")
        finally:
            await browser.close()

    if success:
        # pending → sent 이동
        data = load_pending()
        pending = data.get("pending", [])
        sent = data.get("sent", [])
        for i, r in enumerate(pending):
            if r["id"] == email_id:
                r["status"] = "sent"
                r["sent_at"] = datetime.now().isoformat()
                sent.append(r)
                pending.pop(i)
                break
        data["pending"] = pending
        data["sent"] = sent
        save_pending(data)
        _send_discord(f"✅ 답장 발송 완료! ID: `{email_id}` — {record['subject'][:50]}")

    return success


def list_pending() -> None:
    data = load_pending()
    pending = data.get("pending", [])
    if not pending:
        print("[Responder] 대기 중인 초안 없음")
        return
    print(f"\n[Responder] 대기 중 초안 {len(pending)}개:")
    for r in pending:
        print(f"  [{r['id']}] {r['subject'][:50]} (from {r['sender']}) — {r['status']}")


def run(scan_limit: int = 20) -> dict:
    """전체 파이프라인: 스캔 → 초안 생성 → Discord 게시."""
    print("[Responder] 클라이언트 이메일 스캔 시작...")
    emails = asyncio.run(scan_client_emails_playwright(limit=scan_limit))

    if not emails:
        print("[Responder] 신규 클라이언트 이메일 없음")
        return {"status": "no_emails", "count": 0}

    print(f"[Responder] {len(emails)}개 클라이언트 이메일 감지")
    results = []

    for email_data in emails:
        print(f"[Responder] 초안 생성: {email_data['subject'][:50]}")
        draft = generate_reply_draft(email_data)
        email_id = save_draft_pending(email_data, draft)
        post_approval_request(email_id)
        results.append({"id": email_id, "subject": email_data["subject"]})

    return {"status": "ok", "count": len(results), "items": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wishket 이메일 자동 응답 에이전트")
    parser.add_argument("--send", metavar="ID", help="승인된 초안 발송")
    parser.add_argument("--cancel", metavar="ID", help="초안 취소")
    parser.add_argument("--list", action="store_true", help="대기 중 초안 목록")
    parser.add_argument("--limit", type=int, default=20, help="스캔 메일 수")
    args = parser.parse_args()

    if args.list:
        list_pending()
    elif args.send:
        ok = asyncio.run(send_reply_playwright(args.send))
        print("발송 완료" if ok else "발송 실패 (수동 처리 필요)")
    elif args.cancel:
        data = load_pending()
        before = len(data["pending"])
        data["pending"] = [r for r in data["pending"] if r["id"] != args.cancel]
        if len(data["pending"]) < before:
            save_pending(data)
            print(f"취소 완료: {args.cancel}")
        else:
            print(f"ID 없음: {args.cancel}")
    else:
        result = run(scan_limit=args.limit)
        print(f"\n완료: {result['count']}개 처리")
