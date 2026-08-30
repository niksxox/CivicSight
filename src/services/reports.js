import { state, getProjectById, refreshProjectDerivedFields } from "./mockState.js";

export const reportsApi = {
  async submitReport(data) {
    const project = getProjectById(state.projects, data.projectId || state.projects[0].id);
    if (!project) throw new Error("Project not found");

    const report = {
      id: `rep-${Date.now()}`,
      projectId: project.id,
      projectName: project.name,
      project: project.name,
      files: Array.isArray(data.files) ? data.files : [],
      location: data.location || `${project.latitude}, ${project.longitude}`,
      description: data.description || "",
      submittedAt: new Date().toISOString(),
      status: "Under review",
      reportedProgress: Number(data.reportedProgress ?? project.actualProgress),
    };

    state.reports.unshift(report);

    const evidenceEntry = {
      id: `evd-${Date.now()}`,
      projectId: project.id,
      projectName: project.name,
      type: data.files?.[0]?.type?.startsWith("video/") ? "video" : "image",
      fileName: data.files?.[0]?.name || "evidence-upload.jpg",
      mediaUrl: data.previewUrl || `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300"><rect width="100%" height="100%" fill="#d8f0ff"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial" font-size="28" fill="#0b2d40">Field evidence</text></svg>`)}`,
      location: report.location,
      description: report.description,
      reportedProgress: report.reportedProgress,
      submittedAt: report.submittedAt,
      verificationStatus: "Under review",
    };

    project.evidence.unshift(evidenceEntry);
    project.actualProgress = report.reportedProgress;
    project.deviation = project.actualProgress - project.plannedProgress;
    project.updated = "Just now";
    project.activity.unshift({
      id: `act-${Date.now()}`,
      title: "Citizen evidence submitted",
      time: "Just now",
      detail: `${project.name} received a fresh field report.`,
    });
    refreshProjectDerivedFields(project);

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
