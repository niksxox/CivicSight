import { state } from "./mockState.js";
import { getNodeApiUrl, getApiMode } from "../config.js";

export const recommendationsApi = {
  async getRecommendations(filter = {}) {
    if (getApiMode() === "live") {
      try {
        const query = new URLSearchParams(filter).toString();
        const res = await fetch(`${getNodeApiUrl()}/recommendations${query ? `?${query}` : ""}`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.length) return data;
        }
      } catch (err) {
        console.warn("Live recommendations API fallback to local state:", err);
      }
    }
    let list = state.recommendations;
    if (filter.type && filter.type !== "all") {
      list = list.filter((r) => r.type.toLowerCase() === filter.type.toLowerCase());
    }
    if (filter.district && filter.district !== "all") {
      list = list.filter((r) => r.district.toLowerCase() === filter.district.toLowerCase());
    }
    return list;
  },

  async approveRecommendation(id) {
    const rec = state.recommendations.find((r) => r.id === id);
    if (rec) {
      rec.status = "APPROVED_BY_OFFICER";
      state.activityFeed.unshift({
        text: `Officer approved recommendation: ${rec.title || rec.targetFacilityName}`,
        time: "Just now",
      });
    }
    return rec;
  },
};
