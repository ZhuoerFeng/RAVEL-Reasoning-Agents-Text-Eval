"""Judge client factory (thin compatibility layer over `llm_client`).

Judge routing now lives in the dependency-light `llm_client.make_client`
(OpenAI / Anthropic SDKs, env-configurable, `glm_api_request` optional). This
module keeps the historical names (`make_judge`, `AnthropicJudge`) so existing
imports/scripts keep working.
"""
from llm_client import make_client, AnthropicClient

# Back-compat alias: earlier code referred to `AnthropicJudge`.
AnthropicJudge = AnthropicClient


def make_judge(model_name):
    """Return the right judge client for a model name.

    claude* / anthropic:* -> Anthropic SDK; openrouter:* -> streaming OpenAI SDK;
    otherwise -> OpenAI SDK. Endpoint/key come from env vars (see llm_client),
    falling back to the GLM gateway defaults so behaviour is unchanged at zero config.
    """
    return make_client(model_name)
