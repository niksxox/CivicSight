import {
  seedFacilities,
  seedCivicReports,
  seedRecommendations,
  seedResolutionPairs,
  districtDemographics,
} from "./civicIntelligenceData.js";

const seedProjects = [
  {
    id: "road-zone-a",
    name: "Road Development - Zone A",
    district: "North district",
    location: "North district",
    latitude: 17.3850,
    longitude: 78.4867,
    plannedProgress: 80,
    actualProgress: 55,
    deviation: -25,
    status: "Delayed",
    aiRisk: "High",
    aiConfidence: 89,
    aiExplanation: "Reported progress is 25 points behind plan. Surface condition suggests a schedule risk requiring inspection.",
    citizenReportCount: 4,
    assignedOfficer: "Anita Sharma",
    category: "Roads",
    budget: "Rs 18.4 Cr",
    updated: "18 min ago",
    coordinates: [24, 28],
    evidence: [
      {
        id: "evd-1001",
        projectId: "road-zone-a",
        projectName: "Road Development - Zone A",
        type: "image",
        fileName: "road-surface-1.jpg",
        mediaUrl: makeSvgDataUri("Road surface", "#7ec7b2", "#0f4c59"),
        location: "17.3850, 78.4867",
        description: "Road resurfacing is behind schedule and potholes are reappearing at the junction.",
        reportedProgress: 55,
        submittedAt: "2026-08-27T09:15:00Z",
        verificationStatus: "Under review",
      },
      {
        id: "evd-1002",
        projectId: "road-zone-a",
        projectName: "Road Development - Zone A",
        type: "video",
        fileName: "site-video-1.mp4",
        mediaUrl: makeSvgDataUri("Site video", "#d9b44a", "#44330b"),
        location: "17.3842, 78.4878",
        description: "Heavy vehicle movement is delaying work on the west lane.",
        reportedProgress: 52,
        submittedAt: "2026-08-29T08:05:00Z",
        verificationStatus: "Flagged",
      },
    ],
    activity: [
      { id: "act-1", title: "Citizen evidence submitted", time: "18 min ago", detail: "Road surface issue reported by a field user." },
      { id: "act-2", title: "AI risk review", time: "2 hrs ago", detail: "Deviation flagged against planned schedule." },
    ],
  },
  {
    id: "water-sector-4",
    name: "Water Supply Upgrade - Sector 4",
    district: "East district",
    location: "East district",
    latitude: 17.3667,
    longitude: 78.5244,
    plannedProgress: 62,
    actualProgress: 64,
    deviation: 2,
    status: "On Track",
    aiRisk: "Low",
    aiConfidence: 92,
    aiExplanation: "Current progress is tracking close to plan with minor variance.",
    citizenReportCount: 2,
    assignedOfficer: "Vikram Rao",
    category: "Water",
    budget: "Rs 9.8 Cr",
    updated: "2 hrs ago",
    coordinates: [53, 54],
    evidence: [
      {
        id: "evd-2001",
        projectId: "water-sector-4",
        projectName: "Water Supply Upgrade - Sector 4",
        type: "image",
        fileName: "pipeline-check.jpg",
        mediaUrl: makeSvgDataUri("Pipeline check", "#86c5ff", "#1f4d73"),
        location: "17.3667, 78.5244",
        description: "Pressure line installation is progressing as planned and no major blockages were found.",
        reportedProgress: 64,
        submittedAt: "2026-08-28T14:40:00Z",
        verificationStatus: "Verified",
      },
    ],
    activity: [
      { id: "act-3", title: "Pipeline inspection complete", time: "2 hrs ago", detail: "Pressure line work remains within timeline." },
    ],
  },
  {
    id: "bridge-river-road",
    name: "River Road Bridge",
    district: "South district",
    location: "South district",
    latitude: 17.3294,
    longitude: 78.6194,
    plannedProgress: 38,
    actualProgress: 31,
    deviation: -7,
    status: "At Risk",
    aiRisk: "Medium",
    aiConfidence: 81,
    aiExplanation: "Bridge work is behind schedule due to weather delay, but there is still a viable recovery path.",
    citizenReportCount: 1,
    assignedOfficer: "Meera Iyer",
    category: "Bridges",
    budget: "Rs 24.1 Cr",
    updated: "Yesterday",
    coordinates: [79, 35],
    evidence: [
      {
        id: "evd-3001",
        projectId: "bridge-river-road",
        projectName: "River Road Bridge",
        type: "image",
        fileName: "bridge-abutment.jpg",
        mediaUrl: makeSvgDataUri("Bridge abutment", "#ffcab2", "#9a3f2d"),
        location: "17.3294, 78.6194",
        description: "The abutment area is showing early cracking and water seepage after the rains.",
        reportedProgress: 31,
        submittedAt: "2026-08-26T11:00:00Z",
        verificationStatus: "Pending review",
      },
    ],
    activity: [
      { id: "act-4", title: "Weather delay noted", time: "Yesterday", detail: "Monsoon impacts have slowed completion." },
    ],
  },
  {
    id: "park-renovation",
    name: "Central Park Renovation",
    district: "Central district",
    location: "Central district",
    latitude: 17.4065,
    longitude: 78.4772,
    plannedProgress: 47,
    actualProgress: 49,
    deviation: 2,
    status: "Completed",
    aiRisk: "Low",
    aiConfidence: 94,
    aiExplanation: "Renovation is complete and no major defects have been found in verification checks.",
    citizenReportCount: 3,
    assignedOfficer: "Arjun Menon",
    category: "Public spaces",
    budget: "Rs 4.2 Cr",
    updated: "Yesterday",
    coordinates: [35, 76],
    evidence: [
      {
        id: "evd-4001",
        projectId: "park-renovation",
        projectName: "Central Park Renovation",
        type: "image",
        fileName: "park-final.jpg",
        mediaUrl: makeSvgDataUri("Park repair", "#c7f0d5", "#255f52"),
        location: "17.4065, 78.4772",
        description: "Final walk-through confirms that play equipment and pathways are in good condition.",
        reportedProgress: 49,
        submittedAt: "2026-08-25T13:05:00Z",
        verificationStatus: "Verified",
      },
    ],
    activity: [
      { id: "act-5", title: "Verification complete", time: "Yesterday", detail: "Completion signed off after final inspection." },
    ],
  },
  {
    id: "drainage-ward-12",
    name: "Drainage Network - Ward 12",
    district: "West district",
    location: "West district",
    latitude: 17.4381,
    longitude: 78.3940,
    plannedProgress: 68,
    actualProgress: 43,
    deviation: -25,
    status: "Critical",
    aiRisk: "High",
    aiConfidence: 88,
    aiExplanation: "Drainage work remains significantly below plan and poses a flood risk during seasonal rains.",
    citizenReportCount: 5,
    assignedOfficer: "Suhas Patel",
    category: "Drainage",
    budget: "Rs 12.6 Cr",
    updated: "5 mins ago",
    coordinates: [66, 22],
    evidence: [
      {
        id: "evd-5001",
        projectId: "drainage-ward-12",
        projectName: "Drainage Network - Ward 12",
        type: "image",
        fileName: "drainage-blockage.jpg",
        mediaUrl: makeSvgDataUri("Drainage blockage", "#d6d6ff", "#3d3d7a"),
        location: "17.4381, 78.3940",
        description: "Blocked culvert is causing standing water around the ward and near the pedestrian lane.",
        reportedProgress: 43,
        submittedAt: "2026-08-30T06:20:00Z",
        verificationStatus: "Urgent",
      },
    ],
    activity: [
      { id: "act-6", title: "Flood risk flagged", time: "5 mins ago", detail: "Citizen report elevated to emergency review." },
    ],
  },
  {
    id: "lighting-corridor-2",
    name: "Street Lighting - Corridor 2",
    district: "West district",
    location: "West district",
    latitude: 17.4519,
    longitude: 78.3825,
    plannedProgress: 52,
    actualProgress: 49,
    deviation: -3,
    status: "At Risk",
    aiRisk: "Medium",
    aiConfidence: 84,
    aiExplanation: "Lighting installation is slightly behind schedule due to procurement delays but still manageable.",
    citizenReportCount: 2,
    assignedOfficer: "Rohit Menon",
    category: "Utilities",
    budget: "Rs 6.3 Cr",
    updated: "1 day ago",
    coordinates: [46, 18],
    evidence: [
      {
        id: "evd-6001",
        projectId: "lighting-corridor-2",
        projectName: "Street Lighting - Corridor 2",
        type: "image",
        fileName: "lighting-pole.jpg",
        mediaUrl: makeSvgDataUri("Lighting pole", "#f4d77d", "#6b4b00"),
        location: "17.4519, 78.3825",
        description: "The main corridor is still partially unlit after a contractor delay.",
        reportedProgress: 49,
        submittedAt: "2026-08-29T17:20:00Z",
        verificationStatus: "Under review",
      },
    ],
    activity: [
      { id: "act-7", title: "Procurement issue noted", time: "1 day ago", detail: "Supplier delay affecting final installation." },
    ],
  },
];

