import { state } from "./mockState.js";
import { getApiBaseUrl, getApiMode } from "../config.js";

export const facilitiesApi = {
  async getFacilities(filter = {}) {
    if (getApiMode() === "live") {
      try {
        const query = new URLSearchParams(filter).toString();
        const res = await fetch(`${getApiBaseUrl()}/infrastructure${query ? `?${query}` : ""}`);
        if (res.ok) {
          const data = await res.json();
          if (data.facilities && data.facilities.length) {
            return data.facilities;
          }
        }
      } catch (err) {
        console.warn("Live infrastructure API fallback to local state:", err);
      }
    }
    let list = state.facilities;
    if (filter.district) {
      list = list.filter((f) => f.district.toLowerCase() === filter.district.toLowerCase());
    }
    if (filter.type) {
      list = list.filter((f) => f.type.toLowerCase() === filter.type.toLowerCase());
    }
    if (filter.status) {
      list = list.filter((f) => f.officialStatus.toLowerCase() === filter.status.toLowerCase());
    }
    return list;
  },

  async getFacilityById(id) {
    return state.facilities.find((f) => f.id === id) || null;
  },

  async updateFacilityStatus(id, newStatus) {
    const fac = state.facilities.find((f) => f.id === id);
    if (fac) {
      fac.officialStatus = newStatus;
      if (newStatus === "OPERATIONAL") fac.abandonmentScore = 15;
      if (newStatus === "ABANDONED") fac.abandonmentScore = 95;
    }
    return fac;
  },
};
