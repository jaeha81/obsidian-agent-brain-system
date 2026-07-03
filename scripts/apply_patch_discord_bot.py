#!/usr/bin/env python3
"""
discord_bot.py 패치 스크립트 — 2026-06-09
적용 항목:
  1. thinking_msg.edit() → discord.errors.NotFound 예외 처리 (5곳 + voice 1곳)
  2. timeout=300 하드코딩 → BUCKY_TIMEOUT env 변수 참조 (2곳)
실행: python apply_patch_discord_bot.py
"""

from pathlib import Path
import shutil
import sys

TARGET = Path(__file__).parent / "discord_bot.py"

if not TARGET.exists():
    print(f"❌ 파일 없음: {TARGET}")
    sys.exit(1)

# 백업
backup = TARGET.with_suffix(".py.bak_20260609")
shutil.copy2(TARGET, backup)
print(f"✅ 백업 생성: {backup.name}")

code = TARGET.read_text(encoding="utf-8")
original = code

# ── 패치 1: voice 채널 thinking_msg.edit ──────────────────────────────────────
old = (
    '                voice_chunks = split_message(reply)\n'
    '                await thinking_msg.edit(content=voice_chunks[0])\n'
    '                for chunk in voice_chunks[1:]:\n'
    '                    await ch.send(chunk)'
)
new = (
    '                voice_chunks = split_message(reply)\n'
    '                try:\n'
    '                    await thinking_msg.edit(content=voice_chunks[0])\n'
    '                except discord.errors.NotFound:\n'
    '                    await ch.send(voice_chunks[0])\n'
    '                for chunk in voice_chunks[1:]:\n'
    '                    await ch.send(chunk)'
)
if old in code:
    code = code.replace(old, new, 1)
    print("✅ 패치1 적용 (voice thinking_msg)")
else:
    print("⚠️  패치1 스킵 (이미 적용됐거나 코드 변경됨)")

# ── 패치 2: startproject thinking_msg.edit ────────────────────────────────────
old = (
    '                preview = plan_text[:700] + ("..." if len(plan_text) > 700 else "")\n'
    '                await thinking_msg.edit(content=(\n'
    '                    f"✅ **프로젝트 계획 생성 완료** — `{project_name}`\\n"\n'
    '                    f"저장: `03_Projects/{note_fname}`\\n\\n{preview}"\n'
    '                ))\n'
    '            except Exception as e:\n'
    '                await thinking_msg.edit(content=f"⚠️ startproject 오류: {e}")'
)
new = (
    '                preview = plan_text[:700] + ("..." if len(plan_text) > 700 else "")\n'
    '                _msg = (\n'
    '                    f"✅ **프로젝트 계획 생성 완료** — `{project_name}`\\n"\n'
    '                    f"저장: `03_Projects/{note_fname}`\\n\\n{preview}"\n'
    '                )\n'
    '                try:\n'
    '                    await thinking_msg.edit(content=_msg)\n'
    '                except discord.errors.NotFound:\n'
    '                    await message.channel.send(_msg)\n'
    '            except Exception as e:\n'
    '                _err_msg = f"⚠️ startproject 오류: {e}"\n'
    '                try:\n'
    '                    await thinking_msg.edit(content=_err_msg)\n'
    '                except discord.errors.NotFound:\n'
    '                    await message.channel.send(_err_msg)'
)
if old in code:
    code = code.replace(old, new, 1)
    print("✅ 패치2 적용 (startproject thinking_msg)")
else:
    print("⚠️  패치2 스킵 (이미 적용됐거나 코드 변경됨)")

# ── 패치 3: checkpoint thinking_msg.edit ─────────────────────────────────────
old = (
    '                await thinking_msg.edit(content=(\n'
    '                    f"💾 **체크포인트 저장 완료**\\n"\n'
    '                    f"파일: `05_Logs/{fname_cp}`\\n"\n'
    '                    f"미완료 {len(pending_cl)}개 · 승인대기 {len(pending_approvals)}개"\n'
    '                ))\n'
    '            except Exception as e:\n'
    '                await thinking_msg.edit(content=f"⚠️ checkpoint 오류: {e}")'
)
new = (
    '                _cp_msg = (\n'
    '                    f"💾 **체크포인트 저장 완료**\\n"\n'
    '                    f"파일: `05_Logs/{fname_cp}`\\n"\n'
    '                    f"미완료 {len(pending_cl)}개 · 승인대기 {len(pending_approvals)}개"\n'
    '                )\n'
    '                try:\n'
    '                    await thinking_msg.edit(content=_cp_msg)\n'
    '                except discord.errors.NotFound:\n'
    '                    await message.channel.send(_cp_msg)\n'
    '            except Exception as e:\n'
    '                _cp_err = f"⚠️ checkpoint 오류: {e}"\n'
    '                try:\n'
    '                    await thinking_msg.edit(content=_cp_err)\n'
    '                except discord.errors.NotFound:\n'
    '                    await message.channel.send(_cp_err)'
)
if old in code:
    code = code.replace(old, new, 1)
    print("✅ 패치3 적용 (checkpoint thinking_msg)")
