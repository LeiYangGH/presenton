import asyncio
import dirtyjson
import json
from typing import AsyncGenerator, List, Optional, Dict, Any
from fastapi import HTTPException
from openai import APIStatusError, AsyncOpenAI, OpenAIError
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk as OpenAIChatCompletionChunk,
)
from enums.llm_provider import LLMProvider
from models.llm_message import (
    OpenAIAssistantMessage,
    LLMMessage,
    LLMSystemMessage,
    LLMUserMessage,
)
from models.llm_tool_call import (
    LLMToolCall,
    OpenAIToolCall,
    OpenAIToolCallFunction,
)
from models.llm_tools import LLMDynamicTool, LLMTool
from services.llm_tool_calls_handler import LLMToolCallsHandler
from utils.async_iterator import iterator_to_async
from utils.dummy_functions import do_nothing_async
from utils.get_env import (
    get_custom_llm_api_key_env,
    get_custom_llm_url_env,
    get_disable_thinking_env,
    get_openai_api_key_env,
    get_tool_calls_env,
)
from utils.llm_provider import get_llm_provider, get_model
from utils.parsers import parse_bool_or_none
from utils.schema_utils import (
    ensure_array_schemas_have_items,
    ensure_strict_json_schema,
)


class LLMClient:
    def __init__(self):
        self.llm_provider = get_llm_provider()
        self._client = self._get_client()
        self.tool_calls_handler = LLMToolCallsHandler(self)

    # ? Use tool calls
    def use_tool_calls_for_structured_output(self) -> bool:
        if self.llm_provider != LLMProvider.CUSTOM:
            return False
        return parse_bool_or_none(get_tool_calls_env()) or False

    # ? Disable thinking
    def disable_thinking(self) -> bool:
        return parse_bool_or_none(get_disable_thinking_env()) or False

    # ? Clients
    def _get_client(self):
        match self.llm_provider:
            case LLMProvider.OPENAI:
                return self._get_openai_client()
            case LLMProvider.CUSTOM:
                return self._get_custom_client()
            case _:
                return self._get_openai_client()

    def _get_openai_client(self):
        return AsyncOpenAI(
            api_key=get_openai_api_key_env() or "null",
        )

    def _get_custom_client(self):
        url = get_custom_llm_url_env()
        if not url:
            # Fallback to local llama if CUSTOM is selected but no URL provided
            url = "http://127.0.0.1:8989/v1"
            
        return AsyncOpenAI(
            base_url=url,
            api_key=get_custom_llm_api_key_env() or "null",
        )

    # ? Prompts
    def _get_system_prompt(self, messages: List[LLMMessage]) -> str:
        for message in messages:
            if isinstance(message, LLMSystemMessage):
                return message.content
        return ""

    # ? Generate Unstructured Content
    async def _generate_openai(
        self,
        model: str,
        messages: List[LLMMessage],
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        extra_body: Optional[dict] = None,
        depth: int = 0,
    ) -> str | None:
        client: AsyncOpenAI = self._client
        response = await client.chat.completions.create(
            model=model,
            messages=[message.model_dump() for message in messages],
            max_completion_tokens=max_tokens,
            tools=tools,
            extra_body=extra_body,
        )

        if len(response.choices) == 0:
            return None

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            parsed_tool_calls = [
                OpenAIToolCall(
                    id=tool_call.id,
                    type=tool_call.type,
                    function=OpenAIToolCallFunction(
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                    ),
                )
                for tool_call in tool_calls
            ]
            tool_call_messages = await self.tool_calls_handler.handle_tool_calls_openai(
                parsed_tool_calls
            )
            assistant_message = OpenAIAssistantMessage(
                role="assistant",
                content=response.choices[0].message.content,
                tool_calls=[tool_call.model_dump() for tool_call in parsed_tool_calls],
            )
            new_messages = [
                *messages,
                assistant_message,
                *tool_call_messages,
            ]
            return await self._generate_openai(
                model=model,
                messages=new_messages,
                max_tokens=max_tokens,
                tools=tools,
                extra_body=extra_body,
                depth=depth + 1,
            )

        return response.choices[0].message.content

    async def generate(
        self,
        model: str,
        messages: List[LLMMessage],
        max_tokens: Optional[int] = None,
        tools: Optional[List[type[LLMTool] | LLMDynamicTool]] = None,
    ):
        parsed_tools = self.tool_calls_handler.parse_tools(tools)

        content = None
        match self.llm_provider:
            case LLMProvider.OPENAI:
                content = await self._generate_openai(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    tools=parsed_tools,
                )
            case LLMProvider.CUSTOM:
                extra_body = {"enable_thinking": False} if self.disable_thinking() else None
                content = await self._generate_openai(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    tools=parsed_tools,
                    extra_body=extra_body,
                )
        if content is None:
            raise HTTPException(
                status_code=400,
                detail="LLM did not return any content",
            )
        return content

    # ? Generate Structured Content
    async def _generate_openai_structured(
        self,
        model: str,
        messages: List[LLMMessage],
        response_format: dict,
        strict: bool = False,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        extra_body: Optional[dict] = None,
        depth: int = 0,
    ) -> dict | None:
        client: AsyncOpenAI = self._client
        response_schema = response_format
        all_tools = [*tools] if tools else None

        use_tool_calls_for_structured_output = (
            self.use_tool_calls_for_structured_output()
        )
        if strict and depth == 0:
            response_schema = ensure_strict_json_schema(
                response_schema,
                path=(),
                root=response_schema,
            )
        response_schema = ensure_array_schemas_have_items(response_schema)
        if use_tool_calls_for_structured_output and depth == 0:
            if all_tools is None:
                all_tools = []
            all_tools.append(
                self.tool_calls_handler.parse_tool(
                    LLMDynamicTool(
                        name="ResponseSchema",
                        description="Provide response to the user",
                        parameters=response_schema,
                        handler=do_nothing_async,
                    ),
                    strict=strict,
                )
            )

        response = await client.chat.completions.create(
            model=model,
            messages=[message.model_dump() for message in messages],
            response_format=(
                {
                    "type": "json_schema",
                    "json_schema": (
                        {
                            "name": "ResponseSchema",
                            "strict": strict,
                            "schema": response_schema,
                        }
                    ),
                }
                if not use_tool_calls_for_structured_output
                else None
            ),
            max_completion_tokens=max_tokens,
            tools=all_tools,
            extra_body=extra_body,
        )

        if len(response.choices) == 0:
            return None

        content = response.choices[0].message.content

        tool_calls = response.choices[0].message.tool_calls
        has_response_schema = False

        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name == "ResponseSchema":
                    content = tool_call.function.arguments
                    has_response_schema = True

            if not has_response_schema:
                parsed_tool_calls = [
                    OpenAIToolCall(
                        id=tool_call.id,
                        type=tool_call.type,
                        function=OpenAIToolCallFunction(
                            name=tool_call.function.name,
                            arguments=tool_call.function.arguments,
                        ),
                    )
                    for tool_call in tool_calls
                ]
                tool_call_messages = (
                    await self.tool_calls_handler.handle_tool_calls_openai(
                        parsed_tool_calls
                    )
                )
                new_messages = [
                    *messages,
                    OpenAIAssistantMessage(
                        role="assistant",
                        content=response.choices[0].message.content,
                        tool_calls=[each.model_dump() for each in parsed_tool_calls],
                    ),
                    *tool_call_messages,
                ]
                content = await self._generate_openai_structured(
                    model=model,
                    messages=new_messages,
                    response_format=response_schema,
                    strict=strict,
                    max_tokens=max_tokens,
                    tools=all_tools,
                    extra_body=extra_body,
                    depth=depth + 1,
                )
        if content:
            if depth == 0:
                return dict(dirtyjson.loads(content))
            return content
        return None

    async def generate_structured(
        self,
        model: str,
        messages: List[LLMMessage],
        response_format: dict,
        strict: bool = False,
        tools: Optional[List[type[LLMTool] | LLMDynamicTool]] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        parsed_tools = self.tool_calls_handler.parse_tools(tools)

        for attempt in range(3):
            content = None
            match self.llm_provider:
                case LLMProvider.OPENAI:
                    content = await self._generate_openai_structured(
                        model=model,
                        messages=messages,
                        response_format=response_format,
                        strict=strict,
                        tools=parsed_tools,
                        max_tokens=max_tokens,
                    )
                case LLMProvider.CUSTOM:
                    extra_body = {"enable_thinking": False} if self.disable_thinking() else None
                    content = await self._generate_openai_structured(
                        model=model,
                        messages=messages,
                        response_format=response_format,
                        strict=strict,
                        tools=parsed_tools,
                        max_tokens=max_tokens,
                        extra_body=extra_body,
                    )

            if content is not None:
                return content

            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))

        raise HTTPException(
            status_code=400,
            detail="LLM did not return any content",
        )

    # ? Stream Unstructured Content
    async def _stream_openai(
        self,
        model: str,
        messages: List[LLMMessage],
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        extra_body: Optional[dict] = None,
        depth: int = 0,
    ) -> AsyncGenerator[str, None]:
        client: AsyncOpenAI = self._client

        tool_calls: List[LLMToolCall] = []
        current_index = 0
        current_id = None
        current_name = None
        current_arguments = None
        async for event in await client.chat.completions.create(
            model=model,
            messages=[message.model_dump() for message in messages],
            max_completion_tokens=max_tokens,
            tools=tools,
            extra_body=extra_body,
            stream=True,
        ):
            event: OpenAIChatCompletionChunk = event
            if not event.choices:
                continue

            content_chunk = event.choices[0].delta.content
            if content_chunk:
                yield content_chunk

            tool_call_chunk = event.choices[0].delta.tool_calls
            if tool_call_chunk:
                tool_index = tool_call_chunk[0].index
                tool_id = tool_call_chunk[0].id
                tool_name = tool_call_chunk[0].function.name
                tool_arguments = tool_call_chunk[0].function.arguments

                if current_index != tool_index:
                    tool_calls.append(
                        OpenAIToolCall(
                            id=current_id,
                            type="function",
                            function=OpenAIToolCallFunction(
                                name=current_name,
                                arguments=current_arguments,
                            ),
                        )
                    )
                    current_index = tool_index
                    current_id = tool_id
                    current_name = tool_name
                    current_arguments = tool_arguments
                else:
                    current_name = tool_name or current_name
                    current_id = tool_id or current_id
                    if current_arguments is None:
                        current_arguments = tool_arguments
                    elif tool_arguments:
                        current_arguments += tool_arguments

        if current_id is not None:
            tool_calls.append(
                OpenAIToolCall(
                    id=current_id,
                    type="function",
                    function=OpenAIToolCallFunction(
                        name=current_name,
                        arguments=current_arguments,
                    ),
                )
            )

        if tool_calls:
            tool_call_messages = await self.tool_calls_handler.handle_tool_calls_openai(
                tool_calls
            )
            new_messages = [
                *messages,
                OpenAIAssistantMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[each.model_dump() for each in tool_calls],
                ),
                *tool_call_messages,
            ]
            async for event in self._stream_openai(
                model=model,
                messages=new_messages,
                max_tokens=max_tokens,
                tools=tools,
                extra_body=extra_body,
                depth=depth + 1,
            ):
                yield event

    def stream(
        self,
        model: str,
        messages: List[LLMMessage],
        max_tokens: Optional[int] = None,
        tools: Optional[List[type[LLMTool] | LLMDynamicTool]] = None,
    ):
        parsed_tools = self.tool_calls_handler.parse_tools(tools)

        match self.llm_provider:
            case LLMProvider.OPENAI:
                return self._stream_openai(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    tools=parsed_tools,
                )
            case LLMProvider.CUSTOM:
                extra_body = {"enable_thinking": False} if self.disable_thinking() else None
                return self._stream_openai(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    tools=parsed_tools,
                    extra_body=extra_body,
                )

    # ? Stream Structured Content
    async def _stream_openai_structured(
        self,
        model: str,
        messages: List[LLMMessage],
        response_format: dict,
        strict: bool = False,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        extra_body: Optional[dict] = None,
        depth: int = 0,
    ) -> AsyncGenerator[str, None]:
        client: AsyncOpenAI = self._client

        response_schema = response_format
        all_tools = [*tools] if tools else None

        use_tool_calls_for_structured_output = (
            self.use_tool_calls_for_structured_output()
        )
        if strict and depth == 0:
            response_schema = ensure_strict_json_schema(
                response_schema,
                path=(),
                root=response_schema,
            )
        response_schema = ensure_array_schemas_have_items(response_schema)

        if use_tool_calls_for_structured_output and depth == 0:
            if all_tools is None:
                all_tools = []
            all_tools.append(
                self.tool_calls_handler.parse_tool(
                    LLMDynamicTool(
                        name="ResponseSchema",
                        description="Provide response to the user",
                        parameters=response_schema,
                        handler=do_nothing_async,
                    ),
                    strict=strict,
                )
            )

        tool_calls: List[LLMToolCall] = []
        current_index = 0
        current_id = None
        current_name = None
        current_arguments = None

        has_response_schema_tool_call = False
        async for event in await client.chat.completions.create(
            model=model,
            messages=[message.model_dump() for message in messages],
            max_completion_tokens=max_tokens,
            tools=all_tools,
            response_format=(
                {
                    "type": "json_schema",
                    "json_schema": (
                        {
                            "name": "ResponseSchema",
                            "strict": strict,
                            "schema": response_schema,
                        }
                    ),
                }
                if not use_tool_calls_for_structured_output
                else None
            ),
            extra_body=extra_body,
            stream=True,
        ):
            event: OpenAIChatCompletionChunk = event
            if not event.choices:
                continue

            content_chunk = event.choices[0].delta.content
            if content_chunk and not use_tool_calls_for_structured_output:
                yield content_chunk

            tool_call_chunk = event.choices[0].delta.tool_calls
            if tool_call_chunk:
                tool_index = tool_call_chunk[0].index
                tool_id = tool_call_chunk[0].id
                tool_name = tool_call_chunk[0].function.name
                tool_arguments = tool_call_chunk[0].function.arguments

                if current_index != tool_index:
                    tool_calls.append(
                        OpenAIToolCall(
                            id=current_id,
                            type="function",
                            function=OpenAIToolCallFunction(
                                name=current_name,
                                arguments=current_arguments,
                            ),
                        )
                    )
                    current_index = tool_index
                    current_id = tool_id
                    current_name = tool_name
                    current_arguments = tool_arguments
                else:
                    current_name = tool_name or current_name
                    current_id = tool_id or current_id
                    if current_arguments is None:
                        current_arguments = tool_arguments
                    elif tool_arguments:
                        current_arguments += tool_arguments

                if current_name == "ResponseSchema":
                    if tool_arguments:
                        yield tool_arguments
                    has_response_schema_tool_call = True

        if current_id is not None:
            tool_calls.append(
                OpenAIToolCall(
                    id=current_id,
                    type="function",
                    function=OpenAIToolCallFunction(
                        name=current_name,
                        arguments=current_arguments,
                    ),
                )
            )

        if tool_calls and not has_response_schema_tool_call:
            tool_call_messages = await self.tool_calls_handler.handle_tool_calls_openai(
                tool_calls
            )
            new_messages = [
                *messages,
                OpenAIAssistantMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[each.model_dump() for each in tool_calls],
                ),
                *tool_call_messages,
            ]
            async for event in self._stream_openai_structured(
                model=model,
                messages=new_messages,
                max_tokens=max_tokens,
                strict=strict,
                tools=all_tools,
                response_format=response_schema,
                extra_body=extra_body,
                depth=depth + 1,
            ):
                yield event

    def stream_structured(
        self,
        model: str,
        messages: List[LLMMessage],
        response_format: dict,
        strict: bool = False,
        tools: Optional[List[type[LLMTool] | LLMDynamicTool]] = None,
        max_tokens: Optional[int] = None,
    ):
        parsed_tools = self.tool_calls_handler.parse_tools(tools)

        match self.llm_provider:
            case LLMProvider.OPENAI:
                return self._stream_openai_structured(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    strict=strict,
                    tools=parsed_tools,
                    max_tokens=max_tokens,
                )
            case LLMProvider.CUSTOM:
                extra_body = {"enable_thinking": False} if self.disable_thinking() else None
                return self._stream_openai_structured(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    strict=strict,
                    tools=parsed_tools,
                    max_tokens=max_tokens,
                    extra_body=extra_body,
                )
