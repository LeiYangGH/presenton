from fastapi import HTTPException
from openai import APIError as OpenAIAPIError
import traceback


def handle_llm_client_exceptions(e: Exception) -> HTTPException:
    traceback.print_exc()
    if isinstance(e, OpenAIAPIError):
        return HTTPException(status_code=500, detail=f"OpenAI API error: {e.message}")
    return HTTPException(status_code=500, detail=f"LLM API error: {e}")
