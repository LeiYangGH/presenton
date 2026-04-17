from openai import AsyncOpenAI


async def list_available_openai_compatible_models(url: str, api_key: str) -> list[str]:
    client = AsyncOpenAI(api_key=api_key, base_url=url)
    models = (await client.models.list()).data
    if models:
        return list(map(lambda x: x.id, models))
    return []
