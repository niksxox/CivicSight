export const projects = [
  { id: "road-zone-a", name: "Road Development - Zone A", area: "North district", category: "Roads", planned: 80, actual: 55, status: "Delayed", risk: "HIGH", officer: "Anita Sharma", budget: "Rs 18.4 Cr", updated: "18 min ago", coordinates: [24, 28] },
  { id: "water-sector-4", name: "Water Supply Upgrade - Sector 4", area: "East district", category: "Water", planned: 62, actual: 64, status: "On Track", risk: "LOW", officer: "Vikram Rao", budget: "Rs 9.8 Cr", updated: "2 hrs ago", coordinates: [53, 54] },
  { id: "bridge-river-road", name: "River Road Bridge", area: "South district", category: "Bridges", planned: 38, actual: 31, status: "At Risk", risk: "MEDIUM", officer: "Meera Iyer", budget: "Rs 24.1 Cr", updated: "Yesterday", coordinates: [79, 35] },
  { id: "park-renovation", name: "Central Park Renovation", area: "Central district", category: "Public spaces", planned: 47, actual: 49, status: "Completed", risk: "LOW", officer: "Arjun Menon", budget: "Rs 4.2 Cr", updated: "Yesterday", coordinates: [35, 76] }
];

export const activities = [
  { text: "New evidence submitted for Road Development - Zone A", time: "18 min ago" },
  { text: "Officer assignment updated for River Road Bridge", time: "1 hr ago" },
  { text: "Completion verification requested for Sector 4", time: "2 hrs ago" },
  { text: "Progress report exported by Anita Sharma", time: "Yesterday" }
];

const submissions = [];
const portfolioTotals = { "On Track": 96, "At Risk": 10, Delayed: 31, Critical: 8, Completed: 13 };

function statusKey(status) { return status === "On track" ? "On Track" : status === "At risk" ? "At Risk" : status; }

export const mockService = {
  listProjects: () => projects,
  getProject: (id) => projects.find((project) => project.id === id) || projects[0],
  listSubmissions: () => submissions,
  getDashboardSummary: () => ({ total: 148, ...portfolioTotals }),
  updateStatus: (projectId, status) => {
    const project = projects.find((item) => item.id === projectId);
    if (!project) throw new Error("Project not found");
    const previous = statusKey(project.status);
    if (portfolioTotals[previous] > 0) portfolioTotals[previous] -= 1;
    portfolioTotals[status] = (portfolioTotals[status] || 0) + 1;
    project.status = status;
    project.risk = status === "Critical" || status === "Delayed" ? "HIGH" : status === "At Risk" ? "MEDIUM" : "LOW";
    project.updated = "Just now";
    return project;
  },
  assignOfficer: (projectId, officer) => {
    const project = projects.find((item) => item.id === projectId);
    if (!project) throw new Error("Project not found");
    project.officer = officer;
    project.updated = "Just now";
    return project;
  },
  submitEvidence: (payload) => {
    const submission = { id: `EVD-${Date.now()}`, ...payload, submittedAt: new Date().toISOString(), status: "Under review" };
    submissions.unshift(submission);
    const project = projects.find((item) => item.name === payload.project);
    if (project && payload.reportedProgress) {
      project.actual = payload.reportedProgress;
      project.status = project.actual < project.planned - 10 ? "Delayed" : project.status;
      project.updated = "Just now";
    }
    return submission;
  }
};

// This response mirrors the future API contract and can be replaced with a fetch call.
export const aiAnalysisService = {
  analyze: async () => ({
    plannedProgress: 80,
    reportedProgress: 55,
    deviation: -25,
    riskLevel: "High",
    finding: "Potential delay detected",
    confidence: 89,
    explanation: "Reported progress is 25 points behind the plan. Officer verification is recommended."
  })
};