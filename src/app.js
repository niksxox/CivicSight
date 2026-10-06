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
  dataGovApi,
  DATA_GOV_CATALOGS,
  authApi,
  GOV_ROLES,
  DEMO_CREDENTIALS,
} from "./services/index.js";

const app = document.querySelector("#app");
let currentUser = authApi.getCurrentUser();
let role = authApi.isGovernment() ? "officer" : "citizen";
let latestSubmission = state.reports[0] || null;
let latestAnalysis = null;
let activeMapInstance = null;
let currentBasemap = "streets"; // "streets" | "satellite"
let activeFilter = "all";
let activeRecFilter = "all";
let activeRegion = "all";

export const INDIA_REGIONS = [
  { id: "all", label: "All India", coords: [21.7679, 78.8718], zoom: 5 },
  { id: "delhi", label: "Delhi NCR", coords: [28.6139, 77.2090], zoom: 11 },
  { id: "maharashtra", label: "Maharashtra (Mumbai)", coords: [19.0760, 72.8777], zoom: 11 },
  { id: "karnataka", label: "Karnataka (Bengaluru)", coords: [12.9716, 77.5946], zoom: 11 },
  { id: "tamilnadu", label: "Tamil Nadu (Chennai)", coords: [13.0827, 80.2707], zoom: 11 },
  { id: "telangana", label: "Telangana (Hyderabad)", coords: [17.3850, 78.4867], zoom: 11 },
  { id: "up", label: "Uttar Pradesh (Varanasi)", coords: [25.3176, 82.9739], zoom: 11 },
  { id: "bengal", label: "West Bengal (Kolkata)", coords: [22.5726, 88.3639], zoom: 11 },
  { id: "gujarat", label: "Gujarat (Ahmedabad)", coords: [23.0225, 72.5714], zoom: 11 },
  { id: "rajasthan", label: "Rajasthan (Jaipur)", coords: [26.9124, 75.7873], zoom: 11 },
  { id: "ap", label: "Andhra Pradesh", coords: [16.5062, 80.6480], zoom: 8 },
];

const officerNav = [
  ["Command center", "dashboard", "#/dashboard"],
  ["GIS satellite map", "map", "#/map"],
  ["Abandonment detector", "abandonment", "#/abandonment"],
  ["Recommendations", "recommendations", "#/recommendations"],
  ["Data.gov.in Real-Time", "datagov", "#/data-gov"],
  ["Resolution studio", "verify", "#/resolutions"],
  ["Capital projects", "projects", "#/projects"],
  ["Demographics & indices", "analytics", "#/analytics"],
];

const citizenNav = [
  ["Report civic issue", "capture", "#/report"],
  ["Civic map & alerts", "map", "#/map"],
  ["Recommendations", "recommendations", "#/recommendations"],
  ["Verified resolutions", "verify", "#/resolutions"],
  ["My submissions", "evidence", "#/submissions"],
  ["Official login", "login", "#/login"],
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
  currentUser = authApi.getCurrentUser();
  const isGov = authApi.isGovernment();
  const nav = isGov && role === "officer" ? officerNav : citizenNav;

  return `<div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="${isGov ? "#/dashboard" : "#/report"}">
        <span class="brand-mark"><span>+</span></span>
        <span><strong>CivicSight</strong><small>Civic Infrastructure Platform</small></span>
      </a>

      <!-- Profile & Hierarchy Badge -->
      ${
        isGov
          ? `<div class="user-profile-badge" style="background:#0f172a;border:1px solid #334155;border-radius:6px;padding:9px 12px;margin:8px 12px;color:white;">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <span class="badge ${currentUser.badgeColor || "green"}" style="font-size:9px;padding:2px 6px;">${currentUser.level}</span>
                <button id="btn-sidebar-signout" style="background:transparent;border:none;color:#94a3b8;font-size:10px;cursor:pointer;padding:0;" title="Sign Out">Sign Out ↗</button>
              </div>
              <div style="font-size:12px;font-weight:700;margin-top:5px;color:#f8fafc;">${currentUser.name}</div>
              <div style="font-size:10px;color:#94a3b8;line-height:1.3;margin-top:2px;">${currentUser.designation}</div>
              <div style="font-size:9px;color:#38bdf8;margin-top:4px;">Approval limit: ${currentUser.approvalLimit}</div>
            </div>`
          : `<div class="user-profile-badge" style="background:#f1f5f9;border:1px solid #cbd5e1;border-radius:6px;padding:9px 12px;margin:8px 12px;">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <span class="badge" style="font-size:9px;background:#e2e8f0;color:#334155;padding:2px 6px;">Public Citizen</span>
                <a href="#/login" style="font-size:11px;color:#0284c7;font-weight:700;text-decoration:none;">Officer Login →</a>
              </div>
              <div style="font-size:10px;color:#64748b;margin-top:4px;line-height:1.4;">Submit ground evidence & track civic issues. Tenders require official credentials.</div>
            </div>`
      }

      <div class="role-switcher">
        <button class="${!isGov || role === "citizen" ? "active" : ""}" data-role="citizen">Citizen portal</button>
        <button class="${isGov && role === "officer" ? "active" : ""}" data-role="officer">${isGov ? "Government" : "Gov Login"}</button>
      </div>

      <div class="nav-label">Workspace</div>
      <nav class="nav">${nav
        .map(
          ([label, icon, href]) =>
            `<a class="${currentRoute === href.slice(2) ? "active" : ""}" href="${href}">${label}</a>`
        )
        .join("")}</nav>
      <div class="sidebar-footer">
        <strong>${isGov ? "Government Administration" : "Community Reporting"}</strong>
        ${isGov ? `${currentUser.department}` : "Community reporting across Indian states"}
      </div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="breadcrumb">CivicSight / <b>${isGov ? `Official Command Center (${currentUser.level})` : "Public Citizen Contributor"}</b></div>
        <div class="top-actions">
          ${isGov ? `<span class="badge ${currentUser.badgeColor || "green"}" style="font-size:11px;">${currentUser.level}</span>` : `<span class="badge" style="font-size:11px;">CITIZEN</span>`}
          <span class="avatar">${isGov ? "GOV" : "CIT"}</span>
        </div>
      </header>
      ${content}
    </main>
  </div>`;
}

