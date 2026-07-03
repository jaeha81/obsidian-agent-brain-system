"""Tests for generate_daily_plus_dashboard.py

검증 목표:
1. DASHBOARD_INTERACTION_JS 에 /intake 엔드포인트 로직이 존재한다.
2. payloadForBuckyOS 가 dashboard_type / title 필드를 포함한다.
3. postToBucky 가 base+"/intake" 를 사용하고 request_id 를 반환한다.
4. 생성된 docs/daily-plus.html 에 동일한 로직이 보존된다.
"""

import re
import sys
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def extract_function(js_text: str, name: str) -> str:
    """함수 블록을 중괄호 카운팅으로 추출한다."""
    pattern = r'((?:async\s+)?function\s+' + re.escape(name) + r'\s*\([^)]*\)\s*\{)'
    m = re.search(pattern, js_text)
    if not m:
        return ""
    pos = m.end()
    depth = 1
    while pos < len(js_text) and depth > 0:
        if js_text[pos] == '{':
            depth += 1
        elif js_text[pos] == '}':
            depth -= 1
        pos += 1
    return js_text[m.start():pos].strip()


def get_dashboard_js() -> str:
    """generate_daily_plus_dashboard.py 의 DASHBOARD_INTERACTION_JS 를 반환한다."""
    src = (ROOT / "scripts" / "generate_daily_plus_dashboard.py").read_text(encoding="utf-8")
    m = re.search(r'DASHBOARD_INTERACTION_JS\s*=\s*"""(.*?)"""', src, re.DOTALL)
    if not m:
        raise AssertionError("DASHBOARD_INTERACTION_JS 블록을 찾을 수 없음")
    # Python 이스케이프 → 실제 JS 문자열로 변환
    return m.group(1).replace("\\\\", "\\")


def get_generated_html_js() -> str:
    """docs/daily-plus.html 의 <script> 블록을 반환한다."""
    html = (ROOT / "docs" / "daily-plus.html").read_text(encoding="utf-8")
    start = html.find("<script>")
    end = html.find("</script>") + len("</script>")
    return html[start:end]


# ── 생성기 JS 템플릿 검증 ──────────────────────────────────────────────────

class TestDashboardInteractionJS(unittest.TestCase):
    """DASHBOARD_INTERACTION_JS 템플릿 자체를 검증한다."""

    @classmethod
    def setUpClass(cls):
        cls.js = get_dashboard_js()

    # ── payloadForBuckyOS ─────────────────────────────────────────────────

    def test_payload_has_dashboard_type_field(self):
        fn = extract_function(self.js, "payloadForBuckyOS")
        self.assertIn('dashboard_type: "daily_plus"', fn,
                      "payloadForBuckyOS 에 dashboard_type: \"daily_plus\" 없음")

    def test_payload_has_title_field(self):
        fn = extract_function(self.js, "payloadForBuckyOS")
        self.assertIn("title:", fn,
                      "payloadForBuckyOS 에 title 필드 없음")

    def test_payload_has_channel_role(self):
        fn = extract_function(self.js, "payloadForBuckyOS")
        self.assertIn('channel_role: "daily-plus-intake"', fn)

    def test_payload_has_follow_up_state(self):
        fn = extract_function(self.js, "payloadForBuckyOS")
        self.assertIn('follow_up_state: "awaiting_user_instruction"', fn)

    # ── postToBucky ───────────────────────────────────────────────────────

    def test_post_uses_intake_suffix(self):
        fn = extract_function(self.js, "postToBucky")
        self.assertIn('"/intake"', fn,
                      "postToBucky 가 /intake 경로를 조합하지 않음")

    def test_post_does_not_use_raw_endpoint(self):
        fn = extract_function(self.js, "postToBucky")
        # 구버전: fetch(endpoint, ...) — 직접 endpoint 변수 사용
        self.assertNotIn("fetch(endpoint,", fn.replace(" ", "").replace("\n", ""),
                         "postToBucky 가 raw endpoint 를 사용함 (intakeUrl 을 써야 함)")

    def test_post_uses_intakeUrl_variable(self):
        fn = extract_function(self.js, "postToBucky")
        self.assertIn("intakeUrl", fn)

    def test_post_returns_request_id(self):
        fn = extract_function(self.js, "postToBucky")
        self.assertIn("request_id", fn,
                      "postToBucky 가 response 의 request_id 를 반환하지 않음")

    def test_post_beacon_uses_intakeUrl(self):
        fn = extract_function(self.js, "postToBucky")
        self.assertIn("sendBeacon(intakeUrl", fn,
                      "sendBeacon 도 intakeUrl 을 사용해야 함")

    def test_post_strips_trailing_slash(self):
        fn = extract_function(self.js, "postToBucky")
        self.assertIn("replace(", fn,
                      "trailing slash 제거 코드가 없음")

    # ── 상수 ──────────────────────────────────────────────────────────────

    def test_default_endpoint_localhost_8765(self):
        self.assertIn('DEFAULT_BUCKY_ENDPOINT = "http://localhost:8765"', self.js)

    def test_endpoint_key_consistent(self):
        self.assertIn('ENDPOINT_KEY = "dailyPlusBuckyOsIntakeUrl"', self.js)


