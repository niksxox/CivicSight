import { state, getProjectById, refreshProjectDerivedFields } from "./mockState.js";
import { nodeClient } from "./nodeApi.js";

export const reportsApi = {
  async submitReport(data) {
    // Submit evidence to the real Node.js backend
    const res = await nodeClient.request({
      method: "POST",
      endpoint: `/projects/${data.projectId}/evidence`,
      data: {
        photoUrl: data.previewUrl || "",
        location: data.location,
        description: data.description,
      },
    });

    if (!res.ok) {
      throw new Error(res.data?.message || `Evidence submission failed (${res.status})`);
    }

    // Update local state for immediate UI feedback
    const project = getProjectById(state.projects, data.projectId);
    if (project) {
      const evidenceEntry = {
        id: res.data._id || `evd-${Date.now()}`,
        projectId: project.id,
        projectName: project.name,
        type: data.files?.[0]?.type?.startsWith("video/") ? "video" : "image",
        fileName: data.files?.[0]?.name || "evidence-upload.jpg",
        mediaUrl: data.previewUrl || "",
        location: data.location,
        description: data.description,
        reportedProgress: data.reportedProgress,
        submittedAt: new Date().toISOString(),
        verificationStatus: "Under review",
      };
      project.evidence.unshift(evidenceEntry);
      project.actualProgress = data.reportedProgress;
      project.deviation = project.actualProgress - project.plannedProgress;
      project.updated = "Just now";
      project.activity.unshift({
        id: `act-${Date.now()}`,
        title: "Citizen evidence submitted",
        time: "Just now",
        detail: `${project.name} received a fresh field report.`,
      });
      refreshProjectDerivedFields(project);
    }

    const report = {
      id: res.data._id || `rep-${Date.now()}`,
      projectId: data.projectId,
      projectName: project?.name || data.project,
      project: project?.name || data.project,
      files: Array.isArray(data.files) ? data.files : [],
      location: data.location,
      description: data.description,
      submittedAt: new Date().toISOString(),
      status: "Under review",
      reportedProgress: data.reportedProgress,
    };

    state.reports.unshift(report);
    return report;
  },

  async getProjectReports(projectId) {
    const project = getProjectById(state.projects, projectId);
    return project ? [...project.evidence] : [];
  },

  async getReport(id) {
    return state.reports.find((report) => report.id === id) || null;
  },

  async listReports() {
    return [...state.reports];
  },
};
