from enum import Enum


class LLMProvider(Enum):
    LOCAL_LLAMA = "local_llama"
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"
    CODEX = "codex"