const seedReports = [
  {
    id: "rep-1",
    projectId: "road-zone-a",
    projectName: "Road Development - Zone A",
    project: "Road Development - Zone A",
    files: [{ name: "road-surface-1.jpg", type: "image/jpeg" }],
    location: "17.3850, 78.4867",
    description: "Road resurfacing is behind schedule and potholes are reappearing at the junction.",
    submittedAt: "2026-08-27T09:15:00Z",
    status: "Under review",
    reportedProgress: 55,
  },
  {
    id: "rep-2",
    projectId: "drainage-ward-12",
    projectName: "Drainage Network - Ward 12",
    project: "Drainage Network - Ward 12",
    files: [{ name: "drainage-blockage.jpg", type: "image/jpeg" }],
    location: "17.4381, 78.3940",
    description: "Blocked culvert is causing standing water around the ward and near the pedestrian lane.",
    submittedAt: "2026-08-30T06:20:00Z",
    status: "Urgent",
    reportedProgress: 43,
  },
];

export const state = {
  projects: cloneProjects(seedProjects),
  reports: cloneReports(seedReports),
  facilities: seedFacilities.map((f) => ({ ...f })),
  civicReports: seedCivicReports.map((r) => ({ ...r })),
  recommendations: seedRecommendations.map((r) => ({ ...r })),
  resolutions: seedResolutionPairs.map((r) => ({ ...r })),
  demographics: [...districtDemographics],
  activityFeed: [
    { text: "AI generated new REPURPOSE recommendation for ZP School Pendurthi", time: "2 mins ago" },
    { text: "Critical water outage report submitted in Kurnool Ward 4", time: "14 mins ago" },
    { text: "Locked toilet report verified by field officer in Vijayawada", time: "1 hr ago" },
    { text: "Resolution verified for Tirupati Renigunta Sanitation Block #2", time: "3 hrs ago" },
    { text: "Citizen report escalated for Drainage Network - Ward 12", time: "4 hrs ago" },
  ],
};

