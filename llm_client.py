"""Simple, dependency-light LLM client entrance for RAVEL / C3EBench.

Goal: let the pipeline reach any model through the official **OpenAI** and
**Anthropic** SDKs, configured by environment variables, so that the internal
`glm_api_request` package is NOT a required dependency.

Endpoint + key resolution (first match wins):

  OpenAI-compatible models
    base_url : $RAVEL_OPENAI_BASE_URL -> $OPENAI_BASE_URL -> GLM gateway default
    api_key  : $RAVEL_API_KEY -> $OPENAI_API_KEY -> glm_api_request key (if present)
  Anthropic (claude* / anthropic:*) models
    base_url : $RAVEL_ANTHROPIC_BASE_URL -> $ANTHROPIC_BASE_URL -> GLM gateway default
    api_key  : $RAVEL_API_KEY -> $ANTHROPIC_API_KEY -> glm_api_request key (if present)

With env vars set, `glm_api_request` is never imported. With NOTHING set, the
defaults reproduce the released GLM-gateway behaviour exactly (same URL + key),
so existing runs are unchanged.

`make_client(model_name)` routes by name and returns a client exposing the same
`get_api_result(messages, tools, temperature, max_completion_tokens)` interface as
the legacy `glm_api_request.model.GateWays` (result has `.choices[0].message.content`),
so callers do not change:

    claude* / anthropic:*  -> AnthropicClient        (Anthropic Messages API)
    openrouter:*           -> StreamingOpenAIClient   (OpenAI SDK, stream=True)
    otherwise              -> OpenAIClient            (OpenAI SDK, chat.completions)
"""
import os
from types import SimpleNamespace

# GLM gateway defaults (used only when no env override is provided).
_GLM_OPENAI_BASE_URL = "https://api-gateway.glm.ai/v1"
_GLM_ANTHROPIC_BASE_URL = "https://api-gateway.glm.ai"


def _first_env(*names):
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None


def _glm_fallback_key():
    """Optionally read the legacy gateway key from glm_api_request, if installed.
    Instantiating GateWays does not make a network call. Returns None if absent."""
    try:
        from glm_api_request.model import GateWays
        return GateWays("_probe").api_key
    except Exception:
        return None


def _resolve_key(explicit=None, provider="openai"):
    key = explicit or _first_env(
        "RAVEL_API_KEY",
        "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY",
    )
    if key:
        return key
    key = _glm_fallback_key()
    if key:
        return key
    raise RuntimeError(
        "No API key found. Set RAVEL_API_KEY (or OPENAI_API_KEY / ANTHROPIC_API_KEY), "
        "or install glm_api_request. See ravel_bench/README.md."
    )


def _openai_base_url(explicit=None):
    return explicit or _first_env("RAVEL_OPENAI_BASE_URL", "OPENAI_BASE_URL") or _GLM_OPENAI_BASE_URL


def _anthropic_base_url(explicit=None):
    return explicit or _first_env("RAVEL_ANTHROPIC_BASE_URL", "ANTHROPIC_BASE_URL") or _GLM_ANTHROPIC_BASE_URL


class LLMBaseClient:
    """Marker/duck base so callers can type-hint the client uniformly."""
    model = None


class OpenAIClient(LLMBaseClient):
    """OpenAI-SDK chat client. GateWays-compatible."""

    def __init__(self, model_name, base_url=None, api_key=None):
        from openai import OpenAI
        self.model = model_name
        self.api_url = _openai_base_url(base_url)
        self.api_key = _resolve_key(api_key, "openai")
        self.client = OpenAI(base_url=self.api_url, api_key=self.api_key)

    def get_api_result(self, messages, tools=None, temperature=1.0, max_completion_tokens=5000):
        return self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools,
            max_completion_tokens=max_completion_tokens, temperature=temperature,
            timeout=120,
        )


class StreamingOpenAIClient(OpenAIClient):
    """OpenAI-SDK client for channels that require stream=True (e.g. openrouter:*).
    Accumulates the stream and returns the non-streaming response shape."""

    def get_api_result(self, messages, tools=None, temperature=1.0, max_completion_tokens=5000):
        stream = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools,
            max_completion_tokens=max_completion_tokens, temperature=temperature,
            timeout=120, stream=True,
        )
        parts = []
        for ev in stream:
            if ev.choices and ev.choices[0].delta and ev.choices[0].delta.content:
                parts.append(ev.choices[0].delta.content)
        text = "".join(parts)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


class AnthropicClient(LLMBaseClient):
    """Anthropic-SDK client. Splits the system prompt into Anthropic's `system=`
    param and shims the response to the OpenAI `.choices[0].message.content` shape."""

    def __init__(self, model_name, base_url=None, api_key=None):
        import anthropic
        self.model = model_name
        self.api_url = _anthropic_base_url(base_url)
        self.api_key = _resolve_key(api_key, "anthropic")
        self.client = anthropic.Anthropic(base_url=self.api_url, api_key=self.api_key)

    def get_api_result(self, messages, tools=None, temperature=1.0, max_completion_tokens=1000):
        system_parts, conv = [], []
        for m in messages:
            if m.get("role") == "system":
                system_parts.append(m.get("content", ""))
            else:
                conv.append({"role": m["role"], "content": m["content"]})
        kwargs = dict(model=self.model, max_tokens=max_completion_tokens,
                      temperature=temperature, messages=conv)
        if system_parts:
            kwargs["system"] = "\n".join(system_parts)
        resp = self.client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def needs_streaming(model_name) -> bool:
    return str(model_name).startswith("openrouter:")


def is_anthropic(model_name) -> bool:
    n = str(model_name).lower()
    return n.startswith("claude") or n.startswith("anthropic:")


def make_client(model_name, base_url=None, api_key=None):
    """Return the right SDK client for a model name (see module docstring)."""
    if is_anthropic(model_name):
        mid = str(model_name).split("anthropic:", 1)[-1]
        return AnthropicClient(mid, base_url=base_url, api_key=api_key)
    if needs_streaming(model_name):
        return StreamingOpenAIClient(model_name, base_url=base_url, api_key=api_key)
    return OpenAIClient(model_name, base_url=base_url, api_key=api_key)
