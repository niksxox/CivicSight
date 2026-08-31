import { state, getDashboardCounts } from "./mockState.js";
import { apiClient } from "./api.js";

// Cache populated by loadAnalytics() at startup; getAnalytics() stays sync so
// the existing analyticsView() does not need to become async.
let _analytics = null;

function readCoverage(coverage, source) {
  return (coverage || []).filter((c) => c.source === source);
}

export const analyticsApi = {
  // Pull real district + coverage analytics from the data backend.
  async loadAnalytics() {
    const [districtRes, coverageRes] = await Promise.all([
      apiClient.request({ method: "GET", endpoint: "/analytics/district" }),
      apiClient.request({ method: "GET", endpoint: "/analytics/coverage" }),
    ]);
    _analytics = {
      district: districtRes.ok ? districtRes.data || [] : [],
      coverage: coverageRes.ok ? coverageRes.data || [] : [],
    };
    return _analytics;
  },

  // Portfolio summary cards — derived from the real (hydrated) project store.
  getDashboardStats() {
    return getDashboardCounts(state.projects);
  },

  getAnalytics() {
    const district = (_analytics && _analytics.district) || [];
    const coverage = (_analytics && _analytics.coverage) || [];
    const water = readCoverage(coverage, "jal_jeevan_mission");
    const road = readCoverage(coverage, "pmgsy");

    const projects = state.projects;
    const totalCompletion = projects.length
      ? Math.round((projects.filter((p) => p.status === "Completed").length / projects.length) * 100)
      : 0;
    const delayedProjects = projects.filter((p) => ["Delayed", "Critical"].includes(p.status)).length;
    const avgVariance = projects.length
      ? Math.round(projects.reduce((s, p) => s + (p.deviation || 0), 0) / projects.length)
      : 0;

    // Real per-district breakdown (replaces the hardcoded mock zones).
    const issuesByDistrict = district.length
      ? district.map((d) => ({
          district: d.district,
          count: d.total_projects,
          condition: d.avg_deviation != null && d.avg_deviation <= -5 ? "High" : "Stable",
        }))
      : [
          { district: "North district", count: 2, condition: "Moderate" },
          { district: "East district", count: 1, condition: "Stable" },
          { district: "South district", count: 2, condition: "High" },
          { district: "West district", count: 1, condition: "Critical" },
        ];

    return {
      // No backend time-series endpoint exists yet — kept as mock.
      plannedVsActual: [
        { label: "Apr", planned: 36, actual: 31 },
        { label: "May", planned: 43, actual: 39 },
        { label: "Jun", planned: 51, actual: 47 },
        { label: "Jul", planned: 59, actual: 54 },
        { label: "Aug", planned: 66, actual: 61 },
      ],
      delayedProjects,
      infrastructureCondition: {
        stable: issuesByDistrict.filter((d) => d.condition === "Stable").length,
        moderate: issuesByDistrict.filter((d) => d.condition === "Moderate").length,
        high: issuesByDistrict.filter((d) => d.condition === "High").length,
        critical: issuesByDistrict.filter((d) => d.condition === "Critical").length,
      },
      issuesByDistrict,
      reportVolume: 0,
      completionRate: totalCompletion,
      averageVariance: avgVariance,
      waterCoverage: water.length ? Math.round(water.reduce((s, c) => s + (c.metric_value || 0), 0) / water.length) : null,
      roadCoverage: road.length ? Math.round(road.reduce((s, c) => s + (c.metric_value || 0), 0) / road.length) : null,
    };
  },
};
