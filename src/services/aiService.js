import { appConfig } from "../config.js";

// Client for the AI service
const AI_BASE = appConfig.AI_API_URL;

export const aiApiService = {
  async analyzeImage(file) {
    const formData = new FormData();
    formData.append("image", file);
    const res = await fetch(`${AI_BASE}/ai/analyze-image`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`AI analysis failed (${res.status})`);
    return res.json();
  },

  async assessProgress(plannedProgress, estimatedActualProgress) {
    const res = await fetch(`${AI_BASE}/ai/assess-progress`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ planned_progress: plannedProgress, estimated_actual_progress: estimatedActualProgress }),
    });
    if (!res.ok) throw new Error(`Progress assessment failed (${res.status})`);
    return res.json();
  },

  async extractIssue(text) {
    const res = await fetch(`${AI_BASE}/ai/extract-issue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(`Issue extraction failed (${res.status})`);
    return res.json();
  },

  async health() {
    try {
      const res = await fetch(`${AI_BASE}/health`);
      return res.ok;
    } catch {
      return false;
    }
  },
};
