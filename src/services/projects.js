import { state, getProjectById, normalizeStatus, refreshProjectDerivedFields, projectStatusValues } from "./mockState.js";
import { apiClient } from "./api.js";
import { nodeClient } from "./nodeApi.js";

// Backend current_status enum -> frontend label used by badges/summary.
const STATUS_MAP = {
  PLANNED: "Planned",
  IN_PROGRESS: "On Track",
  DELAYED: "Delayed",
  STALLED: "Critical",
  COMPLETED: "Completed",
  VERIFIED: "Verified",
};
const mapStatus = (s) => STATUS_MAP[s] || s;
const titleCase = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s || "");
const formatINR = (n) => (n == null ? "—" : `Rs ${(n / 1e7).toFixed(1)} Cr`);

// AI risk/confidence come from the separate AI service, not this data backend.
// Derived here only so the UI has a value until that service is wired in.
const deriveRisk = (dev) => {
  dev = dev ?? 0;
  return dev <= -10 ? "High" : dev <= -5 ? "Medium" : "Low";
};
const deriveExplanation = (dev) => {
  dev = dev ?? 0;
  return dev <= -10
    ? "Reported progress is behind plan and requires officer verification."
    : dev <= -5
    ? "Progress is under expected plan but still within a recoverable range."
    : "Progress is tracking to plan and remains stable.";
};
const relativeTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return d.toISOString().slice(0, 10);
};

// Deterministic schematic placement for the existing frontend map. This is NOT a
// geographic coordinate and is never derived from latitude/longitude.
const schematicCoordinates = (id) => {
  let h = 0;
  const s = String(id);
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return [10 + (h % 80), 10 + ((h >> 3) % 80)];
};

// Backend ProjectOut -> frontend project shape consumed by app.js.
function mapProject(p) {
  const deviation = Math.round((p.progress_deviation ?? (p.actual_progress ?? 0) - (p.planned_progress ?? 0)) * 100) / 100;
  return {
    id: String(p.id),
    name: p.name,
    district: p.district || "",
    location: [p.district, p.state].filter(Boolean).join(", ") || `${p.latitude}, ${p.longitude}`,
    latitude: p.latitude,
    longitude: p.longitude,
    plannedProgress: p.planned_progress ?? 0,
    actualProgress: p.actual_progress ?? 0,
    deviation,
    status: mapStatus(p.current_status),
    aiRisk: deriveRisk(deviation),
    aiConfidence: 85,
    aiExplanation: deriveExplanation(deviation),
    citizenReportCount: 0,
    assignedOfficer: "Unassigned",
    category: titleCase(p.category || ""),
    budget: formatINR(p.budget_allocated),
    updated: relativeTime(p.updated_at),
    coordinates: schematicCoordinates(p.id),
    evidence: [],
    activity: [],
  };
}

export const projectsApi = {
  // Hydrate the in-memory store from the real backend. Falls back to the seed
  // data already in state.projects if the backend is unreachable.
  async loadProjects() {
    const res = await apiClient.request({ method: "GET", endpoint: "/projects?limit=200" });
    if (!res.ok) throw new Error(`Projects API failed (${res.status})`);
    const payload = res.data || {};
    const items = Array.isArray(payload.items) ? payload.items : Array.isArray(payload) ? payload : [];
    if (!items.length) throw new Error("Projects API returned no rows");
    state.projects = items.map(mapProject);
    return state.projects;
  },

  async getProjects() {
    return [...state.projects];
  },

  async getProject(id) {
    return getProjectById(state.projects, id);
  },

  // --- These mutations now call the real Node.js backend ---
  async updateProjectStatus(id, status) {
    const res = await nodeClient.request({
      method: "PATCH",
      endpoint: `/projects/${id}/status`,
      data: { status },
    });
    if (!res.ok) throw new Error(res.data?.message || `Status update failed (${res.status})`);
    // Update local state with server response
    const project = getProjectById(state.projects, id);
    if (project) {
      project.status = normalizeStatus(res.data.status || status);
      refreshProjectDerivedFields(project);
    }
    return res.data;
  },

  async assignOfficer(id, officerName) {
    // First we need to find/create the user - for now we use the project patch endpoint
    const res = await nodeClient.request({
      method: "POST",
      endpoint: `/projects/${id}/assign`,
      data: { name: officerName },
    });
    if (!res.ok) throw new Error(res.data?.message || `Assignment failed (${res.status})`);
    const project = getProjectById(state.projects, id);
    if (project) {
      project.assignedOfficer = officerName;
      project.updated = "Just now";
    }
    return res.data;
  },

  async verifyCompletion(id) {
    const res = await nodeClient.request({
      method: "PATCH",
      endpoint: `/projects/${id}/status`,
      data: { status: "VERIFIED" },
    });
    if (!res.ok) throw new Error(res.data?.message || `Verification failed (${res.status})`);
    const project = getProjectById(state.projects, id);
    if (project) {
      project.status = "Completed";
      project.actualProgress = 100;
      project.deviation = project.actualProgress - project.plannedProgress;
      refreshProjectDerivedFields(project);
    }
    return res.data;
  },

  async listStatuses() {
    return [...projectStatusValues];
  },
};
