export interface ModelOption {
  value: string;
  label: string;
  description?: string;
  icon?: string;
  size: string;
}

export interface ImageProviderOption {
  value: string;
  label: string;
  description?: string;
  icon?: string;
  requiresApiKey?: boolean;
  apiKeyField?: string;
  apiKeyFieldLabel?: string;
}

export interface LLMProviderOption {
  value: string;
  label: string;
  description?: string;
  model_value?: string;
  model_label?: string;
  url?: string;
  icon?: string;
}

export const IMAGE_PROVIDERS: Record<string, ImageProviderOption> = {
  pexels: {
    value: "pexels",
    label: "Pexels",
    description: "Free stock photo and video platform",
    icon: "/icons/pexels.png",
    requiresApiKey: true,
    apiKeyField: "PEXELS_API_KEY",
    apiKeyFieldLabel: "Pexels API Key",
  },
  pixabay: {
    value: "pixabay",
    label: "Pixabay",
    description: "Free images and videos",
    icon: "/icons/pixabay.png",
    requiresApiKey: true,
    apiKeyField: "PIXABAY_API_KEY",
    apiKeyFieldLabel: "Pixabay API Key",
  },
  "dall-e-3": {
    value: "dall-e-3",
    label: "DALL-E 3",
    description: "OpenAI's image generation model",
    icon: "/icons/dall-e.png",
    requiresApiKey: true,
    apiKeyField: "OPENAI_API_KEY",
    apiKeyFieldLabel: "OpenAI API Key",
  },
  "gpt-image-1.5": {
    value: "gpt-image-1.5",
    label: "GPT Image 1.5",
    description: "OpenAI's image generation model",
    icon: "/icons/gpt.png",
    requiresApiKey: true,
    apiKeyField: "OPENAI_API_KEY",
    apiKeyFieldLabel: "OpenAI API Key",
  },
  comfyui: {
    value: "comfyui",
    label: "ComfyUI",
    description: "Use your local ComfyUI server with custom workflows",
    icon: "/icons/comfyui.png",
    requiresApiKey: false,
    apiKeyField: "COMFYUI_URL",
    apiKeyFieldLabel: "ComfyUI Server URL",
  },
  open_webui: {
    value: "open_webui",
    label: "Open WebUI",
    description: "Use your Open WebUI server for image generation",
    icon: "/icons/open-webui.png",
    requiresApiKey: false,
    apiKeyField: "OPEN_WEBUI_IMAGE_URL",
    apiKeyFieldLabel: "Open WebUI URL",
  },
};

export const LLM_PROVIDERS: Record<string, LLMProviderOption> = {
  openai: {
    value: "openai",
    label: "OpenAI",
    description: "OpenAI's latest text generation model",
    url: "https://api.openai.com/v1",
    icon: "/icons/openai.png",
  },
  custom: {
    value: "custom",
    label: "Custom",
    description: "Custom LLM (OpenAI Compatible, Local Llama, etc.)",
    icon: "/icons/custom.png",
  },
};

export const DALLE_3_QUALITY_OPTIONS = [
  {
    label: "Standard",
    value: "standard",
    description: "Faster generation with lower cost",
  },
  {
    label: "HD",
    value: "hd",
    description: "Higher quality images with increased cost",
  },
];

export const GPT_IMAGE_1_5_QUALITY_OPTIONS = [
  {
    label: "Low",
    value: "low",
    description: "Fastest and most cost-effective",
  },
  {
    label: "Medium",
    value: "medium",
    description: "Balanced quality and speed",
  },
  {
    label: "High",
    value: "high",
    description: "Best quality with longer generation time",
  },
];