# ── 생성된 HTML 검증 ───────────────────────────────────────────────────────

class TestGeneratedHTMLMatchesTemplate(unittest.TestCase):
    """docs/daily-plus.html 의 JS 블록이 템플릿과 동일한 핵심 로직을 갖는지 확인한다."""

    @classmethod
    def setUpClass(cls):
        cls.html_js = get_generated_html_js()

    def test_html_has_intake_url(self):
        self.assertIn('"/intake"', self.html_js,
                      "생성된 HTML 에 /intake 경로 없음")

    def test_html_payload_has_dashboard_type(self):
        fn = extract_function(self.html_js, "payloadForBuckyOS")
        self.assertIn('dashboard_type: "daily_plus"', fn)

    def test_html_payload_has_title(self):
        fn = extract_function(self.html_js, "payloadForBuckyOS")
        self.assertIn("title:", fn)

    def test_html_post_uses_intakeUrl(self):
        fn = extract_function(self.html_js, "postToBucky")
        self.assertIn("intakeUrl", fn)

    def test_html_post_returns_request_id(self):
        fn = extract_function(self.html_js, "postToBucky")
        self.assertIn("request_id", fn)

    def test_html_beacon_uses_intakeUrl(self):
        fn = extract_function(self.html_js, "postToBucky")
        self.assertIn("sendBeacon(intakeUrl", fn)

    def test_html_no_raw_endpoint_fetch(self):
        fn = extract_function(self.html_js, "postToBucky")
        self.assertNotIn("fetch(endpoint,", fn.replace(" ", "").replace("\n", ""))

    # ── 템플릿과 생성 HTML 의 핵심 함수가 동일한지 비교 ──────────────────

    def _normalize(self, text: str) -> str:
        """공백·줄바꿈 차이를 무시하고 비교하기 위한 정규화."""
        return re.sub(r'\s+', ' ', text).strip()

    def test_payloadForBuckyOS_matches_template(self):
        tmpl_fn = extract_function(get_dashboard_js(), "payloadForBuckyOS")
        html_fn = extract_function(self.html_js, "payloadForBuckyOS")
        self.assertEqual(
            self._normalize(tmpl_fn),
            self._normalize(html_fn),
            "payloadForBuckyOS 가 템플릿과 HTML 사이에 다름",
        )

    def test_postToBucky_matches_template(self):
        tmpl_fn = extract_function(get_dashboard_js(), "postToBucky")
        html_fn = extract_function(self.html_js, "postToBucky")
        self.assertEqual(
            self._normalize(tmpl_fn),
            self._normalize(html_fn),
            "postToBucky 가 템플릿과 HTML 사이에 다름",
        )


if __name__ == "__main__":
    unittest.main()
