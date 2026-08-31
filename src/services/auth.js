import { nodeClient } from "./nodeApi.js";

export const authApi = {
  async register({ name, email, password, role = "CITIZEN" }) {
    const res = await nodeClient.request({
      method: "POST",
      endpoint: "/auth/register",
      data: { name, email, password, role },
    });
    if (res.ok && res.data?.token) {
      nodeClient.setToken(res.data.token);
    }
    return res;
  },

  async login({ email, password }) {
    const res = await nodeClient.request({
      method: "POST",
      endpoint: "/auth/login",
      data: { email, password },
    });
    if (res.ok && res.data?.token) {
      nodeClient.setToken(res.data.token);
    }
    return res;
  },

  async getMe() {
    const res = await nodeClient.request({
      method: "GET",
      endpoint: "/auth/me",
    });
    return res;
  },

  logout() {
    nodeClient.setToken(null);
  },

  isAuthenticated() {
    return Boolean(nodeClient.getToken());
  },

  getUser() {
    const token = nodeClient.getToken();
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload;
    } catch {
      return null;
    }
  },
};
