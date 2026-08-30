import { state, getDashboardCounts } from "./mockState.js";

export const analyticsApi = {
  async getDashboardStats() {
    return getDashboardCounts(state.projects);
  },

  async getAnalytics() {
    const projects = state.projects;

    const intervalData = [
      { label: "Apr", planned: 36, actual: 31 },
      { label: "May", planned: 43, actual: 39 },
      { label: "Jun", planned: 51, actual: 47 },
      { label: "Jul", planned: 59, actual: 54 },
      { label: "Aug", planned: 66, actual: 61 },
    ];

    const districtIssueBreakdown = [
      { district: "North district", count: 5, condition: "Moderate" },
      { district: "East district", count: 4, condition: "Stable" },
      { district: "South district", count: 6, condition: "High" },
      { district: "Central district", count: 2, condition: "Stable" },
      { district: "West district", count: 7, condition: "Critical" },
    ];

    const totalCompletion = Math.round((projects.filter((project) => project.status === "Completed").length / projects.length) * 100);
    const delayedProjects = projects.filter((project) => project.status === "Delayed" || project.status === "Critical").length;
    const citizenReports = state.reports.length;

    return {
      plannedVsActual: intervalData,
      delayedProjects,
      infrastructureCondition: {
        stable: 2,
        moderate: 2,
        high: 1,
        critical: 1,
      },
      issuesByDistrict: districtIssueBreakdown,
      reportVolume: citizenReports,
      completionRate: totalCompletion,
      populationAffected: 64200,
      interventionPriority: projects
        .slice()
        .sort((a, b) => b.deviation - a.deviation)
        .map((project) => ({
          id: project.id,
          name: project.name,
          priority: project.status === "Critical" ? "Critical" : project.status === "Delayed" ? "High" : "Medium",
          deviation: project.deviation,
        })),
    };
  },
};
