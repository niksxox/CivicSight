import {
  state,
  getProjectById,
  getDashboardCounts,
  getFacilitiesSummary,
  getRecommendationsSummary,
  projectStatusValues,
  addCivicReport,
  makeSvgDataUri,
} from "./services/mockState.js";
import {
  projectsApi,
  reportsApi,
  analyticsApi,
  aiApi,
  evidenceApi,
  facilitiesApi,
  recommendationsApi,
  civicReportsApi,
} from "./services/index.js";

const app = document.querySelector("#app");
let role = "officer";
let latestSubmission = state.reports[0] || null;
let latestAnalysis = null;
let activeMapInstance = null;
let currentBasemap = "streets"; // "streets" | "satellite"
let activeFilter = "all";
let activeRecFilter = "all";

const icons = {
  dashboard: "🎛️",
  projects: "📋",
  map: "🗺️",
  capture: "📸",
  analytics: "📊",
  evidence: "📁",
  verify: "✅",
  abandonment: "🏚️",
  recommendations: "💡",
};

const officerNav = [
  ["Command center", "dashboard", "#/dashboard"],
  ["GIS satellite map", "map", "#/map"],
  ["Abandonment detector", "abandonment", "#/abandonment"],
  ["AI recommendations", "recommendations", "#/recommendations"],
  ["Resolution studio", "verify", "#/resolutions"],
  ["Capital projects", "projects", "#/projects"],
  ["Demographics & analytics", "analytics", "#/analytics"],
];

const citizenNav = [
  ["Report civic issue", "capture", "#/report"],
  ["Civic map & alerts", "map", "#/map"],
  ["AI recommendations", "recommendations", "#/recommendations"],
  ["Verified resolutions", "verify", "#/resolutions"],
  ["My submissions", "evidence", "#/submissions"],
];

const getProjects = () => state.projects;
const getProject = (id) => getProjectById(state.projects, id);
const getDashboardSummary = () => getDashboardCounts(state.projects);

