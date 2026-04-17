import { LLMConfig } from "@/types/llm_config";

export interface DownloadingModel {
  name: string;
  size: number | null;
  downloaded: number | null;
  status: string;
  done: boolean;
}

/**
 * Updates LLM configuration based on field changes
 */
export const updateLLMConfig = (
  currentConfig: LLMConfig,
  field: string,
  value: string | boolean
): LLMConfig => {
  const fieldMappings: Record<string, keyof LLMConfig> = {
    openai_api_key: "OPENAI_API_KEY",
    openai_model: "OPENAI_MODEL",
    custom_llm_url: "CUSTOM_LLM_URL",
    custom_llm_api_key: "CUSTOM_LLM_API_KEY",
    custom_model: "CUSTOM_MODEL",
    pexels_api_key: "PEXELS_API_KEY",
    pixabay_api_key: "PIXABAY_API_KEY",
    image_provider: "IMAGE_PROVIDER",
    disable_image_generation: "DISABLE_IMAGE_GENERATION",
    tool_calls: "TOOL_CALLS",
    disable_thinking: "DISABLE_THINKING",
    extended_reasoning: "EXTENDED_REASONING",
    web_grounding: "WEB_GROUNDING",
    comfyui_url: "COMFYUI_URL",
    comfyui_workflow: "COMFYUI_WORKFLOW",
    dall_e_3_quality: "DALL_E_3_QUALITY",
    gpt_image_1_5_quality: "GPT_IMAGE_1_5_QUALITY",
    open_webui_image_url: "OPEN_WEBUI_IMAGE_URL",
    open_webui_image_api_key: "OPEN_WEBUI_IMAGE_API_KEY",
  };

  const configKey = fieldMappings[field];
  if (configKey) {
    return { ...currentConfig, [configKey]: value };
  }

  return currentConfig;
};

/**
 * Changes the provider and sets appropriate defaults
 */
export const changeProvider = (
  currentConfig: LLMConfig,
  provider: string
): LLMConfig => {
  const newConfig = { ...currentConfig, LLM: provider };

  // Auto Select appropriate image provider based on the text models
  if (provider === "openai") {
    newConfig.IMAGE_PROVIDER = "gpt-image-1.5";
  } else {
    newConfig.IMAGE_PROVIDER = "pexels"; // default for custom
  }

  return newConfig;
};

/**
 * Resets downloading model state
 */
export const resetDownloadingModel = (): DownloadingModel => ({
  name: "",
  size: null,
  downloaded: null,
  status: "",
  done: false,
});

function abortPullError(): Error {
  const err = new Error("Download cancelled");
  err.name = "AbortError";
  return err;
}

function isAbortError(e: unknown): boolean {
  return e instanceof Error && e.name === "AbortError";
}

/**
 * Pulls model with progress tracking.
 * Pass an AbortSignal to stop polling (e.g. user cancels download).
 */
export const pullModel = async (
  model: string,
  onProgress?: (model: DownloadingModel) => void,
  signal?: AbortSignal
): Promise<DownloadingModel> => {
  return new Promise((resolve, reject) => {
    let interval: ReturnType<typeof setInterval> | null = null;
    let settled = false;

    const cleanup = () => {
      if (interval !== null) {
        clearInterval(interval);
        interval = null;
      }
      signal?.removeEventListener("abort", onAbort);
    };

    const onAbort = () => {
      if (settled) return;
      settled = true;
      cleanup();
      onProgress?.(resetDownloadingModel());
      reject(abortPullError());
    };

    if (signal?.aborted) {
      onAbort();
      return;
    }
    signal?.addEventListener("abort", onAbort);

    interval = setInterval(async () => {
      if (signal?.aborted) {
        onAbort();
        return;
      }
      try {
        const response = await fetch(`/api/v1/ppt/model/pull?model=${model}`);
        if (settled) return;
        if (response.status === 200) {
          const data = await response.json();
          if (data.done && data.status !== "error") {
            if (settled) return;
            settled = true;
            cleanup();
            onProgress?.(data);
            resolve(data);
          } else if (data.status === "error") {
            if (settled) return;
            settled = true;
            cleanup();
            onProgress?.(resetDownloadingModel());
            reject(new Error("Error occurred while pulling model"));
          } else {
            onProgress?.(data);
          }
        } else {
          if (settled) return;
          settled = true;
          cleanup();
          onProgress?.(resetDownloadingModel());
          if (response.status === 403) {
            reject(new Error("Request to model Not Authorized"));
          } else {
            reject(new Error("Error occurred while pulling model"));
          }
        }
      } catch (error) {
        if (settled) return;
        if (isAbortError(error)) {
          return;
        }
        settled = true;
        cleanup();
        onProgress?.(resetDownloadingModel());
        reject(error);
      }
    }, 1000);
  });
};