function unauthorizedView(requestedRoute) {
  return layout(
    `<div class="page">
      <div class="panel" style="max-width:680px;margin:40px auto;text-align:center;padding:40px 24px;">
        <div class="eyebrow" style="color:#dc2626;font-weight:700;">Restricted Government Access</div>
        <h1 style="font-size:24px;margin:8px 0 12px;color:#0f172a;">Official Authorization Required</h1>
        <p class="subhead" style="margin-bottom:20px;font-size:14px;color:#475569;line-height:1.6;">
          You are currently in <b>Citizen Contributor Mode</b>. The requested section (<code>${requestedRoute}</code>) contains confidential public asset expenditure registers, internal abandonment audits, and inter-departmental sanction workflows accessible exclusively to authorized Government Authorities.
        </p>
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;text-align:left;margin-bottom:24px;font-size:12px;color:#334155;line-height:1.6;">
          <b style="color:#0f172a;display:block;margin-bottom:6px;">Restricted Officer Hierarchies:</b>
          <div>• <b>District Officer (DUDA):</b> Local asset repairs & field verification sign-offs</div>
          <div>• <b>State Administrator (MA&UD):</b> State-wide facility repurposing & budget reallocations</div>
          <div>• <b>National Director (MoHUA):</b> New capital infrastructure sanctions & real-time Data.gov.in API pipelines</div>
        </div>
        <div style="display:flex;gap:12px;justify-content:center;">
          <a class="button amber" href="#/login">Login with Government Credentials</a>
          <a class="button secondary" href="#/report">Return to Citizen Portal</a>
        </div>
      </div>
    </div>`,
    ""
  );
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

  // Pan-India default center
  const map = L.map(containerId).setView([21.7679, 78.8718], 5);
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

  // 1. Facilities across India
  state.facilities.forEach((fac) => {
    if (filterType !== "all" && filterType !== fac.type) return;
    bounds.push([fac.lat, fac.lng]);

    let color = "#2563eb";
    let iconChar = "F";
    if (fac.type === "school") {
      color = "#7c3aed";
      iconChar = "S";
    } else if (fac.type === "toilet") {
      color = "#d97706";
      iconChar = "T";
    } else if (fac.type === "water") {
      color = "#0284c7";
      iconChar = "W";
    } else if (fac.type === "health") {
      color = "#059669";
      iconChar = "H";
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
      <div style="font-family:sans-serif;min-width:230px;">
        <span style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;">${fac.district}${fac.state ? ` (${fac.state})` : ""} • ${fac.type}</span>
        <h4 style="margin:4px 0 6px;font-size:14px;color:#0f172a;">${fac.name}</h4>
        <div style="margin-bottom:8px;">
          ${badge(fac.officialStatus)}
          ${abandonmentBadge(fac.abandonmentScore)}
        </div>
        <p style="font-size:12px;color:#334155;margin:0 0 8px;line-height:1.4;">${fac.conditionNotes}</p>
        <div style="background:#f8fafc;padding:6px 8px;border-radius:4px;font-size:11px;color:#475569;margin-bottom:8px;">
          <div>Catchment: <b>${fac.populationCatchment?.toLocaleString()} residents</b></div>
          <div>Citizen ground alerts: <b>${fac.citizenReportCount} reports</b></div>
          ${fac.recommendedAction ? `<div>Recommendation: <b>${fac.recommendedAction}</b></div>` : ""}
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
        html: `<div style="background:#ef4444;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:14px;border:2.5px solid white;box-shadow:0 3px 8px rgba(220,38,38,0.5);animation:pulse 1.8s infinite;">!</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const alertPopup = `
        <div style="font-family:sans-serif;min-width:210px;">
          <span style="font-size:10px;font-weight:700;color:#dc2626;">CITIZEN GROUND ALERT</span>
          <h4 style="margin:4px 0 6px;font-size:13px;color:#0f172a;">${rep.issueTitle}</h4>
          <p style="font-size:12px;color:#475569;margin:0 0 6px;">${rep.description}</p>
          <div style="font-size:11px;color:#64748b;">Reported by: <b>${rep.reportedBy}</b> (${rep.district})</div>
          <div style="margin-top:6px;font-size:11px;color:#059669;font-weight:600;">Verification confidence: ${rep.aiConfidence}%</div>
        </div>
      `;

      L.marker([rep.lat, rep.lng], { icon: alertMarker }).addTo(map).bindPopup(alertPopup);
    }
  });

  if (activeRegion === "all" && bounds.length > 0) {
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

  // Region switcher
  document.querySelectorAll("[data-region-jump]").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll("[data-region-jump]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeRegion = btn.dataset.regionJump;
      const reg = INDIA_REGIONS.find((r) => r.id === activeRegion);
      if (reg) {
        if (reg.id === "all" && bounds.length > 0) {
          map.fitBounds(bounds, { padding: [30, 30] });
        } else {
          map.flyTo(reg.coords, reg.zoom, { duration: 1.2 });
        }
      }
    };
  });

  // Dynamic OpenStreetMap Overpass live data fetcher button
  const liveOsmBtn = document.querySelector("#btn-fetch-live-osm");
  if (liveOsmBtn) {
    liveOsmBtn.onclick = async () => {
      liveOsmBtn.disabled = true;
      liveOsmBtn.textContent = "⏳ Fetching Live OSM Nodes...";
      const b = map.getBounds();
      const bbox = [b.getSouth(), b.getWest(), b.getNorth(), b.getEast()];
      const activeRegObj = INDIA_REGIONS.find((r) => r.id === activeRegion);
      const regName = activeRegObj ? activeRegObj.label : "India";
      const newItems = await facilitiesApi.fetchLiveOsmFacilities(bbox, regName);
      liveOsmBtn.textContent = `✓ Added ${newItems.length} Live Assets (${regName})`;
      setTimeout(() => {
        liveOsmBtn.disabled = false;
        liveOsmBtn.textContent = "Load Live Facility Data";
      }, 3000);
      mountLeafletMap(containerId, activeFilter);
    };
  }

  // Filter buttons
  document.querySelectorAll("[data-map-filter]").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll("[data-map-filter]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeFilter = btn.dataset.mapFilter;
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
    .slice(0, 4);

  return layout(
    `<div class="page dashboard-page">
      ${pageHeading(
        "National Civic Infrastructure Monitor",
        "Command Center (All India)",
        "Combining government public asset registers and census demographics with citizen ground evidence to detect abandonment and recommend actions across Indian States.",
        `<div style="display:flex;gap:8px;">
          <a class="button amber" href="#/report">+ Report Ground Issue</a>
          <a class="button" href="#/recommendations">View Recommendations</a>
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
      </div>

      <section class="panel" style="margin-bottom:20px;">
        <div class="panel-heading">
          <div>
            <h2>Infrastructure & Alert Map</h2>
            <span class="muted">Government assets, citizen reports, and basemap imagery across Indian states</span>
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
            <button id="btn-fetch-live-osm" style="background:#0284c7;color:white;border-color:#0284c7;font-weight:700;">Load Live Facility Data</button>
          </div>
          <div class="map-stat-badges">
            <span>${state.facilities.filter((f) => f.type === "school").length} Schools</span>
            <span>${state.facilities.filter((f) => f.type === "toilet").length} Toilets</span>
            <span>${state.facilities.filter((f) => f.type === "water").length} Water</span>
            <span>${state.civicReports.length} Alerts</span>
          </div>
        </div>
        <div class="map-layer-toggles region-selector-strip" style="margin: 8px 14px 4px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center;">
          <span style="font-size:11px;font-weight:700;color:#64748b;margin-right:2px;">Region:</span>
          ${INDIA_REGIONS.map(
            (reg) => `<button data-region-jump="${reg.id}" class="${activeRegion === reg.id ? "active" : ""}" style="font-size:11px;padding:3px 8px;">${reg.label}</button>`
          ).join("")}
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
                <th>District & State</th>
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
                    <td>${f.district}${f.state ? `<br><small style="color:#0d9488;">${f.state}</small>` : ""}</td>
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
              <span class="muted">Recent citizen uploads with verification scores</span>
            </div>
            <a class="text-link" href="#/report">Submit report</a>
          </div>
          <div class="activity">
            ${state.civicReports
              .slice(0, 3)
              .map(
                (r) => `<div class="activity-item">
                  <span class="activity-dot" style="background:#ef4444;"></span>
                  <div>
                    <p><b>${r.issueTitle}</b> — ${r.facilityName}</p>
                    <span style="font-size:11px;color:#64748b;">${r.description.slice(0, 85)}...</span>
                    <div style="font-size:10px;color:#0d9488;margin-top:2px;">${r.aiConfidence}% confidence • ${r.district}</div>
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
        "Geospatial Map",
        "Infrastructure GIS & Satellite Map",
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
            <button id="btn-fetch-live-osm" style="background:#0284c7;color:white;border-color:#0284c7;font-weight:700;">Load Live Facility Data</button>
          </div>
        </div>
        <div class="map-layer-toggles region-selector-strip" style="margin: 8px 14px 4px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center;">
          <span style="font-size:11px;font-weight:700;color:#64748b;margin-right:2px;">Region:</span>
          ${INDIA_REGIONS.map(
            (reg) => `<button data-region-jump="${reg.id}" class="${activeRegion === reg.id ? "active" : ""}" style="font-size:11px;padding:3px 8px;">${reg.label}</button>`
          ).join("")}
        </div>
        <div id="gis-leaflet-map" class="leaflet-map-container" style="height:540px;"></div>
      </section>

      <div class="content-grid" style="margin-top:20px;">
        <section class="panel">
          <div class="panel-heading"><h2>State & District Infrastructure Coverage</h2></div>
          ${state.demographics
            .slice(0, 6)
            .map(
              (d) => `<div class="summary-row" style="padding:10px 0;border-bottom:1px solid #edf1f4;">
                <div>
                  <b>${d.district}</b> <span style="font-size:11px;color:#0d9488;font-weight:600;">(${d.state || "India"})</span>
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
          <div class="panel-heading"><h2>National Deficit Hotspots</h2></div>
          <p class="muted" style="font-size:13px;line-height:1.5;">
            Areas with high population density and limited functional public facilities:
          </p>
          <ul style="padding-left:18px;font-size:12px;color:#334155;line-height:1.7;">
            <li><b>Mumbai Dharavi Sector 5 (Maharashtra):</b> 28,000 residents living beyond 800m of functional sanitation.</li>
            <li><b>Varanasi Adampur Slum Cluster (UP):</b> 14,000 handloom artisans lacking clean piped RO drinking water.</li>
            <li><b>Central Delhi Narela Sub-city (Delhi):</b> Vacant 10-room school suitable for Maternal & Child Health conversion.</li>
            <li><b>Bengaluru Peenya 2nd Stage (Karnataka):</b> Garment industrial cluster needing worker creche & health sub-center.</li>
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
        "Public Asset Condition & Abandonment Register",
        "Detects facilities officially recorded as active that are actually abandoned, locked, or unmaintained based on citizen ground evidence across Indian States.",
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
          <h2>Monitored Public Facilities Register (All India)</h2>
          <span class="muted">Showing top 10 of ${facilities.length} government assets evaluated across States</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Facility Name</th>
                <th>Type, District & State</th>
                <th>Official Status</th>
                <th>Risk Score</th>
                <th>Ground Observations & Citizen Feedback</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              ${[...facilities]
                .sort((a, b) => b.abandonmentScore - a.abandonmentScore)
                .slice(0, 10)
                .map(
                  (f) => `<tr>
                    <td><b>${f.name}</b><br><span class="muted">Est. ${f.establishedYear} • Last insp: ${f.lastInspection}</span></td>
                    <td>${f.type.toUpperCase()}<br><span class="muted">${f.district}${f.state ? ` (${f.state})` : ""}</span></td>
                    <td>${badge(f.officialStatus)}</td>
                    <td>${abandonmentBadge(f.abandonmentScore)}</td>
                    <td style="max-width:320px;font-size:12px;color:#334155;">
                      ${f.conditionNotes}
                      <div style="margin-top:4px;font-size:11px;color:#dc2626;">${f.citizenReportCount} citizen reports verified</div>
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

function dataGovView() {
  const catalogs = dataGovApi.getCatalogs();

  return layout(
    `<div class="page">
      ${pageHeading(
        "Open Government Data (OGD) Platform",
        "Data.gov.in Datasets & Telemetry",
        "Official datasets from Jal Shakti (JJM), MoHUA (SBM-U 2.0), Rural Development (PMGSY), and Education (UDISE+), checked against field reports.",
        `<div style="display:flex;gap:8px;">
          <button id="btn-sync-data-gov" class="button" style="background:#0284c7;border-color:#0284c7;color:white;font-weight:700;">Sync data.gov.in Live APIs</button>
        </div>`
      )}

      <!-- Key National Indicators Streamed from Data.gov.in -->
      <div class="stat-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 24px;">
        <div class="stat status-stat stat-on-track">
          <span class="stat-label">JJM Tap Water Coverage</span>
          <div class="stat-value" id="dg-jjm-cov">${catalogs[0].metrics.nationalCoveragePct}%</div>
          <span class="stat-note">${catalogs[0].metrics.totalRuralHouseholdsWithTap} rural households (Jal Shakti)</span>
        </div>
        <div class="stat status-stat stat-completed">
          <span class="stat-label">SBM-U Public Toilets</span>
          <div class="stat-value" id="dg-sbm-toilets">${catalogs[1].metrics.geotaggedPublicToilets}</div>
          <span class="stat-note">Geotagged public sanitation units (MoHUA)</span>
        </div>
        <div class="stat status-stat stat-delayed">
          <span class="stat-label">PMGSY Roads Completed</span>
          <div class="stat-value">7.42 L km</div>
          <span class="stat-note">1,76,490 habitations connected (MoRD)</span>
        </div>
        <div class="stat status-stat stat-total">
          <span class="stat-label">Schools with Girl Toilets</span>
          <div class="stat-value">97.5%</div>
          <span class="stat-note">UDISE+ National School Census (MoE)</span>
        </div>
      </div>

      <!-- Real-Time Discrepancy Engine: Official Data vs. Ground Citizen Reports -->
      <section class="panel" style="margin-bottom:24px;border-left:4px solid #f59e0b;">
        <div class="panel-heading">
          <div>
            <h2>Official Data vs. Citizen Reports</h2>
            <span class="muted">Compares official completion figures with geotagged citizen reports</span>
          </div>
          <span class="badge amber">Cross-Validation</span>
        </div>
        <div style="font-size:13px;color:#334155;line-height:1.6;margin-bottom:12px;">
          While <b>data.gov.in</b> records register <b>${catalogs[0].metrics.totalRuralHouseholdsWithTap}</b> water taps and <b>${catalogs[1].metrics.geotaggedPublicToilets}</b> sanitation units, CivicSight's ground stream has flagged <b>${state.facilities.filter((f) => f.officialStatus === "ABANDONED" || f.officialStatus === "DEFUNCT").length} defunct or abandoned public assets</b> across monitored urban slums and peri-urban perimeters with dry pipes, broken pumps, or padlocks.
        </div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;">
          <a class="button amber" href="#/abandonment">View Abandonment Audit Detector →</a>
          <a class="button secondary" href="#/recommendations">View Recommended Actions →</a>
        </div>
      </section>

      <!-- Integrated Official Catalogs from Data.gov.in -->
      <div class="content-grid" style="grid-template-columns: 1fr 1fr; gap: 20px;">
        ${catalogs.map(
          (cat) => `
          <section class="panel">
            <div class="panel-heading" style="align-items:flex-start;">
              <div>
                <span style="font-size:10px;font-weight:700;color:#0284c7;text-transform:uppercase;">${cat.ministry}</span>
                <h3 style="margin:4px 0 2px;font-size:15px;color:#0f172a;">${cat.title}</h3>
                <span class="muted" style="font-size:11px;">Cadence: <b>${cat.updateFrequency}</b> • Last Ingestion: <span class="dg-last-sync">${cat.lastSynced.slice(0, 19).replace("T", " ")}</span></span>
              </div>
            </div>

            <div style="background:#f8fafc;padding:10px 12px;border-radius:6px;margin-bottom:12px;font-size:12px;">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span class="muted">Official Portal Resource:</span>
                <a href="${cat.portalUrl}" target="_blank" rel="noopener" style="color:#0284c7;font-weight:600;font-size:11px;">data.gov.in Catalog ↗</a>
              </div>
              <div style="display:flex;justify-content:space-between;">
                <span class="muted">Live API WebService:</span>
                <code style="font-size:10px;color:#475569;">${cat.sourceApi.slice(0, 38)}...</code>
              </div>
            </div>

            <table class="data-table" style="font-size:12px;">
              <thead>
                <tr>
                  <th>State / Region</th>
                  <th>Key Official Metric</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${(cat.stateBreakdown || []).slice(0, 3).map(
                  (st) => `
                  <tr>
                    <td><b>${st.state}</b></td>
                    <td>${st.coveragePct ? `${st.coveragePct}% Tap Coverage` : st.functionalPct ? `${st.functionalPct}% Functional (${st.totalToilets} units)` : st.completedKm ? `${st.completedKm.toLocaleString()} km` : `${st.electricityPct}% Electricity`}</td>
                    <td><span class="badge ${st.coveragePct === 100 || (st.functionalPct && st.functionalPct > 85) ? "green" : "amber"}">${st.status || "Audited"}</span></td>
                  </tr>`
                ).join("")}
              </tbody>
            </table>
          </section>`
        ).join("")}
      </div>
    </div>`,
    "datagov"
  );
}

function recommendationsView() {
  let recs = state.recommendations;
  if (activeRecFilter !== "all") {
    recs = recs.filter((r) => r.type.toLowerCase() === activeRecFilter.toLowerCase());
  }

  const isGov = authApi.isGovernment();

  return layout(
    `<div class="page">
      ${pageHeading(
        "Decision Support",
        "Action Recommendations: Repair, Repurpose, or Develop",
        "Synthesizes demographic census data, existing infrastructure records, and ground citizen evidence into actionable civic intervention plans."
      )}

      <div class="map-layer-toggles" style="margin-bottom:18px;">
        <button data-rec-tab="all" class="${activeRecFilter === "all" ? "active" : ""}">All Recommendations (${state.recommendations.length})</button>
        <button data-rec-tab="repair" class="${activeRecFilter === "repair" ? "active" : ""}">Repair (${state.recommendations.filter((r) => r.type === "REPAIR").length})</button>
        <button data-rec-tab="repurpose" class="${activeRecFilter === "repurpose" ? "active" : ""}">Repurpose (${state.recommendations.filter((r) => r.type === "REPURPOSE").length})</button>
        <button data-rec-tab="newly_develop" class="${activeRecFilter === "newly_develop" ? "active" : ""}">New Development (${state.recommendations.filter((r) => r.type === "NEWLY_DEVELOP").length})</button>
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

            let approveButtonHtml = "";
            if (!isGov) {
              approveButtonHtml = `
                <button class="button disabled" disabled style="opacity:0.65;cursor:not-allowed;" title="Citizen accounts cannot approve government tenders">Officer Authorization Required</button>
                <div style="font-size:10px;color:#64748b;margin-top:4px;">Citizens can review evidence. Official tenders require verified Government login.</div>
              `;
            } else if (r.status === "APPROVED_BY_OFFICER" || r.status === "APPROVED_FOR_TENDER") {
              approveButtonHtml = `<button class="button secondary" disabled style="font-size:11px;">✓ Approved (${r.status})</button>`;
            } else if (r.type === "REPAIR" && !authApi.canApproveRepair()) {
              approveButtonHtml = `<button class="button disabled" disabled style="opacity:0.65;cursor:not-allowed;">District Officer+ Required</button>`;
            } else if (r.type === "REPURPOSE" && !authApi.canApproveRepurpose()) {
              approveButtonHtml = `<button class="button disabled" disabled style="opacity:0.65;cursor:not-allowed;">State Admin+ Required</button>`;
            } else if (r.type === "NEWLY_DEVELOP" && !authApi.canApproveDevelop()) {
              approveButtonHtml = `<button class="button disabled" disabled style="opacity:0.65;cursor:not-allowed;">National Director Required</button>`;
            } else {
              approveButtonHtml = `
                <button class="button amber" data-action="approve-rec" data-rec-id="${r.id}">
                  Approve Action Plan (${currentUser.level.split(" ")[0]})
                </button>
              `;
            }

            return `
            <div class="rec-card">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                  <span class="rec-type-badge ${badgeClass}">${r.type.replace("_", " ")}</span>
                  <span class="badge ${r.urgency === "CRITICAL" ? "red" : r.urgency === "HIGH" ? "amber" : "green"}">${r.urgency}</span>
                </div>
                <h3 class="rec-title">${r.targetFacilityName}</h3>
                <span class="rec-district">${r.district} • Social ROI: <b>${r.roiScore}/10</b></span>
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
                  ${approveButtonHtml}
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

function loginView() {
  const user = authApi.getCurrentUser();
  const isGov = authApi.isGovernment();

  return layout(
    `<div class="page" style="max-width:860px;margin:20px auto;">
      ${pageHeading(
        "Official Government Authentication",
        "National Civic Infrastructure Portal — SSO Login",
        "Role-based access control with multi-tier government authorization for District Officers, State Administrators, and National Ministry Officials."
      )}

      ${
        isGov
          ? `<div class="panel" style="margin-bottom:24px;background:#f0fdf4;border:1px solid #bbf7d0;padding:16px;">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
                <div>
                  <span class="badge green">AUTHENTICATED OFFICIAL</span>
                  <h3 style="margin:6px 0 2px;color:#166534;">Currently Logged In: ${user.name}</h3>
                  <div style="font-size:12px;color:#15803d;">${user.designation} • <b>${user.level}</b></div>
                  <div style="font-size:11px;color:#166534;margin-top:4px;">Jurisdiction: ${user.jurisdiction} | Sanction Limit: ${user.approvalLimit}</div>
                </div>
                <div style="display:flex;gap:8px;">
                  <a class="button" href="#/dashboard">Go to Command Center →</a>
                  <button class="button secondary" id="btn-login-signout">Sign Out</button>
                </div>
              </div>
            </div>`
          : ""
      }

      <div class="content-grid" style="grid-template-columns: 1fr 1fr; gap: 24px;">
        <!-- Left: Official Form -->
        <section class="panel" style="padding:20px;">
          <div class="panel-heading" style="margin-bottom:16px;">
            <div>
              <h2>Government Officer SSO Login</h2>
              <span class="muted">Authorized .gov.in or .nic.in credentials</span>
            </div>
          </div>

          <form id="gov-login-form" style="display:flex;flex-direction:column;gap:14px;">
            <div id="login-error-msg" class="form-error" hidden style="background:#fee2e2;color:#991b1b;padding:8px 12px;border-radius:4px;font-size:12px;"></div>

            <div class="field">
              <label for="gov-username" style="display:block;font-size:12px;font-weight:700;margin-bottom:4px;">Official Username or Email</label>
              <input id="gov-username" type="text" required placeholder="e.g. officer.district or director@moua.gov.in" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;">
            </div>

            <div class="field">
              <label for="gov-password" style="display:block;font-size:12px;font-weight:700;margin-bottom:4px;">Government Access Password</label>
              <input id="gov-password" type="password" required placeholder="••••••••••••" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;">
            </div>

            <button type="submit" class="button full amber" style="padding:12px;font-weight:700;">Secure Login to Government Workspace</button>
            <p class="muted" style="font-size:11px;line-height:1.5;margin-top:4px;">
              Note: Unauthorized access to Government registers and budget workflows is strictly prohibited under the Information Technology Act.
            </p>
          </form>
        </section>

        <!-- Right: 1-Click Fast Demo Credentials -->
        <section class="panel" style="background:#f8fafc;padding:20px;">
          <div class="panel-heading" style="margin-bottom:14px;">
            <div>
              <h2>Demo Access (Official Roles)</h2>
              <span class="muted">Click any role to test instant hierarchical authorization</span>
            </div>
          </div>

          <div style="display:flex;flex-direction:column;gap:10px;">
            ${DEMO_CREDENTIALS.map(
              (acc) => `
              <div class="demo-acc-card" style="background:white;border:1px solid #e2e8f0;border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:5px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                  <div>
                    <span class="badge ${acc.badgeColor}" style="font-size:9px;padding:2px 6px;">${acc.level}</span>
                    <h4 style="margin:4px 0 1px;font-size:13px;color:#0f172a;">${acc.name}</h4>
                  </div>
                  <button class="button secondary" style="font-size:10px;padding:4px 9px;" data-demo-role="${acc.role}">1-Click Login</button>
                </div>
                <div style="font-size:11px;color:#475569;">${acc.designation}</div>
                <div style="font-size:10px;color:#0284c7;background:#f0f9ff;padding:3px 6px;border-radius:4px;">
                  <b>User:</b> <code>${acc.username}</code> | <b>Pass:</b> <code>${acc.password}</code>
                </div>
                <div style="font-size:10px;color:#64748b;">Sanction Limit: <b>${acc.approvalLimit}</b></div>
              </div>`
            ).join("")}
          </div>

          <div style="margin-top:14px;padding-top:12px;border-top:1px solid #e2e8f0;text-align:center;">
            <a href="#/report" style="font-size:12px;color:#64748b;text-decoration:none;">← Return to Public Citizen Portal</a>
          </div>
        </section>
      </div>
    </div>`,
    "login"
  );
}

function resolutionsView() {
  const resolutions = state.resolutions;
  return layout(
    `<div class="page">
      ${pageHeading(
        "Resolution Verification Studio",
        "Before vs. After Visual Verification",
        "Validates that civic works, repairs, and facility unlocks reported as completed are verified by before/after image comparison and field sign-offs."
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
                <span>Automated Visual Verification Score</span>
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
        "Upload geotagged photos or videos to report locked facilities, abandoned schools, defunct water kiosks, or structural damage across India."
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
              <button type="button" class="category-pill selected" data-issue="LOCKED_TOILET">Locked Public Toilet</button>
              <button type="button" class="category-pill" data-issue="ABANDONED_SCHOOL">Abandoned School</button>
              <button type="button" class="category-pill" data-issue="DEFUNCT_WATER">Defunct Water Plant</button>
              <button type="button" class="category-pill" data-issue="DEFUNCT_FACILITY">Non-Functional Facility</button>
              <button type="button" class="category-pill" data-issue="DAMAGED_INFRASTRUCTURE">Damaged Road / Culvert</button>
            </div>
            <input type="hidden" id="selected-issue-type" value="LOCKED_TOILET">
          </div>

          <div class="field">
            <label for="project-search">Associated Public Facility</label>
            <input id="project-search" list="facility-options" required placeholder="Type or select a registered public facility anywhere in India...">
            <datalist id="facility-options">
              ${state.facilities
                .map((f) => `<option value="${f.name}">${f.type.toUpperCase()} • ${f.district} (${f.state || "India"}) - ${f.officialStatus}</option>`)
                .join("")}
            </datalist>
            <div id="project-info" class="selection-info">Select a facility or let GPS find the nearest registered government asset across India.</div>
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
              <span id="location-value">Pan-India Coordinates (Auto-Detect available)</span>
              <div class="location-fields">
                <input id="latitude" type="number" step="any" placeholder="Latitude" value="28.6139">
                <input id="longitude" type="number" step="any" placeholder="Longitude" value="77.2090">
              </div>
              <button class="button secondary" type="button" data-action="locate">Detect My Current Location</button>
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
          <h2>How Reports Are Reviewed</h2>
          <div class="summary">
            <b>1. Proximity Cross-Referencing</b>
            <p class="muted" style="font-size:12px;margin:5px 0 0">Your GPS coordinates are matched against the National Public Asset Register to pinpoint the exact asset ID.</p>
          </div>
          <div class="summary">
            <b>2. Visual Deterioration Analysis</b>
            <p class="muted" style="font-size:12px;margin:5px 0 0">Submitted images are inspected for rusted padlocks, broken glass, vegetation overgrowth, and dry taps to calculate an Abandonment Score.</p>
          </div>
          <div class="summary">
            <b>3. Recommendation Routing</b>
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
            <div class="summary-row"><span>Verification</span><b>${submission?.aiConfidence || 92}% Confidence</b></div>
          </div>
          <div style="display:flex;gap:10px;justify-content:center;">
            <a class="button" href="#/map">View on GIS Map</a>
            <a class="button secondary" href="#/recommendations">View Recommendations</a>
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
        <div class="stat"><span class="stat-label">Verification confidence</span><div class="stat-value">${project.aiConfidence || 89}%</div></div>
        <div class="stat"><span class="stat-label">Budget</span><div class="stat-value" style="font-size:21px">${project.budget}</div></div>
      </div>
    </div>`,
    "projects"
  );
}

function analyticsView() {
  return layout(
    `<div class="page">
      ${pageHeading("Demographics & Performance", "District Infrastructure Analytics", "Demographic census overlay and civic condition metrics across Indian districts.")}
      <div class="content-grid">
        <section class="panel">
          <div class="panel-heading"><h2>District Demographics & Deficit Indices</h2></div>
          <table class="data-table">
            <thead>
              <tr><th>District & State</th><th>Population</th><th>Density / km²</th><th>Tracked Assets</th><th>Vulnerability Index</th></tr>
            </thead>
            <tbody>
              ${state.demographics
                .slice(0, 8)
                .map(
                  (d) =>
                    `<tr><td><b>${d.district}</b> <small style="color:#0d9488;">(${d.state || "India"})</small></td><td>${d.population.toLocaleString()}</td><td>${d.density}</td><td>${d.facilitiesCount}</td><td>${badge(d.vulnerabilityIndex > 0.35 ? "High deficit" : "Moderate")}</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        </section>
        <section class="panel">
          <div class="panel-heading"><h2>Summary of Findings</h2></div>
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
  currentUser = authApi.getCurrentUser();
  const isGov = authApi.isGovernment();

  if (hash === "#/login") return loginView();
  if (hash === "#/report") return reportView();
  if (hash === "#/submissions") return confirmationView();
  if (hash === "#/map") return mapView();
  if (hash === "#/resolutions") return resolutionsView();
  if (hash === "#/recommendations") return recommendationsView();

  // Protected Government Routes - Block Citizens
  const govOnlyRoutes = ["#/dashboard", "#/abandonment", "#/projects", "#/analytics", "#/data-gov"];
  if (govOnlyRoutes.includes(hash) || hash.startsWith("#/projects/")) {
    if (!isGov) {
      return unauthorizedView(hash);
    }
  }

  if (hash === "#/dashboard") return dashboardView();
  if (hash === "#/abandonment") return abandonmentView();
  if (hash === "#/data-gov") return dataGovView();
  if (hash === "#/projects") return projectsView();
  if (hash === "#/analytics") return analyticsView();
  if (hash.startsWith("#/projects/")) return await detailView(hash.split("/")[2]);

  return isGov ? dashboardView() : reportView();
}

async function render() {
  const hash = location.hash || (authApi.isGovernment() ? "#/dashboard" : "#/report");
  app.innerHTML = `<div class="page"><p class="muted">Loading CivicSight…</p></div>`;
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
  if (hash === "#/login") bindLoginEvents();
  if (hash === "#/data-gov") bindDataGovEvents();
}

function bindGlobalEvents() {
  document.querySelectorAll("[data-role]").forEach((button) => {
    button.addEventListener("click", () => {
      const targetRole = button.dataset.role;
      if (targetRole === "citizen") {
        authApi.logout();
        role = "citizen";
        location.hash = "#/report";
      } else {
        if (!authApi.isGovernment()) {
          location.hash = "#/login";
        } else {
          role = "officer";
          location.hash = "#/dashboard";
        }
      }
    });
  });

  const sidebarSignout = document.querySelector("#btn-sidebar-signout");
  if (sidebarSignout) {
    sidebarSignout.onclick = () => {
      authApi.logout();
      role = "citizen";
      location.hash = "#/report";
    };
  }

  document.querySelectorAll("[data-action='toast']").forEach((button) => {
    button.addEventListener("click", () => {
      button.textContent = "Saved";
      setTimeout(() => {
        button.textContent = "Done";
      }, 900);
    });
  });
}

function bindLoginEvents() {
  const form = document.querySelector("#gov-login-form");
  const errorMsg = document.querySelector("#login-error-msg");

  if (form) {
    form.onsubmit = (e) => {
      e.preventDefault();
      const username = document.querySelector("#gov-username").value;
      const password = document.querySelector("#gov-password").value;
      const res = authApi.login(username, password);
      if (res.success) {
        role = "officer";
        location.hash = "#/dashboard";
      } else {
        errorMsg.textContent = res.message;
        errorMsg.hidden = false;
      }
    };
  }

  document.querySelectorAll("[data-demo-role]").forEach((btn) => {
    btn.onclick = () => {
      const demoRole = btn.dataset.demoRole;
      authApi.loginDemo(demoRole);
      role = "officer";
      location.hash = "#/dashboard";
    };
  });

  const signoutBtn = document.querySelector("#btn-login-signout");
  if (signoutBtn) {
    signoutBtn.onclick = () => {
      authApi.logout();
      role = "citizen";
      location.hash = "#/report";
    };
  }
}

function bindDataGovEvents() {
  const syncBtn = document.querySelector("#btn-sync-data-gov");
  if (syncBtn) {
    syncBtn.onclick = async () => {
      syncBtn.disabled = true;
      syncBtn.textContent = "Syncing data.gov.in APIs...";
      const res = await dataGovApi.syncRealtimeData();
      syncBtn.textContent = `✓ Ingested ${res.syncedCatalogsCount} Official APIs (${new Date().toLocaleTimeString()})`;
      setTimeout(() => {
        syncBtn.disabled = false;
        syncBtn.textContent = "Sync data.gov.in Live APIs";
      }, 3500);
      render();
    };
  }
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
      if (!authApi.isGovernment()) {
        alert("Access Denied: Citizens cannot approve government tenders or capital actions. Please log in as a Government Officer.");
        location.hash = "#/login";
        return;
      }

      const recId = btn.dataset.recId;
      const rec = state.recommendations.find((r) => r.id === recId);
      if (rec) {
        if (rec.type === "REPAIR" && !authApi.canApproveRepair()) {
          alert("Permission Denied: District Officer or higher authorization required.");
          return;
        }
        if (rec.type === "REPURPOSE" && !authApi.canApproveRepurpose()) {
          alert("Permission Denied: State Administrator or National Director authorization required for facility repurposing.");
          return;
        }
        if (rec.type === "NEWLY_DEVELOP" && !authApi.canApproveDevelop()) {
          alert("Permission Denied: National Mission Director (MoHUA) sanction required for new capital works.");
          return;
        }
      }

      await recommendationsApi.approveRecommendation(recId);
      render();
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
      projectInfo.innerHTML = `<strong>${fac.name}</strong><span>${fac.type.toUpperCase()} • ${fac.district} (${fac.state || "India"}) • Status: <b>${fac.officialStatus}</b></span>`;
      document.querySelector("#latitude").value = fac.lat;
      document.querySelector("#longitude").value = fac.lng;
    } else {
      projectInfo.innerHTML = "Select a facility or let GPS find the nearest registered government asset across India.";
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

        // Match nearest facility across India
        let closest = null;
        let minDist = Infinity;
        state.facilities.forEach((f) => {
          const dist = Math.hypot(f.lat - lat, f.lng - lng);
          if (dist < minDist) {
            minDist = dist;
            closest = f;
          }
        });
        if (closest && minDist < 0.3) {
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
        district: fac ? `${fac.district} (${fac.state || "India"})` : "India",
        lat: Number(document.querySelector("#latitude").value) || 28.6139,
        lng: Number(document.querySelector("#longitude").value) || 77.2090,
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
