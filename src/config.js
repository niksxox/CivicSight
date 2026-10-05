// Single configurable API base URL. Defaults to the local FastAPI data backend.
// Override at runtime by setting window.CIVICSIGHT_CONFIG = { API_BASE_URL, API_MODE }
// (e.g. in Docker/nginx inject window.CIVICSIGHT_CONFIG = { API_BASE_URL: "/data-api", API_MODE: "live" }).
const injected = (typeof window !== "undefined" && window.CIVICSIGHT_CONFIG) || {};
const isProductionDomain =
  typeof window !== "undefined" &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1";

export const appConfig = {
  // In production (served via nginx on Render), use relative paths. In local development, use localhost URLs.
  API_BASE_URL: injected.API_BASE_URL || (isProductionDomain ? "/data-api" : "http://localhost:8000"),
  NODE_API_URL: injected.NODE_API_URL || (isProductionDomain ? "/api" : "http://localhost:5000/api"),
  AI_API_URL: injected.AI_API_URL || (isProductionDomain ? "/ai-api" : "http://localhost:8001"),
  API_MODE: injected.API_MODE || "live",
  DEFAULT_TIMEOUT: 12000,
};

export const getApiBaseUrl = () => appConfig.API_BASE_URL;
export const getNodeApiUrl = () => appConfig.NODE_API_URL;
export const getAiApiUrl = () => appConfig.AI_API_URL;
export const getApiMode = () => appConfig.API_MODE;