function cloneProjects(projects) {
  return projects.map((project) => ({
    ...project,
    evidence: project.evidence.map((item) => ({ ...item })),
    activity: project.activity.map((item) => ({ ...item })),
  }));
}

function cloneReports(reports) {
  return reports.map((report) => ({ ...report }));
}

function makeSvgDataUri(label, from, to) {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="260" viewBox="0 0 400 260">
      <defs>
        <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="${from}" />
          <stop offset="100%" stop-color="${to}" />
        </linearGradient>
      </defs>
      <rect width="400" height="260" fill="url(#g)"/>
      <rect x="26" y="26" width="348" height="208" rx="18" fill="rgba(255,255,255,0.18)" stroke="rgba(255,255,255,0.35)"/>
      <text x="200" y="118" text-anchor="middle" font-family="Arial, sans-serif" font-size="26" fill="white" font-weight="700">${label}</text>
      <text x="200" y="154" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="rgba(255,255,255,0.9)">Infrastructure evidence</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export const normalizeStatus = (status) => {
  const map = {
    "On track": "On Track",
    "At risk": "At Risk",
    "Delayed": "Delayed",
    "Critical": "Critical",
    "Completed": "Completed",
  };
  return map[status] || status;
};

export const calculateDeviation = (project) => Number((project.actualProgress - project.plannedProgress).toFixed(0));

export const refreshProjectDerivedFields = (project) => {
  if (!project) return null;
  const deviation = calculateDeviation(project);
  project.deviation = deviation;
  project.updated = "Just now";
  project.aiRisk = project.status === "Critical" || project.status === "Delayed" ? "High" : project.status === "At Risk" ? "Medium" : "Low";
  project.aiConfidence = project.status === "Completed" ? 94 : project.status === "Delayed" ? 88 : project.status === "At Risk" ? 82 : 91;
  project.aiExplanation = project.status === "Completed"
    ? "Verification indicates the infrastructure is completed and stable."
    : project.status === "Delayed"
    ? "Work is running behind schedule and needs action from the delivery team."
    : project.status === "Critical"
    ? "Critical schedule and field signal risk require immediate intervention."
    : "Current progress is tracking to plan and remains within the expected range.";
  project.citizenReportCount = Array.isArray(project.evidence) ? project.evidence.length : 0;
  return project;
};

export const getProjectById = (projects, id) => projects.find((project) => project.id === id) || projects[0];

export const getDashboardCounts = (projects) => {
  const totals = { total: projects.length, "On Track": 0, "At Risk": 0, Delayed: 0, Critical: 0, Completed: 0 };
  projects.forEach((project) => {
    if (project.status in totals) totals[project.status] += 1;
  });
  return totals;
};

export const projectStatusValues = ["On Track", "At Risk", "Delayed", "Critical", "Completed"];

export const getProjectMaps = (projects) => projects.map((project) => ({
  ...project,
  markerColor: project.status === "Delayed" ? "red" : project.status === "Critical" ? "red" : project.status === "At Risk" ? "amber" : project.status === "Completed" ? "blue" : "green",
}));

export const getFacilitiesSummary = () => {
  const total = state.facilities.length;
  const operational = state.facilities.filter((f) => f.officialStatus === "OPERATIONAL").length;
  const underutilized = state.facilities.filter((f) => f.officialStatus === "UNDERUTILIZED").length;
  const abandoned = state.facilities.filter((f) => f.officialStatus === "ABANDONED").length;
  const defunct = state.facilities.filter((f) => f.officialStatus === "DEFUNCT").length;
  const atRiskTotal = underutilized + abandoned + defunct;
  return { total, operational, underutilized, abandoned, defunct, atRiskTotal };
};

export const getRecommendationsSummary = () => {
  const total = state.recommendations.length;
  const repair = state.recommendations.filter((r) => r.type === "REPAIR").length;
  const repurpose = state.recommendations.filter((r) => r.type === "REPURPOSE").length;
  const newlyDevelop = state.recommendations.filter((r) => r.type === "NEWLY_DEVELOP").length;
  const totalPopulation = state.recommendations.reduce((sum, r) => sum + (r.affectedPopulation || 0), 0);
  return { total, repair, repurpose, newlyDevelop, totalPopulation };
};

export const addCivicReport = (report) => {
  const newReport = {
    id: `civ-rep-${Date.now()}`,
    submittedAt: new Date().toISOString(),
    status: "CONFIRMED_ISSUE",
    aiConfidence: 91,
    aiTags: ["GROUND_VERIFIED", report.issueType || "DEFUNCT_FACILITY"],
    mediaUrl: makeSvgDataUri(report.issueTitle || "Citizen Report", "#b03a2e", "#641e16"),
    ...report,
  };
  state.civicReports.unshift(newReport);

  if (report.facilityId) {
    const facility = state.facilities.find((f) => f.id === report.facilityId);
    if (facility) {
      facility.citizenReportCount = (facility.citizenReportCount || 0) + 1;
      facility.abandonmentScore = Math.min(100, (facility.abandonmentScore || 50) + 6);
      if (facility.officialStatus === "OPERATIONAL") {
        facility.officialStatus = "UNDERUTILIZED";
      }
    }
  }

  state.activityFeed.unshift({
    text: `New citizen ground report filed: "${report.issueTitle || report.description?.slice(0, 35)}"`,
    time: "Just now",
  });

  return newReport;
};

