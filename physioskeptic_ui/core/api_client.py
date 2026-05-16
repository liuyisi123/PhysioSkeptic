"""
API Client — PhysioSkeptic
Multi-provider LLM client with unified interface.
Providers: OpenAI, Anthropic, DeepSeek, Qwen, Ollama, Azure OpenAI, Mock.
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

# ── optional deps ──────────────────────────────────────────────────────────────
try:
    import openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class CompletionResult:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    latency_ms: float = 0.0
    provider: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


# ── base class ─────────────────────────────────────────────────────────────────

class BaseAPIClient(ABC):
    """Abstract base for all provider clients."""

    def __init__(self, api_key: str = "", model: str = "", **kwargs: Any) -> None:
        self.api_key = api_key
        self.model = model
        self.extra = kwargs

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> CompletionResult:
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        ...

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Default cost estimate — subclasses override."""
        return 0.0

    def _make_openai_messages(self, messages: List[Message]) -> List[Dict]:
        return [{"role": m.role, "content": m.content} for m in messages]


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAIClient(BaseAPIClient):
    PRICE_PER_1K = {
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-5": (0.015, 0.045),
        "gpt-5.2": (0.020, 0.060),
    }

    def __init__(self, api_key: str = "", model: str = "gpt-4o", **kwargs: Any) -> None:
        super().__init__(api_key, model, **kwargs)

    def chat_completion(self, messages, temperature=0.7, max_tokens=2048) -> CompletionResult:
        if not _HAS_OPENAI:
            return self._http_fallback(messages, temperature, max_tokens)
        try:
            client = openai.OpenAI(api_key=self.api_key)
            t0 = time.time()
            resp = client.chat.completions.create(
                model=self.model,
                messages=self._make_openai_messages(messages),
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency = (time.time() - t0) * 1000
            return CompletionResult(
                content=resp.choices[0].message.content or "",
                input_tokens=resp.usage.prompt_tokens,
                output_tokens=resp.usage.completion_tokens,
                model=self.model,
                latency_ms=latency,
                provider="openai",
            )
        except Exception as e:
            return CompletionResult(content="", error=str(e), provider="openai")

    def _http_fallback(self, messages, temperature, max_tokens) -> CompletionResult:
        """Pure HTTP fallback when openai package not installed."""
        try:
            payload = {
                "model": self.model,
                "messages": self._make_openai_messages(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            t0 = time.time()
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload, headers=headers, timeout=60
            )
            latency = (time.time() - t0) * 1000
            r.raise_for_status()
            data = r.json()
            return CompletionResult(
                content=data["choices"][0]["message"]["content"],
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                model=self.model,
                latency_ms=latency,
                provider="openai",
            )
        except Exception as e:
            return CompletionResult(content="", error=str(e), provider="openai")

    def test_connection(self) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            r = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        in_p, out_p = self.PRICE_PER_1K.get(self.model, (0.005, 0.015))
        return (input_tokens * in_p + output_tokens * out_p) / 1000.0


# ── Anthropic ─────────────────────────────────────────────────────────────────

class AnthropicClient(BaseAPIClient):
    PRICE_PER_1K = {
        "claude-3-7-sonnet-20250219": (0.003, 0.015),
        "claude-3-5-haiku-20241022": (0.0008, 0.004),
        "claude-opus-4-5": (0.015, 0.075),
    }

    def __init__(self, api_key: str = "", model: str = "claude-3-7-sonnet-20250219", **kwargs: Any) -> None:
        super().__init__(api_key, model, **kwargs)

    def chat_completion(self, messages, temperature=0.7, max_tokens=2048) -> CompletionResult:
        if not _HAS_ANTHROPIC:
            return self._http_fallback(messages, temperature, max_tokens)
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            # separate system message
            system = ""
            msg_list = []
            for m in messages:
                if m.role == "system":
                    system = m.content
                else:
                    msg_list.append({"role": m.role, "content": m.content})

            t0 = time.time()
            resp = client.messages.create(
                model=self.model,
                system=system or anthropic.NOT_GIVEN,
                messages=msg_list,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency = (time.time() - t0) * 1000
            return CompletionResult(
                content=resp.content[0].text,
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                model=self.model,
                latency_ms=latency,
                provider="anthropic",
            )
        except Exception as e:
            return CompletionResult(content="", error=str(e), provider="anthropic")

    def _http_fallback(self, messages, temperature, max_tokens) -> CompletionResult:
        try:
            system = ""
            msg_list = []
            for m in messages:
                if m.role == "system":
                    system = m.content
                else:
                    msg_list.append({"role": m.role, "content": m.content})
            payload = {
                "model": self.model,
                "system": system,
                "messages": msg_list,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            t0 = time.time()
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                json=payload, headers=headers, timeout=60
            )
            latency = (time.time() - t0) * 1000
            r.raise_for_status()
            data = r.json()
            return CompletionResult(
                content=data["content"][0]["text"],
                input_tokens=data["usage"]["input_tokens"],
                output_tokens=data["usage"]["output_tokens"],
                model=self.model,
                latency_ms=latency,
                provider="anthropic",
            )
        except Exception as e:
            return CompletionResult(content="", error=str(e), provider="anthropic")

    def test_connection(self) -> bool:
        try:
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
            r = requests.get("https://api.anthropic.com/v1/models", headers=headers, timeout=10)
            return r.status_code in (200, 404)  # 404 → endpoint exists but no model list
        except Exception:
            return False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        in_p, out_p = self.PRICE_PER_1K.get(self.model, (0.003, 0.015))
        return (input_tokens * in_p + output_tokens * out_p) / 1000.0


# ── DeepSeek ──────────────────────────────────────────────────────────────────

class DeepSeekClient(BaseAPIClient):
    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str = "", model: str = "deepseek-chat", **kwargs: Any) -> None:
        super().__init__(api_key, model, **kwargs)

    def chat_completion(self, messages, temperature=0.7, max_tokens=2048) -> CompletionResult:
        try:
            payload = {
                "model": self.model,
                "messages": self._make_openai_messages(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            t0 = time.time()
            r = requests.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload, headers=headers, timeout=60
            )
            latency = (time.time() - t0) * 1000
            r.raise_for_status()
            data = r.json()
            return CompletionResult(
                content=data["choices"][0]["message"]["content"],
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                model=self.model,
                latency_ms=latency,
                provider="deepseek",
            )
        except Exception as e:
            return CompletionResult(content="", error=str(e), provider="deepseek")

    def test_connection(self) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            r = requests.get(f"{self.BASE_URL}/models", headers=headers, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * 0.00014 + output_tokens * 0.00028) / 1000.0


# ── Qwen (DashScope) ─────────────────────────────────────────────────────────

class QwenClient(BaseAPIClient):
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, api_key: str = "", model: str = "qwen-plus", **kwargs: Any) -> None:
        super().__init__(api_key, model, **kwargs)

    def chat_completion(self, messages, temperature=0.7, max_tokens=2048) -> CompletionResult:
        try:
            payload = {
                "model": self.model,
                "messages": self._make_openai_messages(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            t0 = time.time()
            r = requests.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload, headers=headers, timeout=60
            )
            latency = (time.time() - t0) * 1000
            r.raise_for_status()
            data = r.json()
            return CompletionResult(
                content=data["choices"][0]["message"]["content"],
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                model=self.model,
                latency_ms=latency,
                provider="qwen",
            )
        except Exception as e:
            return CompletionResult(content="", error=str(e), provider="qwen")

    def test_connection(self) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            r = requests.get(f"{self.BASE_URL}/models", headers=headers, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * 0.0004 + output_tokens * 0.0012) / 1000.0


# ── Ollama (local) ────────────────────────────────────────────────────────────

class OllamaClient(BaseAPIClient):
    def __init__(self, api_key: str = "", model: str = "llama3:70b",
                 base_url: str = "http://localhost:11434", **kwargs: Any) -> None:
        super().__init__(api_key, model, **kwargs)
        self.base_url = base_url.rstrip("/")

    def chat_completion(self, messages, temperature=0.7, max_tokens=2048) -> CompletionResult:
        try:
            payload = {
                "model": self.model,
                "messages": self._make_openai_messages(messages),
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            }
            t0 = time.time()
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload, timeout=120
            )
            latency = (time.time() - t0) * 1000
            r.raise_for_status()
            data = r.json()
            content = data.get("message", {}).get("content", "")
            return CompletionResult(
                content=content,
                model=self.model,
                latency_ms=latency,
                provider="ollama",
            )
        except Exception as e:
            return CompletionResult(content="", error=str(e), provider="ollama")

    def test_connection(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0  # local, free


# ── Azure OpenAI ──────────────────────────────────────────────────────────────

class AzureOpenAIClient(BaseAPIClient):
    def __init__(self, api_key: str = "", model: str = "gpt-4o",
                 endpoint: str = "", api_version: str = "2024-02-15-preview",
                 **kwargs: Any) -> None:
        super().__init__(api_key, model, **kwargs)
        self.endpoint = endpoint.rstrip("/")
        self.api_version = api_version

    def chat_completion(self, messages, temperature=0.7, max_tokens=2048) -> CompletionResult:
        try:
            url = (f"{self.endpoint}/openai/deployments/{self.model}"
                   f"/chat/completions?api-version={self.api_version}")
            payload = {
                "messages": self._make_openai_messages(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json",
            }
            t0 = time.time()
            r = requests.post(url, json=payload, headers=headers, timeout=60)
            latency = (time.time() - t0) * 1000
            r.raise_for_status()
            data = r.json()
            return CompletionResult(
                content=data["choices"][0]["message"]["content"],
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                model=self.model,
                latency_ms=latency,
                provider="azure",
            )
        except Exception as e:
            return CompletionResult(content="", error=str(e), provider="azure")

    def test_connection(self) -> bool:
        try:
            url = f"{self.endpoint}/openai/deployments?api-version={self.api_version}"
            r = requests.get(url, headers={"api-key": self.api_key}, timeout=10)
            return r.status_code in (200, 403)
        except Exception:
            return False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * 0.005 + output_tokens * 0.015) / 1000.0


# ── Mock client ───────────────────────────────────────────────────────────────

MOCK_DEBATE_RESPONSES = {
    "proposer": (
        "Based on the physiological signal features I observe — "
        "regular RR interval variability of 42 ms, narrow QRS complex (82 ms), "
        "and positive P-wave morphology in lead II — I propose the primary rhythm "
        "is **Sinus Rhythm** with confidence 0.91. The heart rate of 68 bpm falls "
        "within normal sinus range (60-100 bpm). Signal Quality Index: 0.87 (good)."
    ),
    "checker": (
        "Cross-validating against PPG-derived features: SpO₂ stable at 98%, "
        "photoplethysmography waveform shows consistent dicrotic notch at ~200 ms "
        "post-systole. Temporal alignment between ECG R-peaks and PPG systolic peaks "
        "confirms sinus rhythm hypothesis. No ectopic beats detected in 30-second window. "
        "Agreement: HIGH. Checker confidence: 0.89."
    ),
    "skeptic": (
        "I challenge the high confidence claim. Three concerns: "
        "(1) Beats 14-17 show subtle PR prolongation (>200 ms) — possible first-degree AV block. "
        "(2) The SQI dips to 0.61 at t=18s due to motion artifact; features derived from "
        "this segment are unreliable. "
        "(3) The proposed sinus rhythm label conflates 'structurally sinus' with 'physiologically normal'. "
        "I recommend flagging for cardiologist review. Revised confidence ceiling: 0.78."
    ),
    "advocate": (
        "Addressing the Skeptic's challenges: "
        "(1) PR prolongation is borderline (208 ms) and within measurement uncertainty given 125 Hz sampling. "
        "(2) The SQI-contaminated segment represents only 12% of the recording; core classification "
        "uses SQI-gated features exclusively. "
        "(3) The sinus rhythm label is clinically standard — first-degree AVB, if present, "
        "is a separate finding and does not invalidate the primary rhythm classification. "
        "Advocate confidence: 0.86."
    ),
    "arbiter": (
        "After weighing Proposer, Checker, Skeptic, and Advocate arguments:\n"
        "**Final Verdict: Sinus Rhythm** — Confidence 0.84 (CI: 0.79–0.89)\n"
        "Review Flag: YES (τ_rev threshold exceeded due to Skeptic-raised PR prolongation concern)\n"
        "Recommendation: Automated classification suitable for screening; "
        "cardiologist review advised for PR prolongation artifact vs. first-degree AV block distinction.\n"
        "ECE: 0.071 (well-calibrated). Macro-F1 estimate: 0.88."
    ),
}


class MockAPIClient(BaseAPIClient):
    """Deterministic mock for testing/demo without real API keys."""
    ROLES = ["proposer", "checker", "skeptic", "advocate", "arbiter"]

    def __init__(self, api_key: str = "", model: str = "mock-v1", **kwargs: Any) -> None:
        super().__init__(api_key, model, **kwargs)
        self._call_count = 0

    def chat_completion(self, messages, temperature=0.7, max_tokens=2048) -> CompletionResult:
        import time as _time
        _time.sleep(0.4)  # simulate latency
        role = self.ROLES[self._call_count % len(self.ROLES)]
        self._call_count += 1
        content = MOCK_DEBATE_RESPONSES[role]
        input_tok = sum(len(m.content.split()) * 1.3 for m in messages)
        output_tok = len(content.split()) * 1.3
        return CompletionResult(
            content=content,
            input_tokens=int(input_tok),
            output_tokens=int(output_tok),
            model=self.model,
            latency_ms=400.0,
            provider="mock",
        )

    def test_connection(self) -> bool:
        return True

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0


# ── Factory ───────────────────────────────────────────────────────────────────

class APIClientFactory:
    """Create provider clients by name."""

    PROVIDER_MAP = {
        "openai": OpenAIClient,
        "gpt-5.2": OpenAIClient,
        "gpt-5": OpenAIClient,
        "gpt-4o": OpenAIClient,
        "anthropic": AnthropicClient,
        "claude": AnthropicClient,
        "claude-3.7": AnthropicClient,
        "deepseek": DeepSeekClient,
        "qwen": QwenClient,
        "ollama": OllamaClient,
        "azure": AzureOpenAIClient,
        "mock": MockAPIClient,
    }

    MODEL_DEFAULTS = {
        "GPT-5.2": ("openai", "gpt-5.2-preview"),
        "GPT-5": ("openai", "gpt-5-preview"),
        "GPT-4o": ("openai", "gpt-4o"),
        "DeepSeek-V3.2": ("deepseek", "deepseek-chat"),
        "Qwen3.5-27B": ("qwen", "qwen3.5-27b"),
        "Llama-3-70B": ("ollama", "llama3:70b"),
        "Claude-3.7": ("anthropic", "claude-3-7-sonnet-20250219"),
        "Mock / Demo": ("mock", "mock-v1"),
    }

    @classmethod
    def create(
        cls,
        provider_or_display_name: str,
        api_key: str = "",
        model: str = "",
        **kwargs: Any,
    ) -> BaseAPIClient:
        key = provider_or_display_name.lower()

        # check display-name map first
        if provider_or_display_name in cls.MODEL_DEFAULTS:
            provider, default_model = cls.MODEL_DEFAULTS[provider_or_display_name]
            m = model or default_model
            cls_type = cls.PROVIDER_MAP.get(provider, MockAPIClient)
            return cls_type(api_key=api_key, model=m, **kwargs)

        # fuzzy match
        for k, cls_type in cls.PROVIDER_MAP.items():
            if k in key:
                m = model or k
                return cls_type(api_key=api_key, model=m, **kwargs)

        return MockAPIClient(api_key=api_key, model="mock-v1")

    @classmethod
    def list_display_names(cls) -> List[str]:
        return list(cls.MODEL_DEFAULTS.keys())
