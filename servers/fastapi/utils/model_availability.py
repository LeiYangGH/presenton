from constants.llm import OPENAI_URL
from enums.image_provider import ImageProvider
from enums.llm_provider import LLMProvider
from utils.available_models import (
    list_available_openai_compatible_models,
)
from utils.get_env import (
    get_can_change_keys_env,
    get_openai_api_key_env,
    get_openai_model_env,
    get_pixabay_api_key_env,
    get_pexels_api_key_env,
    get_comfyui_url_env,
    get_comfyui_workflow_env,
)
from utils.get_env import get_custom_llm_api_key_env
from utils.get_env import get_custom_llm_url_env
from utils.get_env import get_custom_model_env
from utils.llm_provider import (
    get_llm_provider,
    is_custom_llm_selected,
)
from utils.image_provider import (
    get_selected_image_provider,
    is_image_generation_disabled,
)


async def check_llm_and_image_provider_api_or_model_availability():
    can_change_keys = get_can_change_keys_env() != "false"
    if not can_change_keys:
        if get_llm_provider() == LLMProvider.OPENAI:
            openai_api_key = get_openai_api_key_env()
            if not openai_api_key:
                raise Exception("OPENAI_API_KEY must be provided")
            openai_model = get_openai_model_env()
            if openai_model:
                available_models = await list_available_openai_compatible_models(
                    OPENAI_URL, openai_api_key
                )
                if openai_model not in available_models:
                    print("-" * 50)
                    print("Available models: ", available_models)
                    raise Exception(f"Model {openai_model} is not available")

        elif is_custom_llm_selected():
            custom_model = get_custom_model_env()
            custom_llm_url = get_custom_llm_url_env()
            # If no model/url provided, we skip check (defaults to local 8989)
            if custom_model and custom_llm_url:
                available_models = await list_available_openai_compatible_models(
                    custom_llm_url, get_custom_llm_api_key_env() or "null"
                )
                print("-" * 50)
                print("Available models: ", available_models)
                if custom_model not in available_models:
                    raise Exception(f"Model {custom_model} is not available")

        # Skip image provider and API key checks if image generation is disabled
        if is_image_generation_disabled():
            return

        # Check for Image Provider and API keys
        selected_image_provider = get_selected_image_provider()
        if not selected_image_provider:
            raise Exception("IMAGE_PROVIDER must be provided")

        if selected_image_provider == ImageProvider.PEXELS:
            pexels_api_key = get_pexels_api_key_env()
            if not pexels_api_key:
                raise Exception("PEXELS_API_KEY must be provided")

        elif selected_image_provider == ImageProvider.PIXABAY:
            pixabay_api_key = get_pixabay_api_key_env()
            if not pixabay_api_key:
                raise Exception("PIXABAY_API_KEY must be provided")

        elif (
            selected_image_provider == ImageProvider.DALLE3
            or selected_image_provider == ImageProvider.GPT_IMAGE_1_5
        ):
            openai_api_key = get_openai_api_key_env()
            if not openai_api_key:
                raise Exception("OPENAI_API_KEY must be provided")

        elif selected_image_provider == ImageProvider.COMFYUI:
            comfyui_url = get_comfyui_url_env()
            if not comfyui_url:
                raise Exception("COMFYUI_URL must be provided")
            workflow_json = get_comfyui_workflow_env()
            if not workflow_json:
                raise Exception("COMFYUI_WORKFLOW must be provided")
