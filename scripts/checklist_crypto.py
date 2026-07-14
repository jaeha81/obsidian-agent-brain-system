"""체크리스트 공개 미러 암호화 — 저장소가 public이므로 미러는 암호문으로만 게시한다.

미러(docs/data/user_checklist.json)는 GitHub Pages로 그대로 공개된다.
평문으로 두면 주소만 알면 누구나 할 일 제목 전체를 읽는다.

AES-256-GCM + PBKDF2-HMAC-SHA256. 브라우저 Web Crypto와 같은 규격이라
docs/shared/checklist-crypto.js가 같은 비밀번호로 그대로 복호화한다.

비밀번호는 data/.checklist_key(git 미추적)에 한 줄로 둔다.
키가 없거나 암복호에 실패하면 예외를 던진다 — 조용히 평문으로 흘리거나
빈 값을 내주지 않는다(2026-07-11 체크리스트 소실의 원인이 그 패턴이었다).
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = Path(__file__).resolve().parents[1]
KEY_FILE = ROOT / "data" / ".checklist_key"

ITERATIONS = 200_000
SALT_BYTES = 16
IV_BYTES = 12


class KeyUnavailable(RuntimeError):
    """비밀번호를 얻지 못했다. 이 상태로는 미러를 읽을 수도 쓸 수도 없다."""


class DecryptFailed(RuntimeError):
    """비밀번호가 틀렸거나 암호문이 손상됐다."""


def load_password() -> str:
    """비밀번호를 얻는다. 환경변수가 우선, 없으면 키 파일."""
    env = os.environ.get("CHECKLIST_PASSWORD", "").strip()
    if env:
        return env

    if not KEY_FILE.exists():
        raise KeyUnavailable(
            f"비밀번호 파일이 없다: {KEY_FILE}\n"
            "파일을 만들고 비밀번호를 한 줄로 적어라 (환경변수 CHECKLIST_PASSWORD도 가능)."
        )

    password = KEY_FILE.read_text(encoding="utf-8-sig").strip()
    if not password:
        raise KeyUnavailable(f"비밀번호 파일이 비어 있다: {KEY_FILE}")
    return password


def _derive(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS
    )
    return kdf.derive(password.encode("utf-8"))


def is_encrypted(data: object) -> bool:
    return isinstance(data, dict) and data.get("encrypted") is True


def encrypt(plaintext: str, password: str) -> dict:
    salt = os.urandom(SALT_BYTES)
    iv = os.urandom(IV_BYTES)
    ct = AESGCM(_derive(password, salt)).encrypt(iv, plaintext.encode("utf-8"), None)
    return {
        "encrypted": True,
        "v": 1,
        "kdf": "pbkdf2-sha256",
        "iter": ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "ct": base64.b64encode(ct).decode("ascii"),
    }


def decrypt(envelope: dict, password: str) -> str:
    if not is_encrypted(envelope):
        raise DecryptFailed("암호문 봉투가 아니다")
    try:
        salt = base64.b64decode(envelope["salt"])
        iv = base64.b64decode(envelope["iv"])
        ct = base64.b64decode(envelope["ct"])
        key = _derive(password, salt)
        return AESGCM(key).decrypt(iv, ct, None).decode("utf-8")
    except DecryptFailed:
        raise
    except Exception as exc:  # 비번 오류·손상 모두 여기로 — 조용히 넘기지 않는다
        raise DecryptFailed(f"복호화 실패(비밀번호가 틀렸거나 파일이 손상됐다): {exc}") from exc


def encrypt_json(data: dict, password: str) -> str:
    """dict → 암호문 봉투 JSON 문자열."""
    plaintext = json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(encrypt(plaintext, password), ensure_ascii=False, indent=2)


def decrypt_json(envelope: dict, password: str) -> dict:
    """암호문 봉투 → 원래 dict."""
    data = json.loads(decrypt(envelope, password))
    if not isinstance(data, dict):
        raise DecryptFailed("복호화 결과가 객체가 아니다")
    return data
