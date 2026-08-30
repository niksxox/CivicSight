import { state, getProjectById, normalizeStatus, refreshProjectDerivedFields, projectStatusValues } from "./mockState.js";

export const projectsApi = {
  async getProjects() {
    return [...state.projects];
  },

  async getProject(id) {
    return getProjectById(state.projects, id);
  },

  async updateProjectStatus(id, status) {
    const project = getProjectById(state.projects, id);
    if (!project) throw new Error("Project not found");

    project.status = normalizeStatus(status);
    refreshProjectDerivedFields(project);
    return project;
  },

  async assignOfficer(id, officerId) {
    const project = getProjectById(state.projects, id);
    if (!project) throw new Error("Project not found");

    project.assignedOfficer = officerId;
    project.updated = "Just now";
    project.activity.unshift({
      id: `act-${Date.now()}`,
      title: "Officer assigned",
      time: "Just now",
      detail: `${officerId} assigned to project.`,
    });
    return project;
  },

  async verifyCompletion(id) {
    const project = getProjectById(state.projects, id);
    if (!project) throw new Error("Project not found");

    project.status = "Completed";
    project.actualProgress = 100;
    project.deviation = project.actualProgress - project.plannedProgress;
    refreshProjectDerivedFields(project);
    project.activity.unshift({
      id: `act-${Date.now()}`,
      title: "Completion verified",
      time: "Just now",
      detail: "Project verification completed by the government team.",
    });
    return project;
  },

  async listStatuses() {
    return [...projectStatusValues];
  },
};
