from fastapi import HTTPException

from constants.llm import (
    DEFAULT_OPENAI_MODEL,
)
from enums.llm_provider import LLMProvider
from utils.get_env import (
    get_custom_model_env,
    get_llm_provider_env,
    get_openai_model_env,
)


def get_llm_provider():
    try:
        provider = get_llm_provider_env()
        # Default to CUSTOM (which points to local 8989 by default)
        if not provider:
            return LLMProvider.CUSTOM
        return LLMProvider(provider)
    except:
        return LLMProvider.CUSTOM


def is_openai_selected():
    return get_llm_provider() == LLMProvider.OPENAI


def is_custom_llm_selected():
    return get_llm_provider() == LLMProvider.CUSTOM


def get_model():
    selected_llm = get_llm_provider()
    if selected_llm == LLMProvider.OPENAI:
        return get_openai_model_env() or DEFAULT_OPENAI_MODEL
    elif selected_llm == LLMProvider.CUSTOM:
        return get_custom_model_env() or "local-model"
    else:
        return "local-model"
