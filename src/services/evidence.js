import { state, getProjectById } from "./mockState.js";

export const evidenceApi = {
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

  async getProjectEvidence(projectId) {
    const project = getProjectById(state.projects, projectId);
    return project ? [...project.evidence] : [];
  },
};
