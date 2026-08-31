import { appConfig } from "../config.js";

// Client for the Node.js business API (auth, project mutations)
export const nodeClient = {
  baseUrl: appConfig.NODE_API_URL,
  token: null,

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem("civsight_token", token);
    } else {
      localStorage.removeItem("civsight_token");
    }
  },

  getToken() {
    if (this.token) return this.token;
    this.token = localStorage.getItem("civsight_token");
    return this.token;
  },

  async request({ method = "GET", endpoint = "", data = null }) {
    const token = this.getToken();
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), appConfig.DEFAULT_TIMEOUT);

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        body: data ? JSON.stringify(data) : null,
        credentials: "include",
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const payload = await response.json().catch(() => null);

      if (response.status === 401) {
        this.setToken(null);
      }

      return {
        ok: response.ok,
        status: response.status,
        data: payload,
      };
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === "AbortError") {
        return { ok: false, status: 408, data: { message: "Request timed out" } };
      }
      return { ok: false, status: 0, data: { message: error.message } };
    }
  },
};

// Initialize token from storage on import
nodeClient.getToken();
