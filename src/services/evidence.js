import { state, getProjectById } from "./mockState.js";
import { apiClient } from "./api.js";

// Map a real project_history row -> frontend evidence/activity item.
function mapHistoryRow(row) {
  const when = row.recorded_at || row.submitted_at;
  return {
    id: `hist-${when || Math.random()}`,
    projectId: row.project_id,
    projectName: row.project_name || "",
    type: "record",
    fileName: row.note || "Status update",
    mediaUrl: "",
    location: "",
    description: row.note || "",
    reportedProgress: row.progress,
    submittedAt: when,
    verificationStatus: row.status || "Recorded",
  };
}

export const evidenceApi = {
  // No citizen-evidence create endpoint exists in the data backend — kept mock.
  async uploadEvidence(data) {
    const project = getProjectById(state.projects, data.projectId || state.projects[0].id);
    if (!project) throw new Error("Project not found");

    const item = {
      id: `evd-${Date.now()}`,
      projectId: project.id,
      projectName: project.name,
      type: data.type || "image",
      fileName: data.fileName || "uploaded-evidence.jpg",
      mediaUrl: data.mediaUrl || "",
      location: data.location || `${project.latitude}, ${project.longitude}`,
      description: data.description || "",
      reportedProgress: Number(data.reportedProgress ?? project.actualProgress),
      submittedAt: new Date().toISOString(),
      verificationStatus: "Under review",
    };

    project.evidence.unshift(item);
    project.updated = "Just now";
    return item;
  },

  async getEvidence(id) {
    const projectWithEvidence = state.projects.find((project) => project.evidence.some((item) => item.id === id));
    if (!projectWithEvidence) return null;
    return projectWithEvidence.evidence.find((item) => item.id === id) || null;
  },

  // Real evidence timeline from the data backend's project history.
  async getProjectEvidence(projectId) {
    const res = await apiClient.request({ method: "GET", endpoint: `/projects/${projectId}/history` });
    if (!res.ok) throw new Error(`Evidence API failed (${res.status})`);
    const rows = Array.isArray(res.data) ? res.data : [];
    return rows.map(mapHistoryRow);
  },
};