else:
    print("⚠️  패치3 스킵 (이미 적용됐거나 코드 변경됨)")

# ── 패치 4: 일반 채팅 핸들러 thinking_msg.edit ───────────────────────────────
old = (
    '    chunks = split_message(reply)\n'
    '    await thinking_msg.edit(content=chunks[0])\n'
    '    for chunk in chunks[1:]:\n'
    '        await message.channel.send(chunk)\n'
    '\n'
    '    write_discord_message(message, reply, status="answered")'
)
new = (
    '    chunks = split_message(reply)\n'
    '    try:\n'
    '        await thinking_msg.edit(content=chunks[0])\n'
    '    except discord.errors.NotFound:\n'
    '        await message.channel.send(chunks[0])\n'
    '    for chunk in chunks[1:]:\n'
    '        await message.channel.send(chunk)\n'
    '\n'
    '    write_discord_message(message, reply, status="answered")'
)
if old in code:
    code = code.replace(old, new, 1)
    print("✅ 패치4 적용 (일반 채팅 thinking_msg)")
else:
    print("⚠️  패치4 스킵 (이미 적용됐거나 코드 변경됨)")

# ── 패치 5: work 채널 핸들러 thinking_msg.edit ───────────────────────────────
old = (
    '                chunks = split_message(reply)\n'
    '                await thinking_msg.edit(content=chunks[0])\n'
    '                for chunk in chunks[1:]:\n'
    '                    await message.channel.send(chunk)\n'
    '\n'
    '                # 음성 채널 TTS 재생 (입장 중인 경우)'
)
new = (
    '                chunks = split_message(reply)\n'
    '                try:\n'
    '                    await thinking_msg.edit(content=chunks[0])\n'
    '                except discord.errors.NotFound:\n'
    '                    await message.channel.send(chunks[0])\n'
    '                for chunk in chunks[1:]:\n'
    '                    await message.channel.send(chunk)\n'
    '\n'
    '                # 음성 채널 TTS 재생 (입장 중인 경우)'
)
if old in code:
    code = code.replace(old, new, 1)
    print("✅ 패치5 적용 (work 채널 thinking_msg)")
else:
    print("⚠️  패치5 스킵 (이미 적용됐거나 코드 변경됨)")

# ── 패치 6: gdrive migrator timeout=300 → env var ────────────────────────────
old = '                            capture_output=True, text=True, encoding="utf-8", timeout=300'
new = '                            capture_output=True, text=True, encoding="utf-8", timeout=int(os.getenv("BUCKY_TIMEOUT", "900"))'
if old in code:
    code = code.replace(old, new, 1)
    print("✅ 패치6 적용 (gdrive migrator timeout)")
else:
    print("⚠️  패치6 스킵 (이미 적용됐거나 코드 변경됨)")

# ── 패치 7: multi-task parallel timeout=300.0 → env var ──────────────────────
old = '                        timeout=300.0,'
new = '                        timeout=float(os.getenv("BUCKY_TIMEOUT", "900")),'
if old in code:
    code = code.replace(old, new, 1)
    print("✅ 패치7 적용 (multi-task timeout)")
else:
    print("⚠️  패치7 스킵 (이미 적용됐거나 코드 변경됨)")

# ── 변경사항 저장 ──────────────────────────────────────────────────────────────
if code == original:
    print("\n⚠️  변경 없음 — 모든 패치가 이미 적용되어 있거나 코드가 변경됐습니다.")
    backup.unlink(missing_ok=True)
else:
    Target = TARGET
    Target.write_text(code, encoding="utf-8")
    changed = sum(1 for a, b in zip(original.splitlines(), code.splitlines()) if a != b)
    print(f"\n✅ 완료 — discord_bot.py 업데이트 ({len(code) - len(original):+d}자, ~{changed}줄 변경)")
    print(f"   백업: {backup.name}")
    print("\n봇을 재시작해야 변경사항이 적용됩니다:")
    print("  discord_bot.pid 파일 삭제 후 discord_bot.py 재실행")
