import { state, addCivicReport } from "./mockState.js";
import { getNodeApiUrl, getApiMode } from "../config.js";

export const civicReportsApi = {
  async getReports(filter = {}) {
    if (getApiMode() === "live") {
      try {
        const query = new URLSearchParams(filter).toString();
        const res = await fetch(`${getNodeApiUrl()}/civic-reports${query ? `?${query}` : ""}`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.length) return data;
        }
      } catch (err) {
        console.warn("Live civic reports API fallback to local state:", err);
      }
    }
    let list = state.civicReports;
    if (filter.issueType && filter.issueType !== "all") {
      list = list.filter((r) => r.issueType === filter.issueType);
    }
    if (filter.district && filter.district !== "all") {
      list = list.filter((r) => r.district.toLowerCase() === filter.district.toLowerCase());
    }
    return list;
  },

  async submitReport(payload) {
    if (getApiMode() === "live") {
      try {
        const res = await fetch(`${getNodeApiUrl()}/civic-reports`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (res.ok) {
          const created = await res.json();
          return addCivicReport(created);
        }
      } catch (err) {
        console.warn("Live civic report submit fallback to local:", err);
      }
    }
    return addCivicReport(payload);
  },

  async getResolutions() {
    return state.resolutions;
  },

  async verifyResolution(id, feedback = {}) {
    const item = state.resolutions.find((r) => r.id === id);
    if (item) {
      item.status = "VERIFIED_RESOLVED";
      item.officerSignoff = feedback.officerSignoff || "Verified by Field Officer";
      item.signoffDate = new Date().toISOString().slice(0, 10);
    }
    return item;
  },
};
