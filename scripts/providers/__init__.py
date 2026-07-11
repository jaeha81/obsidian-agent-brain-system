"""Bucky OS V3 — provider 어댑터 패키지 (Stage 6).

인터페이스: scripts/core/provider_adapter.py
레지스트리: config/model_registry.yaml providers.* (키 이름은 ADAPTERS와 1:1)

Usage:
    from providers import get_adapter, all_adapters
    adapter = get_adapter("claude_code")
    health = adapter.healthcheck()
"""

from __future__ import annotations

from core.config import load_model_registry
from core.provider_adapter import ProviderAdapter

from providers.anthropic_api_adapter import AnthropicApiAdapter
from providers.claude_cli_adapter import ClaudeCliAdapter
from providers.codex_cli_adapter import CodexCliAdapter
from providers.gemini_adapter import GeminiAdapter
from providers.openai_adapter import OpenAIAdapter

ADAPTERS: dict[str, type[ProviderAdapter]] = {
    cls.name: cls
    for cls in (
        ClaudeCliAdapter,
        CodexCliAdapter,
        OpenAIAdapter,
        GeminiAdapter,
        AnthropicApiAdapter,
    )
}


def get_adapter(name: str, registry: dict | None = None) -> ProviderAdapter | None:
    """이름으로 어댑터 인스턴스 생성. 미등록 이름 → None (crash 금지)."""
    cls = ADAPTERS.get(name)
    if cls is None:
        return None
    providers = (registry or load_model_registry()).get("providers", {})
    entry = providers.get(name, {}) if isinstance(providers, dict) else {}
    return cls(entry)


def all_adapters(registry: dict | None = None) -> dict[str, ProviderAdapter]:
    """등록된 어댑터 전부 인스턴스화."""
    return {name: get_adapter(name, registry) for name in ADAPTERS}
