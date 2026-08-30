import { appConfig } from "../config.js";

export const apiClient = {
  baseUrl: appConfig.API_BASE_URL,
  mode: appConfig.API_MODE,
  async request({ method = "GET", endpoint = "", data = null, headers = {} }) {
    const finalUrl = `${this.baseUrl}${endpoint}`;

    if (this.mode === "mock") {
      return {
        ok: true,
        status: 200,
        url: finalUrl,
        data,
        headers,
        method,
      };
    }

    const response = await fetch(finalUrl, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      body: data ? JSON.stringify(data) : null,
    });

    const payload = await response.json().catch(() => null);

    return {
      ok: response.ok,
      status: response.status,
      data: payload,
    };
  },
};

export const withLoading = async (operation, callback) => {
  try {
    operation?.({ loading: true });
    const result = await callback();
    operation?.({ loading: false, success: true, data: result });
    return result;
  } catch (error) {
    operation?.({ loading: false, success: false, error });
    throw error;
  }
};
