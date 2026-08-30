export const appConfig = {
  API_BASE_URL: (typeof window !== "undefined" && window.CIVICSIGHT_CONFIG && window.CIVICSIGHT_CONFIG.API_BASE_URL) || "",
  API_MODE: (typeof window !== "undefined" && window.CIVICSIGHT_CONFIG && window.CIVICSIGHT_CONFIG.API_MODE) || "mock",
  DEFAULT_TIMEOUT: 1200,
};

export const getApiBaseUrl = () => appConfig.API_BASE_URL || "";

export const getApiMode = () => appConfig.API_MODE || "mock";
