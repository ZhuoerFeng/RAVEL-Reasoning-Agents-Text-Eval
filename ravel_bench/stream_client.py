"""Streaming generation client for gateway channels that reject non-streaming
calls (e.g. the `openrouter:*` route on the GLM gateway returns
400 "stream: Invalid input" unless stream=True).

StreamingGateWays subclasses the released GateWays and overrides get_api_result
to stream and accumulate the content, returning the same response shape
(`.choices[0].message.content`). glm_api_request is not modified.
"""
from types import SimpleNamespace

from glm_api_request.model import GateWays


def needs_streaming(model_name) -> bool:
    """Models whose gateway channel requires stream=True."""
    return str(model_name).startswith("openrouter:")


class StreamingGateWays(GateWays):
    def get_api_result(self, messages, tools=None, temperature=1.0,
                       max_completion_tokens=5000):
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