function pageHeading(eyebrow, title, description, action = "") {
  return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="subhead">${description}</p></div>${action}</div>`;
}

function badge(status) {
  const kind = ["On Track", "Completed", "OPERATIONAL"].includes(status)
    ? "green"
    : ["At Risk", "Critical", "ABANDONED", "DEFUNCT"].includes(status)
    ? "red"
    : "amber";
  return `<span class="badge ${kind}">${status}</span>`;
}

function abandonmentBadge(score) {
  if (score >= 85) return `<span class="abandonment-badge abandonment-critical">Critical risk (${score}%)</span>`;
  if (score >= 70) return `<span class="abandonment-badge abandonment-high">High risk (${score}%)</span>`;
  if (score >= 50) return `<span class="abandonment-badge abandonment-medium">Moderate (${score}%)</span>`;
  return `<span class="abandonment-badge abandonment-low">Low risk (${score}%)</span>`;
}

function riskBadge(risk = "Low") {
  const normalized = String(risk).toLowerCase();
  return `<span class="risk risk-${normalized}">${risk}</span>`;
}

function layout(content, currentRoute) {
  const nav = role === "officer" ? officerNav : citizenNav;
  return `<div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#/dashboard"><span class="brand-mark"><span>+</span></span><span><strong>CivicSight</strong><small>Civic Intelligence</small></span></a>
      <div class="role-switcher">
        <button class="${role === "citizen" ? "active" : ""}" data-role="citizen">Citizen portal</button>
        <button class="${role === "officer" ? "active" : ""}" data-role="officer">Government</button>
      </div>
      <div class="nav-label">Workspace</div>
      <nav class="nav">${nav
        .map(
          ([label, icon, href]) =>
            `<a class="${currentRoute === href.slice(2) ? "active" : ""}" href="${href}"><span class="nav-icon">${icons[icon]}</span>${label}</a>`
        )
        .join("")}</nav>
      <div class="sidebar-footer">
        <strong>${role === "officer" ? "District Planning & Works" : "Civic Action Platform"}</strong>
        ${role === "officer" ? "Cross-referencing gov & citizen data" : "Ground reports empower community action"}
      </div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="breadcrumb">CivicSight / <b>${role === "officer" ? "Government command center" : "Citizen ground reporter"}</b></div>
        <div class="top-actions">
          <button title="Notifications">🔔</button>
          <span class="avatar">${role === "officer" ? "GOV" : "CIT"}</span>
        </div>
      </header>
      ${content}
    </main>
  </div>`;
}

/* ==========================================================================
   GIS Leaflet Multi-layer Map Engine (Streets + Satellite)
   ========================================================================== */

function mountLeafletMap(containerId = "gis-leaflet-map", filterType = "all") {
  if (typeof L === "undefined") {
    console.warn("Leaflet library not found.");
    return;
  }
  const container = document.getElementById(containerId);
  if (!container) return;

  if (activeMapInstance) {
    try {
      activeMapInstance.remove();
    } catch (e) {
      console.warn("Map cleanup:", e);
    }
    activeMapInstance = null;
  }

  // AP center
  const map = L.map(containerId).setView([16.4, 80.5], 8);
  activeMapInstance = map;

  const streetLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors",
  });

  const satelliteLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
    }
  );

  if (currentBasemap === "satellite") {
    satelliteLayer.addTo(map);
  } else {
    streetLayer.addTo(map);
  }

  // Markers
  const bounds = [];

  // 1. Facilities
  state.facilities.forEach((fac) => {
    if (filterType !== "all" && filterType !== fac.type) return;
    bounds.push([fac.lat, fac.lng]);

    let color = "#2563eb";
    let iconChar = "🏛️";
    if (fac.type === "school") {
      color = "#7c3aed";
      iconChar = "🏫";
    } else if (fac.type === "toilet") {
      color = "#d97706";
      iconChar = "🚾";
    } else if (fac.type === "water") {
      color = "#0284c7";
      iconChar = "💧";
    } else if (fac.type === "health") {
      color = "#059669";
      iconChar = "🏥";
    }

    if (fac.officialStatus === "ABANDONED" || fac.officialStatus === "DEFUNCT") {
      color = "#dc2626";
    }

    const customMarker = L.divIcon({
      className: "custom-gis-pin",
      html: `<div style="background:${color};width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:16px;border:2.5px solid white;box-shadow:0 3px 8px rgba(0,0,0,0.35);">${iconChar}</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });

    const popupContent = `
      <div style="font-family:sans-serif;min-width:220px;">
        <span style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;">${fac.district} • ${fac.type}</span>
        <h4 style="margin:4px 0 6px;font-size:14px;color:#0f172a;">${fac.name}</h4>
        <div style="margin-bottom:8px;">
          ${badge(fac.officialStatus)}
          ${abandonmentBadge(fac.abandonmentScore)}
        </div>
        <p style="font-size:12px;color:#334155;margin:0 0 8px;line-height:1.4;">${fac.conditionNotes}</p>
        <div style="background:#f8fafc;padding:6px 8px;border-radius:4px;font-size:11px;color:#475569;margin-bottom:8px;">
          <div>👥 Catchment: <b>${fac.populationCatchment?.toLocaleString()} residents</b></div>
          <div>📢 Citizen ground alerts: <b>${fac.citizenReportCount} reports</b></div>
          ${fac.recommendedAction ? `<div>💡 AI Recommendation: <b>${fac.recommendedAction}</b></div>` : ""}
        </div>
        <a href="#/report" style="display:inline-block;padding:5px 9px;background:#0d9488;color:white;text-decoration:none;border-radius:4px;font-size:11px;font-weight:600;">+ File Ground Report</a>
      </div>
    `;

    L.marker([fac.lat, fac.lng], { icon: customMarker }).addTo(map).bindPopup(popupContent);
  });

  // 2. Citizen ground alerts
  state.civicReports.forEach((rep) => {
    if (rep.lat && rep.lng) {
      bounds.push([rep.lat, rep.lng]);
      const alertMarker = L.divIcon({
        className: "custom-alert-pin",
        html: `<div style="background:#ef4444;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:14px;border:2.5px solid white;box-shadow:0 3px 8px rgba(220,38,38,0.5);animation:pulse 1.8s infinite;">⚠️</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const alertPopup = `
        <div style="font-family:sans-serif;min-width:210px;">
          <span style="font-size:10px;font-weight:700;color:#dc2626;">CITIZEN GROUND ALERT</span>
          <h4 style="margin:4px 0 6px;font-size:13px;color:#0f172a;">${rep.issueTitle}</h4>
          <p style="font-size:12px;color:#475569;margin:0 0 6px;">${rep.description}</p>
          <div style="font-size:11px;color:#64748b;">Reported by: <b>${rep.reportedBy}</b> (${rep.district})</div>
          <div style="margin-top:6px;font-size:11px;color:#059669;font-weight:600;">AI Vision Confidence: ${rep.aiConfidence}%</div>
        </div>
      `;

      L.marker([rep.lat, rep.lng], { icon: alertMarker }).addTo(map).bindPopup(alertPopup);
    }
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [30, 30] });
  }

  // Bind basemap switcher events
  const streetsBtn = document.querySelector("#btn-basemap-streets");
  const satelliteBtn = document.querySelector("#btn-basemap-satellite");
  if (streetsBtn && satelliteBtn) {
    streetsBtn.onclick = () => {
      currentBasemap = "streets";
      if (map.hasLayer(satelliteLayer)) map.removeLayer(satelliteLayer);
      streetLayer.addTo(map);
      streetsBtn.classList.add("active");
      satelliteBtn.classList.remove("active");
    };
    satelliteBtn.onclick = () => {
      currentBasemap = "satellite";
      if (map.hasLayer(streetLayer)) map.removeLayer(streetLayer);
      satelliteLayer.addTo(map);
      satelliteBtn.classList.add("active");
      streetsBtn.classList.remove("active");
    };
  }

  // Filter buttons
  document.querySelectorAll("[data-map-filter]").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll("[data-map-filter]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      mountLeafletMap(containerId, btn.dataset.mapFilter);
    };
  });
}

/* ==========================================================================
   Views
   ========================================================================== */

function dashboardView() {
  const facSummary = getFacilitiesSummary();
  const recSummary = getRecommendationsSummary();
  const topAbandonment = [...state.facilities]
    .sort((a, b) => b.abandonmentScore - a.abandonmentScore)
    .slice(0, 5);

  return layout(
    `<div class="page dashboard-page">
      ${pageHeading(
        "Civic Infrastructure Intelligence",
        "Command Center & Delivery Monitor",
        "Combining government public assets and open demographic data with citizen-contributed ground evidence to detect abandonment and recommend actions.",
        `<div style="display:flex;gap:8px;">
          <a class="button amber" href="#/report">+ Report Ground Issue</a>
          <a class="button" href="#/recommendations">View AI Recommendations</a>
        </div>`
      )}

      <div class="stat-grid dashboard-stats">
        <div class="stat status-stat stat-total">
          <span class="stat-label">Public Facilities Tracked</span>
          <div class="stat-value">${facSummary.total}</div>
          <span class="stat-note">Schools, Water, Toilets, Health</span>
        </div>
        <div class="stat status-stat stat-critical">
          <span class="stat-label">At-Risk / Defunct</span>
          <div class="stat-value">${facSummary.atRiskTotal}</div>
          <span class="stat-note">Underutilized or Abandoned</span>
        </div>
        <div class="stat status-stat stat-at-risk">
          <span class="stat-label">Citizen Ground Evidence</span>
          <div class="stat-value">${state.civicReports.length}</div>
          <span class="stat-note">Geotagged citizen reports</span>
        </div>
        <div class="stat status-stat stat-delayed">
          <span class="stat-label">Repair Actions</span>
          <div class="stat-value">${recSummary.repair}</div>
          <span class="stat-note">Immediate interventions</span>
        </div>
        <div class="stat status-stat stat-completed">
          <span class="stat-label">Repurpose Plans</span>
          <div class="stat-value">${recSummary.repurpose}</div>
          <span class="stat-note">Converting disused assets</span>
        </div>
        <div class="stat status-stat stat-on-track">
          <span class="stat-label">New Developments</span>
          <div class="stat-value">${recSummary.newlyDevelop}</div>
          <span class="stat-note">Addressing deficit zones</span>
        </div>
      </div>

      <section class="panel" style="margin-bottom:20px;">
        <div class="panel-heading">
          <div>
            <h2>Geospatial Infrastructure & Alert Map</h2>
            <span class="muted">Interactive GIS layer showing government assets, citizen reports, and satellite imagery</span>
          </div>
          <div class="map-layer-toggles">
            <button id="btn-basemap-streets" class="${currentBasemap === "streets" ? "active" : ""}">Vector Streets</button>
            <button id="btn-basemap-satellite" class="${currentBasemap === "satellite" ? "active" : ""}">Satellite Imagery</button>
          </div>
        </div>
        <div class="map-toolbar">
          <div class="map-layer-toggles">
            <button data-map-filter="all" class="active">All Layers</button>
            <button data-map-filter="school">Schools</button>
            <button data-map-filter="toilet">Public Toilets</button>
            <button data-map-filter="water">Water Plants</button>
            <button data-map-filter="health">Health Clinics</button>
          </div>
          <div class="map-stat-badges">
            <span>🏫 ${state.facilities.filter((f) => f.type === "school").length} Schools</span>
            <span>🚾 ${state.facilities.filter((f) => f.type === "toilet").length} Public Toilets</span>
            <span>💧 ${state.facilities.filter((f) => f.type === "water").length} Water Points</span>
            <span>⚠️ ${state.civicReports.length} Citizen Alerts</span>
          </div>
        </div>
        <div id="gis-leaflet-map" class="leaflet-map-container"></div>
      </section>

      <div class="content-grid" style="grid-template-columns: 1.3fr 0.9fr; gap: 20px;">
        <section class="panel">
          <div class="panel-heading">
            <div>
              <h2>Underutilized & Abandonment Priority Watchlist</h2>
              <span class="muted">Government registered facilities with highest citizen abandonment signals</span>
            </div>
            <a class="text-link" href="#/abandonment">Full detector view →</a>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Facility</th>
                <th>District</th>
                <th>Status</th>
                <th>Risk Score</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              ${topAbandonment
                .map(
                  (f) => `<tr>
                    <td><b>${f.name}</b><br><span class="muted">${f.type} • Catchment: ${f.populationCatchment?.toLocaleString()}</span></td>
                    <td>${f.district}</td>
                    <td>${badge(f.officialStatus)}</td>
                    <td>${abandonmentBadge(f.abandonmentScore)}</td>
                    <td><span class="rec-type-badge badge-${(f.recommendedAction || "repair").toLowerCase()}">${f.recommendedAction || "MAINTAIN"}</span></td>
                  </tr>`
                )
                .join("")}
            </tbody>
          </table>
        </section>

        <section class="panel">
          <div class="panel-heading">
            <div>
              <h2>Recent Ground Evidence Stream</h2>
              <span class="muted">Live citizen uploads & AI validation</span>
            </div>
            <a class="text-link" href="#/report">Submit report</a>
          </div>
          <div class="activity">
            ${state.civicReports
              .slice(0, 4)
              .map(
                (r) => `<div class="activity-item">
                  <span class="activity-dot" style="background:#ef4444;"></span>
                  <div>
                    <p><b>${r.issueTitle}</b> — ${r.facilityName}</p>
                    <span style="font-size:11px;color:#64748b;">${r.description.slice(0, 85)}...</span>
                    <div style="font-size:10px;color:#0d9488;margin-top:2px;">AI Match: ${r.aiConfidence}% confidence • ${r.district}</div>
                  </div>
                </div>`
              )
              .join("")}
          </div>
        </section>
      </div>
    </div>`,
    "dashboard"
  );
}

function mapView() {
  return layout(
    `<div class="page">
      ${pageHeading(
        "Geospatial Intelligence",
        "Interactive Infrastructure GIS & Satellite Map",
        "Pan, zoom, and inspect public assets against satellite imagery, population clusters, and citizen alerts."
      )}
      <section class="panel">
        <div class="map-toolbar">
          <div class="map-layer-toggles">
            <button id="btn-basemap-streets" class="${currentBasemap === "streets" ? "active" : ""}">Vector Streets</button>
            <button id="btn-basemap-satellite" class="${currentBasemap === "satellite" ? "active" : ""}">Satellite Imagery</button>
          </div>
          <div class="map-layer-toggles">
            <button data-map-filter="all" class="active">Show All</button>
            <button data-map-filter="school">Schools</button>
            <button data-map-filter="toilet">Public Toilets</button>
            <button data-map-filter="water">Water Assets</button>
            <button data-map-filter="health">Health Centers</button>
          </div>
        </div>
        <div id="gis-leaflet-map" class="leaflet-map-container" style="height:540px;"></div>
      </section>

      <div class="content-grid" style="margin-top:20px;">
        <section class="panel">
          <div class="panel-heading"><h2>District Infrastructure Coverage</h2></div>
          ${state.demographics
            .map(
              (d) => `<div class="summary-row" style="padding:10px 0;border-bottom:1px solid #edf1f4;">
                <div>
                  <b>${d.district}</b>
                  <span class="muted" style="display:block;font-size:11px;">Population: ${d.population.toLocaleString()} • Density: ${d.density}/km²</span>
                </div>
                <div style="text-align:right;">
                  <b>${d.facilitiesCount} Assets</b>
                  <span class="badge ${d.vulnerabilityIndex > 0.35 ? "red" : "amber"}" style="font-size:10px;">Deficit idx ${d.vulnerabilityIndex}</span>
                </div>
              </div>`
            )
            .join("")}
        </section>

        <section class="panel">
          <div class="panel-heading"><h2>Identified Deficit Hotspots</h2></div>
          <p class="muted" style="font-size:13px;line-height:1.5;">
            Geospatial catchment analysis cross-referencing population density against functional public facilities has identified the following high-priority infrastructure voids:
          </p>
          <ul style="padding-left:18px;font-size:12px;color:#334155;line-height:1.7;">
            <li><b>Guntur West Slum Zone:</b> 13,800 residents with zero functional toilets within 1.8km radius.</li>
            <li><b>Tirupati Outer Ring:</b> 7,500 residents lacking clean piped drinking water.</li>
            <li><b>Visakhapatnam Anandapuram:</b> Healthcare deficit zone requiring new Primary Health Center.</li>
            <li><b>Vijayawada Sector 3:</b> Underutilized school with 8 vacant classrooms suitable for digital library.</li>
          </ul>
        </section>
      </div>
    </div>`,
    "map"
  );
}

function abandonmentView() {
  const facilities = state.facilities;
  return layout(
    `<div class="page">
      ${pageHeading(
        "Infrastructure Underutilization & Abandonment",
        "Public Asset Condition & Abandonment Detector",
        "Detects facilities officially recorded as active that are actually abandoned, locked, or unmaintained based on citizen ground evidence.",
        `<a class="button amber" href="#/report">+ Report Abandoned Facility</a>`
      )}

      <div class="stat-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 20px;">
        <div class="stat"><span class="stat-label">Underutilized Assets</span><div class="stat-value">${facilities.filter((f) => f.officialStatus === "UNDERUTILIZED").length}</div></div>
        <div class="stat"><span class="stat-label">Confirmed Abandoned</span><div class="stat-value">${facilities.filter((f) => f.officialStatus === "ABANDONED").length}</div></div>
        <div class="stat"><span class="stat-label">Defunct / Locked</span><div class="stat-value">${facilities.filter((f) => f.officialStatus === "DEFUNCT").length}</div></div>
        <div class="stat"><span class="stat-label">Population Affected</span><div class="stat-value" style="font-size:20px;">${facilities.reduce((sum, f) => sum + (f.populationCatchment || 0), 0).toLocaleString()}</div></div>
      </div>

      <section class="panel">
        <div class="panel-heading">
          <h2>Monitored Public Facilities Register</h2>
          <span class="muted">${facilities.length} government assets evaluated</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Facility Name</th>
                <th>Type & District</th>
                <th>Official Status</th>
                <th>Risk Score</th>
                <th>Ground Observations & Citizen Feedback</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              ${facilities
                .map(
                  (f) => `<tr>
                    <td><b>${f.name}</b><br><span class="muted">Est. ${f.establishedYear} • Last insp: ${f.lastInspection}</span></td>
                    <td>${f.type.toUpperCase()}<br><span class="muted">${f.district}</span></td>
                    <td>${badge(f.officialStatus)}</td>
                    <td>${abandonmentBadge(f.abandonmentScore)}</td>
                    <td style="max-width:320px;font-size:12px;color:#334155;">
                      ${f.conditionNotes}
                      <div style="margin-top:4px;font-size:11px;color:#dc2626;">📢 ${f.citizenReportCount} citizen reports verified</div>
                    </td>
                    <td>
                      <span class="rec-type-badge badge-${(f.recommendedAction || "repair").toLowerCase()}">${f.recommendedAction || "MAINTAIN"}</span>
                      <div style="font-size:11px;color:#64748b;margin-top:3px;">${f.proposedUse || "Regular maintenance"}</div>
                    </td>
                  </tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>`,
    "abandonment"
  );
}

function recommendationsView() {
  let recs = state.recommendations;
  if (activeRecFilter !== "all") {
    recs = recs.filter((r) => r.type.toLowerCase() === activeRecFilter.toLowerCase());
  }

  return layout(
    `<div class="page">
      ${pageHeading(
        "AI Strategic Decision Engine",
        "Action Recommendations: Repair, Repurpose, or Develop",
        "Synthesizes demographic census data, existing infrastructure records, and ground citizen evidence into actionable civic intervention plans."
      )}

      <div class="map-layer-toggles" style="margin-bottom:18px;">
        <button data-rec-tab="all" class="${activeRecFilter === "all" ? "active" : ""}">All Recommendations (${state.recommendations.length})</button>
        <button data-rec-tab="repair" class="${activeRecFilter === "repair" ? "active" : ""}">🔧 Repair Urgent Infrastructure (${state.recommendations.filter((r) => r.type === "REPAIR").length})</button>
        <button data-rec-tab="repurpose" class="${activeRecFilter === "repurpose" ? "active" : ""}">🔄 Repurpose Abandoned Assets (${state.recommendations.filter((r) => r.type === "REPURPOSE").length})</button>
        <button data-rec-tab="newly_develop" class="${activeRecFilter === "newly_develop" ? "active" : ""}">🏗️ Newly Develop in Deficit Hotspots (${state.recommendations.filter((r) => r.type === "NEWLY_DEVELOP").length})</button>
      </div>

      <div class="rec-grid">
        ${recs
          .map((r) => {
            const badgeClass =
              r.type === "REPAIR"
                ? "badge-repair"
                : r.type === "REPURPOSE"
                ? "badge-repurpose"
                : "badge-develop";
            const icon = r.type === "REPAIR" ? "🔧" : r.type === "REPURPOSE" ? "🔄" : "🏗️";

            return `
            <div class="rec-card">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                  <span class="rec-type-badge ${badgeClass}">${icon} ${r.type.replace("_", " ")}</span>
                  <span class="badge ${r.urgency === "CRITICAL" ? "red" : r.urgency === "HIGH" ? "amber" : "green"}">${r.urgency}</span>
                </div>
                <h3 class="rec-title">${r.targetFacilityName}</h3>
                <span class="rec-district">📍 ${r.district} • Social ROI: <b>${r.roiScore}/10</b></span>
                <p class="rec-rationale">${r.rationale}</p>
                ${r.proposedUse ? `<div style="background:#f0fdf4;border-left:3px solid #16a34a;padding:8px 10px;border-radius:4px;font-size:12px;margin-bottom:12px;"><b>Proposed New Utility:</b> ${r.proposedUse}</div>` : ""}
              </div>

              <div>
                <div class="rec-metrics">
                  <div class="rec-metric-item">
                    <span>Beneficiaries</span>
                    <b>${r.affectedPopulation?.toLocaleString()} ppl</b>
                  </div>
                  <div class="rec-metric-item">
                    <span>Est. Cost</span>
                    <b>${r.estimatedCost}</b>
                  </div>
                  <div class="rec-metric-item">
                    <span>Timeline</span>
                    <b>${r.timelineDays} days</b>
                  </div>
                </div>

                <div style="margin-bottom:12px;">
                  <span style="font-size:11px;font-weight:700;color:#64748b;">KEY ACTION ITEMS:</span>
                  <ul style="padding-left:16px;margin:5px 0 0;font-size:11px;color:#334155;line-height:1.5;">
                    ${r.actionItems.map((item) => `<li>${item}</li>`).join("")}
                  </ul>
                </div>

                <div class="rec-actions">
                  <button class="button ${r.status === "APPROVED_FOR_TENDER" || r.status === "APPROVED_BY_OFFICER" ? "secondary" : "amber"}" data-action="approve-rec" data-rec-id="${r.id}">
                    ${r.status === "APPROVED_BY_OFFICER" ? "✓ Approved by Officer" : r.status === "APPROVED_FOR_TENDER" ? "Approved for Tender" : "Approve Action Plan"}
                  </button>
                </div>
              </div>
            </div>`;
          })
          .join("")}
      </div>
    </div>`,
    "recommendations"
  );
}

function resolutionsView() {
  const resolutions = state.resolutions;
  return layout(
    `<div class="page">
      ${pageHeading(
        "Resolution Verification Studio",
        "Before vs. After Visual Verification",
        "Validates that civic works, repairs, and facility unlocks reported as completed are verified by visual AI comparison and field sign-offs."
      )}

      <div class="resolution-grid">
        ${resolutions
          .map(
            (res) => `
            <div class="resolution-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                  <span style="font-size:11px;color:#64748b;font-weight:700;">${res.district}</span>
                  <h3 style="margin:3px 0 6px;font-size:15px;color:#0f172a;">${res.facilityName}</h3>
                </div>
                <span class="badge green">VERIFIED</span>
              </div>
              <p style="font-size:12px;color:#475569;margin:0 0 10px;">Issue: <b>${res.issueReported}</b></p>

              <div class="comparison-container">
                <div class="comparison-box">
                  <div class="comparison-label">BEFORE REPAIR</div>
                  <img src="${res.beforeImage}" alt="Before evidence">
                  <div style="font-size:10px;padding:4px;color:#64748b;">Reported by ${res.reportedBy}</div>
                </div>
                <div class="comparison-box">
                  <div class="comparison-label after">AFTER RESOLUTION</div>
                  <img src="${res.afterImage}" alt="After resolution">
                  <div style="font-size:10px;padding:4px;color:#059669;font-weight:600;">Resolved by ${res.resolvedBy}</div>
                </div>
              </div>

              <div class="ai-verification-badge">
                <span>🤖 AI Visual Verification Score</span>
                <span style="font-size:14px;color:#047857;">${res.aiVerificationScore}% Match</span>
              </div>
              <p style="font-size:11px;color:#334155;margin:8px 0 0;line-height:1.4;">${res.aiInspectionReport}</p>
            </div>`
          )
          .join("")}
      </div>
    </div>`,
    "resolutions"
  );
}

function reportView() {
  return layout(
    `<div class="page">
      ${pageHeading(
        "Citizen Ground Evidence Portal",
        "Report Facility Issue or Abandonment",
        "Upload geotagged photos or videos to report locked facilities, abandoned schools, defunct water kiosks, or structural damage."
      )}

      <div class="stepper">
        <span class="active">1 Quick Issue Tag</span>
        <span>2 Match Facility</span>
        <span>3 Photo / Video Evidence</span>
        <span>4 Submit & Verify</span>
      </div>

      <div class="form-layout">
        <form class="form-panel" id="citizen-evidence-form">
          <h2>Report Ground Evidence</h2>

          <div class="field">
            <label>Select Issue Category</label>
            <div class="category-pills" id="category-pills-container">
              <button type="button" class="category-pill selected" data-issue="LOCKED_TOILET">🚾 Locked Public Toilet</button>
              <button type="button" class="category-pill" data-issue="ABANDONED_SCHOOL">🏫 Abandoned School</button>
              <button type="button" class="category-pill" data-issue="DEFUNCT_WATER">💧 Defunct Water Plant</button>
              <button type="button" class="category-pill" data-issue="DEFUNCT_FACILITY">⚠️ Non-Functional Facility</button>
              <button type="button" class="category-pill" data-issue="DAMAGED_INFRASTRUCTURE">🚧 Damaged Road / Culvert</button>
            </div>
            <input type="hidden" id="selected-issue-type" value="LOCKED_TOILET">
          </div>

          <div class="field">
            <label for="project-search">Associated Public Facility</label>
            <input id="project-search" list="facility-options" required placeholder="Type or select a registered government facility...">
            <datalist id="facility-options">
              ${state.facilities
                .map((f) => `<option value="${f.name}">${f.type.toUpperCase()} • ${f.district} (${f.officialStatus})</option>`)
                .join("")}
            </datalist>
            <div id="project-info" class="selection-info">Select a facility or let GPS find the nearest government asset.</div>
          </div>

          <div class="field">
            <label for="evidence-file">Photo or Video Evidence</label>
            <div class="upload upload-active">
              <strong>Drop files here or choose from this device</strong>
              <span>JPG, PNG, WEBP, MP4 up to 25 MB</span>
              <input id="evidence-file" type="file" accept="image/*,video/*" multiple required>
              <div id="evidence-preview" class="evidence-preview"></div>
              <p id="evidence-error" class="form-error" hidden>Please add at least one photo or video before continuing.</p>
            </div>
          </div>

          <div class="field">
            <label>Geolocation (GPS Coordinates)</label>
            <div class="location-box">
              <strong id="location-status">Location ready</strong>
              <span id="location-value">Using Andhra Pradesh default or device GPS</span>
              <div class="location-fields">
                <input id="latitude" type="number" step="any" placeholder="Latitude" value="16.5123">
                <input id="longitude" type="number" step="any" placeholder="Longitude" value="80.6214">
              </div>
              <button class="button secondary" type="button" data-action="locate">📍 Auto-Detect My Current GPS</button>
            </div>
          </div>

          <div class="field">
            <label for="description">Ground Observation / Issue Description <span class="muted">(min 20 chars)</span></label>
            <textarea id="description" required placeholder="Describe what is wrong: e.g. This toilet has been padlocked for 6 months, no water supply, weeds overgrown..."></textarea>
            <div class="character-count"><span id="description-count">0</span>/500</div>
            <p id="description-error" class="form-error" hidden>Please enter at least 20 characters describing the condition.</p>
          </div>

          <button class="button full" type="submit" style="margin-top:14px;font-size:14px;padding:12px;">Submit Ground Evidence</button>
          <p id="submit-error" class="form-error" hidden>There was a problem submitting your report. Please try again.</p>
        </form>

        <aside class="form-panel">
          <h2>How AI Evaluates Your Report</h2>
          <div class="summary">
            <b>1. Proximity Cross-Referencing</b>
            <p class="muted" style="font-size:12px;margin:5px 0 0">Your GPS coordinates are matched against the official Government Infrastructure Registry to pinpoint the exact asset ID.</p>
          </div>
          <div class="summary">
            <b>2. Vision AI Deterioration Analysis</b>
            <p class="muted" style="font-size:12px;margin:5px 0 0">Visual models inspect your photo for rusted padlocks, broken glass, vegetation overgrowth, and dry taps to calculate an Abandonment Score.</p>
          </div>
          <div class="summary">
            <b>3. Policy Recommendation Matrix</b>
            <p class="muted" style="font-size:12px;margin:5px 0 0">Verified reports automatically route into District Works planning for urgent <b>Repair</b> or community <b>Repurposing</b>.</p>
          </div>
        </aside>
      </div>
    </div>`,
    "report"
  );
}

function confirmationView() {
  const submission = latestSubmission || state.civicReports[0];
  return layout(
    `<div class="page">
      <div class="confirmation">
        <section class="panel">
          <div class="check">✓</div>
          <div class="eyebrow">Ground Report Received</div>
          <h1>Thank you for your civic contribution</h1>
          <p class="subhead">Your evidence has been geotagged and cross-referenced with the Government Infrastructure Registry.</p>
          <div class="summary" style="text-align:left;margin:25px 0">
            <div class="summary-row"><span>Reference ID</span><b>${submission?.id || "CIV-2026-8941"}</b></div>
            <div class="summary-row"><span>Asset</span><b>${submission?.facilityName || submission?.project || "Public Facility"}</b></div>
            <div class="summary-row"><span>Status</span><b>${badge("Confirmed Issue")}</b></div>
            <div class="summary-row"><span>AI Verification</span><b>${submission?.aiConfidence || 92}% Confidence</b></div>
          </div>
          <div style="display:flex;gap:10px;justify-content:center;">
            <a class="button" href="#/map">View on GIS Map</a>
            <a class="button secondary" href="#/recommendations">View AI Recommendations</a>
          </div>
        </section>
      </div>
    </div>`,
    "submissions"
  );
}

function projectsView() {
  return layout(
    `<div class="page">
      ${pageHeading("Government workspace", "Capital Works Register", "Track construction and maintenance projects against planned schedules.", `<button class="button amber" data-action="toast">+ Add project</button>`)}
      <section class="panel">
        <div class="panel-heading"><h2>Project Register <span class="muted">(${getProjects().length})</span></h2></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th>Project</th><th>Progress</th><th>Status</th><th>Officer</th><th>Updated</th></tr>
            </thead>
            <tbody>
              ${getProjects()
                .map(
                  (p) =>
                    `<tr><td><a class="text-link" href="#/projects/${p.id}">${p.name}</a><br><span class="muted">${p.category} / ${p.location}</span></td><td>${p.actualProgress}% / ${p.plannedProgress}% planned</td><td>${badge(p.status)}</td><td>${p.assignedOfficer}</td><td>${p.updated}</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>`,
    "projects"
  );
}

async function detailView(id) {
  const project = getProject(id) || getProjects()[0];
  if (!project) return layout("<div class='page'><p class='muted'>Project not found.</p></div>", "projects");

  return layout(
    `<div class="page">
      ${pageHeading("Project details", project.name, `${project.category} / ${project.location}`, `<a class="button secondary" href="#/projects">Back to projects</a>`)}
      <div class="hero-strip">
        <div>
          <h2>${["At Risk", "Delayed", "Critical"].includes(project.status) ? "Schedule variance detected" : "Work is progressing"}</h2>
          <p>Last field update ${project.updated}. Assigned to ${project.assignedOfficer}.</p>
        </div>
        <button class="button amber" data-action="toast">Update status</button>
      </div>
      <div class="stat-grid">
        <div class="stat"><span class="stat-label">Planned progress</span><div class="stat-value">${project.plannedProgress}%</div></div>
        <div class="stat"><span class="stat-label">Actual progress</span><div class="stat-value">${project.actualProgress}%</div></div>
        <div class="stat"><span class="stat-label">AI confidence</span><div class="stat-value">${project.aiConfidence || 89}%</div></div>
        <div class="stat"><span class="stat-label">Budget</span><div class="stat-value" style="font-size:21px">${project.budget}</div></div>
      </div>
    </div>`,
    "projects"
  );
}

function analyticsView() {
  return layout(
    `<div class="page">
      ${pageHeading("Demographics & Performance", "District Infrastructure Analytics", "Demographic census overlay and civic condition metrics across districts.")}
      <div class="content-grid">
        <section class="panel">
          <div class="panel-heading"><h2>District Demographics & Deficit Indices</h2></div>
          <table class="data-table">
            <thead>
              <tr><th>District</th><th>Population</th><th>Density / km²</th><th>Tracked Assets</th><th>Vulnerability Index</th></tr>
            </thead>
            <tbody>
              ${state.demographics
                .map(
                  (d) =>
                    `<tr><td><b>${d.district}</b></td><td>${d.population.toLocaleString()}</td><td>${d.density}</td><td>${d.facilitiesCount}</td><td>${badge(d.vulnerabilityIndex > 0.35 ? "High deficit" : "Moderate")}</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        </section>
        <section class="panel">
          <div class="panel-heading"><h2>AI Intelligence Summary</h2></div>
          ${[
            ["Facilities Analyzed", `${state.facilities.length}`],
            ["Identified for Repurposing", `${state.recommendations.filter((r) => r.type === "REPURPOSE").length}`],
            ["Urgent Repair Interventions", `${state.recommendations.filter((r) => r.type === "REPAIR").length}`],
            ["New Infrastructure Proposals", `${state.recommendations.filter((r) => r.type === "NEWLY_DEVELOP").length}`],
            ["Total Citizens Benefited", `${state.recommendations.reduce((s, r) => s + (r.affectedPopulation || 0), 0).toLocaleString()}`],
          ]
            .map(([label, value]) => `<div class="summary-row"><span>${label}</span><b>${value}</b></div>`)
            .join("")}
        </section>
      </div>
    </div>`,
    "analytics"
  );
}

/* ==========================================================================
   Routing & Event Binding
   ========================================================================== */

async function viewForHash(hash) {
  if (role === "citizen" && hash === "#/dashboard") {
    location.hash = "#/report";
    return;
  }
  if (hash === "#/report") return reportView();
  if (hash === "#/submissions") return confirmationView();
  if (hash === "#/map") return mapView();
  if (hash === "#/abandonment") return abandonmentView();
  if (hash === "#/recommendations") return recommendationsView();
  if (hash === "#/resolutions") return resolutionsView();
  if (hash === "#/projects") return projectsView();
  if (hash === "#/analytics") return analyticsView();
  if (hash.startsWith("#/projects/")) return await detailView(hash.split("/")[2]);
  return dashboardView();
}

async function render() {
  const hash = location.hash || "#/dashboard";
  app.innerHTML = `<div class="page"><p class="muted">Loading CiviSight…</p></div>`;
  let view;
  try {
    view = await viewForHash(hash);
  } catch (err) {
    view = layout(`<div class="page"><p class="form-error">Error: ${err.message}</p></div>`, "");
  }
  if (view) {
    app.innerHTML = view;
  }
  bindGlobalEvents();

  if (hash === "#/dashboard" || hash === "#/map") {
    setTimeout(() => mountLeafletMap("gis-leaflet-map"), 50);
  }
  if (hash === "#/report") bindCitizenEvents();
  if (hash === "#/recommendations") bindRecommendationEvents();
}

function bindGlobalEvents() {
  document.querySelectorAll("[data-role]").forEach((button) => {
    button.addEventListener("click", () => {
      role = button.dataset.role;
      location.hash = role === "citizen" ? "#/report" : "#/dashboard";
    });
  });

  document.querySelectorAll("[data-action='toast']").forEach((button) => {
    button.addEventListener("click", () => {
      button.textContent = "Saved";
      setTimeout(() => {
        button.textContent = "Done";
      }, 900);
    });
  });
}

function bindRecommendationEvents() {
  document.querySelectorAll("[data-rec-tab]").forEach((btn) => {
    btn.onclick = () => {
      activeRecFilter = btn.dataset.recTab;
      render();
    };
  });

  document.querySelectorAll("[data-action='approve-rec']").forEach((btn) => {
    btn.onclick = async () => {
      const recId = btn.dataset.recId;
      await recommendationsApi.approveRecommendation(recId);
      btn.textContent = "✓ Approved by Officer";
      btn.classList.remove("amber");
      btn.classList.add("secondary");
    };
  });
}

function bindCitizenEvents() {
  const form = document.querySelector("#citizen-evidence-form");
  const facilityInput = document.querySelector("#project-search");
  const projectInfo = document.querySelector("#project-info");
  const fileInput = document.querySelector("#evidence-file");
  const preview = document.querySelector("#evidence-preview");
  const description = document.querySelector("#description");
  const count = document.querySelector("#description-count");
  const evidenceError = document.querySelector("#evidence-error");
  const descriptionError = document.querySelector("#description-error");
  const locateButton = document.querySelector("[data-action='locate']");
  const issueTypeInput = document.querySelector("#selected-issue-type");

  let files = [];

  // Category pill selection
  document.querySelectorAll(".category-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".category-pill").forEach((p) => p.classList.remove("selected"));
      pill.classList.add("selected");
      issueTypeInput.value = pill.dataset.issue;
    });
  });

  function selectedFacility() {
    return state.facilities.find((f) => f.name.toLowerCase() === facilityInput.value.toLowerCase().trim()) || null;
  }

  function renderFacilityInfo() {
    const fac = selectedFacility();
    if (fac) {
      projectInfo.innerHTML = `<strong>${fac.name}</strong><span>${fac.type.toUpperCase()} • ${fac.district} • Status: <b>${fac.officialStatus}</b></span>`;
      document.querySelector("#latitude").value = fac.lat;
      document.querySelector("#longitude").value = fac.lng;
    } else {
      projectInfo.innerHTML = "Select a facility or let GPS find the nearest registered government asset.";
    }
  }

  function renderPreview() {
    preview.innerHTML = files
      .map(
        (file, index) =>
          `<div class="evidence-item">
            <div class="media-preview">${file.type.startsWith("video/") ? `<video src="${URL.createObjectURL(file)}" controls></video>` : `<img src="${URL.createObjectURL(file)}" alt="Evidence">`}</div>
            <span>${file.name}</span>
            <button type="button" data-remove-file="${index}">Remove</button>
          </div>`
      )
      .join("");

    preview.querySelectorAll("[data-remove-file]").forEach((button) => {
      button.addEventListener("click", () => {
        files.splice(Number(button.dataset.removeFile), 1);
        renderPreview();
      });
    });
  }

  function addFiles(fileList) {
    files = [...files, ...[...fileList].filter((f) => f.type.startsWith("image/") || f.type.startsWith("video/"))].slice(0, 5);
    if (evidenceError) evidenceError.hidden = files.length > 0;
    renderPreview();
  }

  facilityInput.addEventListener("input", renderFacilityInfo);
  fileInput.addEventListener("change", () => addFiles(fileInput.files));

  description.addEventListener("input", () => {
    count.textContent = description.value.length;
    descriptionError.hidden = description.value.length === 0 || description.value.length >= 20;
  });

  locateButton.addEventListener("click", () => {
    const status = document.querySelector("#location-status");
    const value = document.querySelector("#location-value");

    if (!navigator.geolocation) {
      status.textContent = "GPS Unavailable";
      return;
    }

    status.textContent = "Detecting GPS...";
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(4));
        const lng = Number(pos.coords.longitude.toFixed(4));
        document.querySelector("#latitude").value = lat;
        document.querySelector("#longitude").value = lng;
        status.textContent = "GPS Locked";
        value.textContent = `${lat} N, ${lng} E`;

        // Match nearest facility
        let closest = null;
        let minDist = Infinity;
        state.facilities.forEach((f) => {
          const dist = Math.hypot(f.lat - lat, f.lng - lng);
          if (dist < minDist) {
            minDist = dist;
            closest = f;
          }
        });
        if (closest && minDist < 0.2) {
          facilityInput.value = closest.name;
          renderFacilityInfo();
        }
      },
      () => {
        status.textContent = "Manual location used";
      }
    );
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (description.value.length < 20) {
      descriptionError.hidden = false;
      description.focus();
      return;
    }

    const submitBtn = form.querySelector("button[type='submit']");
    submitBtn.disabled = true;
    submitBtn.textContent = "Analyzing & Submitting...";

    try {
      const fac = selectedFacility();
      const payload = {
        facilityId: fac ? fac.id : null,
        facilityName: fac ? fac.name : facilityInput.value || "Reported Location Asset",
        issueType: issueTypeInput.value,
        issueTitle: description.value.slice(0, 45),
        district: fac ? fac.district : "Andhra Pradesh",
        lat: Number(document.querySelector("#latitude").value) || 16.5,
        lng: Number(document.querySelector("#longitude").value) || 80.6,
        description: description.value,
        reportedBy: "Citizen Ground Contributor",
      };

      latestSubmission = await civicReportsApi.submitReport(payload);
      location.hash = "#/submissions";
    } catch (err) {
      console.error(err);
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Ground Evidence";
    }
  });
}

window.addEventListener("hashchange", render);

async function bootstrap() {
  app.innerHTML = `<div class="page"><p class="muted">Loading CivicSight…</p></div>`;
  // Resilient load
  try {
    await projectsApi.loadProjects();
  } catch (err) {
    console.warn("Live projects backend offline, using mock state:", err);
  }
  await render();
}

bootstrap();
