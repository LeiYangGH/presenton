from typing import List, Literal, Optional
from pydantic import BaseModel


class LLMMessage(BaseModel):
    pass


class LLMUserMessage(LLMMessage):
    role: Literal["user"] = "user"
    content: str


class LLMSystemMessage(LLMMessage):
    role: Literal["system"] = "system"
    content: str


class OpenAIAssistantMessage(LLMMessage):
    role: Literal["assistant"] = "assistant"
    content: str | None = None
    tool_calls: Optional[List[dict]] = None


class OpenAIToolCallMessage(LLMMessage):
    role: Literal["tool"] = "tool"
    content: str
    tool_call_id: str
