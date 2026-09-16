// Single configurable API base URL. Defaults to the local FastAPI data backend.
// Override at runtime by setting window.CIVICSIGHT_CONFIG = { API_BASE_URL, API_MODE }
// (e.g. in Docker/nginx inject window.CIVICSIGHT_CONFIG = { API_BASE_URL: "/data-api", API_MODE: "live" }).
const injected = (typeof window !== "undefined" && window.CIVICSIGHT_CONFIG) || {};

export const appConfig = {
  // In production (served via nginx), use relative paths. In development, use full URLs.
  API_BASE_URL: injected.API_BASE_URL || "http://localhost:8000",
  NODE_API_URL: injected.NODE_API_URL || "http://localhost:5000/api",
  AI_API_URL: injected.AI_API_URL || "http://localhost:8001",
  API_MODE: injected.API_MODE || "live",
  DEFAULT_TIMEOUT: 12000,
};

export const getApiBaseUrl = () => appConfig.API_BASE_URL;
export const getNodeApiUrl = () => appConfig.NODE_API_URL;
export const getAiApiUrl = () => appConfig.AI_API_URL;
export const getApiMode = () => appConfig.API_MODE;
