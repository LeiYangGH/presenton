from fastapi import HTTPException

from constants.llm import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_GOOGLE_MODEL,
    DEFAULT_OPENAI_MODEL,
)
from enums.llm_provider import LLMProvider
from utils.get_env import (
    get_anthropic_model_env,
    get_codex_model_env,
    get_custom_model_env,
    get_google_model_env,
    get_llm_provider_env,
    get_ollama_model_env,
    get_openai_model_env,
)


def get_llm_provider():
    try:
        provider = get_llm_provider_env()
        # 如果未设置，默认为 LOCAL_LLAMA (llama.server at 8989)
        if not provider:
            return LLMProvider.LOCAL_LLAMA
        return LLMProvider(provider)
    except:
        return LLMProvider.LOCAL_LLAMA


def is_local_llama_selected():
    return get_llm_provider() == LLMProvider.LOCAL_LLAMA


def is_openai_selected():
    return get_llm_provider() == LLMProvider.OPENAI


def is_google_selected():
    return get_llm_provider() == LLMProvider.GOOGLE


def is_anthropic_selected():
    return get_llm_provider() == LLMProvider.ANTHROPIC


def is_custom_llm_selected():
    return get_llm_provider() == LLMProvider.CUSTOM


def is_codex_selected():
    return get_llm_provider() == LLMProvider.CODEX


def get_model():
    selected_llm = get_llm_provider()
    if selected_llm == LLMProvider.LOCAL_LLAMA:
        return "local-model"  # 默认模型名
    elif selected_llm == LLMProvider.OPENAI:
        return get_openai_model_env() or DEFAULT_OPENAI_MODEL
    elif selected_llm == LLMProvider.GOOGLE:
        return get_google_model_env() or DEFAULT_GOOGLE_MODEL
    elif selected_llm == LLMProvider.ANTHROPIC:
        return get_anthropic_model_env() or DEFAULT_ANTHROPIC_MODEL
    elif selected_llm == LLMProvider.CUSTOM:
        return get_custom_model_env()
    elif selected_llm == LLMProvider.CODEX:
        return get_codex_model_env()
    else:
        return "local-model"
