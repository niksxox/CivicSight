import { state, getProjectById, getDashboardCounts, projectStatusValues } from "./services/mockState.js";
import { projectsApi, reportsApi, analyticsApi, aiApi } from "./services/index.js";

const app = document.querySelector("#app");
let role = "officer";
let latestSubmission = state.reports[0] || null;
let latestAnalysis = null;

const icons = { dashboard: "[]", projects: "<>", map: "()", capture: "+", analytics: "%", evidence: "#", verify: "✓" };
const officerNav = [
  ["Dashboard", "dashboard", "#/dashboard"],
  ["Projects", "projects", "#/projects"],
  ["Project map", "map", "#/map"],
  ["Analytics", "analytics", "#/analytics"],
];
const citizenNav = [["Report evidence", "capture", "#/report"], ["My submissions", "evidence", "#/submissions"]];

const getProjects = () => state.projects;
const getProject = (id) => getProjectById(state.projects, id);
const getDashboardSummary = () => getDashboardCounts(state.projects);

function pageHeading(eyebrow, title, description, action = "") {
  return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="subhead">${description}</p></div>${action}</div>`;
}

function badge(status) {
  const kind = ["On Track", "Completed"].includes(status) ? "green" : ["At Risk", "Critical"].includes(status) ? "red" : "amber";
  return `<span class="badge ${kind}">${status}</span>`;
}

function showDialog({ title, message = "", defaultValue = "", confirmText = "Confirm", inputLabel = "Value", inputType = "text" }) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "dialog-overlay";
    overlay.innerHTML = `
      <div class="dialog-card" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <div class="dialog-header">
          <h3 id="dialog-title">${title}</h3>
        </div>
        <div class="dialog-body">
          ${message ? `<p>${message}</p>` : ""}
          ${inputType === "text" ? `<label class="dialog-label"><span>${inputLabel}</span><input type="text" value="${defaultValue}" /></label>` : ""}
        </div>
        <div class="dialog-actions">
          <button type="button" class="button secondary" data-dialog-cancel>Cancel</button>
          <button type="button" class="button" data-dialog-confirm>${confirmText}</button>
        </div>
      </div>
    `;

    const input = overlay.querySelector("input");
    const confirmButton = overlay.querySelector("[data-dialog-confirm]");
    const cancelButton = overlay.querySelector("[data-dialog-cancel]");

    const close = () => overlay.remove();

    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        close();
        resolve(null);
      }
    });

    cancelButton.addEventListener("click", () => {
      close();
      resolve(null);
    });

    confirmButton.addEventListener("click", () => {
      const value = input ? input.value.trim() : "";
      close();
      resolve(value || null);
    });

    document.body.appendChild(overlay);
    if (input) input.focus();
  });
}

function showConfirm({ title, message, confirmText = "Confirm" }) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "dialog-overlay";
    overlay.innerHTML = `
      <div class="dialog-card" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div class="dialog-header">
          <h3 id="confirm-title">${title}</h3>
        </div>
        <div class="dialog-body">
          <p>${message}</p>
        </div>
        <div class="dialog-actions">
          <button type="button" class="button secondary" data-dialog-cancel>Cancel</button>
          <button type="button" class="button" data-dialog-confirm>${confirmText}</button>
        </div>
      </div>
    `;

    const confirmButton = overlay.querySelector("[data-dialog-confirm]");
    const cancelButton = overlay.querySelector("[data-dialog-cancel]");
    const close = () => overlay.remove();

    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        close();
        resolve(false);
      }
    });

    cancelButton.addEventListener("click", () => {
      close();
      resolve(false);
    });

    confirmButton.addEventListener("click", () => {
      close();
      resolve(true);
    });

    document.body.appendChild(overlay);
    confirmButton.focus();
  });
}

function riskBadge(risk = "Low") {
  const normalized = String(risk).toLowerCase();
  return `<span class="risk risk-${normalized}">${risk}</span>`;
}

function layout(content, currentRoute) {
  const nav = role === "officer" ? officerNav : citizenNav;
  return `<div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#/dashboard"><span class="brand-mark"><span>+</span></span><span><strong>CivicSight</strong><small>Progress intelligence</small></span></a>
      <div class="role-switcher"><button class="${role === "citizen" ? "active" : ""}" data-role="citizen">Field user</button><button class="${role === "officer" ? "active" : ""}" data-role="officer">Government</button></div>
      <div class="nav-label">Workspace</div>
      <nav class="nav">${nav.map(([label, icon, href]) => `<a class="${currentRoute === href.slice(2) ? "active" : ""}" href="${href}"><span class="nav-icon">${icons[icon]}</span>${label}</a>`).join("")}</nav>
      <div class="sidebar-footer"><strong>${role === "officer" ? "District Works Office" : "Civic reporting"}</strong>${role === "officer" ? "Planning & execution cell" : "Your reports make projects visible"}</div>
    </aside>
    <main class="main"><header class="topbar"><div class="breadcrumb">CivicSight / <b>${role === "officer" ? "Government workspace" : "Field reporting"}</b></div><div class="top-actions"><button title="Notifications">o</button><span class="avatar">${role === "officer" ? "AS" : "FU"}</span></div></header>${content}</main>
  </div>`;
}

function projectCards() {
  return getProjects().map((project) => `<a class="project-card" href="#/projects/${project.id}"><div><h3>${project.name}</h3><div class="project-meta">${project.category} / ${project.location}</div><div class="progress-row"><span>Actual ${project.actualProgress}%</span><span>Planned ${project.plannedProgress}%</span></div><div class="progress-track"><div class="progress-bar ${project.actualProgress < project.plannedProgress ? "warning" : ""}" style="width:${project.actualProgress}%"></div></div></div><div>${badge(project.status)}</div></a>`).join("");
}

function activityList() {
  const recent = state.reports.map((report) => ({ text: `New field evidence submitted for ${report.projectName}`, time: "Just now" }));
  return `<div class="activity">${[...recent, ...state.activityFeed].map((item) => `<div class="activity-item"><span class="activity-dot"></span><div><p>${item.text}</p><time>${item.time}</time></div></div>`).join("")}</div>`;
}

function mapMarkup() {
  return `<div class="map"><span class="pin one"></span><span class="pin warning two"></span><span class="pin three"></span><span class="pin warning four"></span><span class="map-caption"><b>${getProjects().length} projects</b> mapped across 4 zones</span></div>`;
}

function officerStatusClass(status) {
  return String(status).toLowerCase().replace(/\s+/g, "-");
}

function officerMap(projects) {
  return `<div class="officer-map">${projects.map((project) => `<button class="map-marker marker-${officerStatusClass(project.status)}" data-map-project="${project.id}" style="left:${project.coordinates[0]}%;top:${project.coordinates[1]}%" title="${project.name}"><span></span></button>`).join("")}<div class="map-legend"><span><i class="legend-on-track"></i>On track</span><span><i class="legend-at-risk"></i>At risk</span><span><i class="legend-delayed"></i>Delayed</span><span><i class="legend-completed"></i>Completed</span></div><div class="map-caption"><b>${projects.length} live signals</b> / district infrastructure map</div></div>`;
}

function selectedProjectDetail(project) {
  const deviation = project.deviation ?? (project.actualProgress - project.plannedProgress);
  return `<h2>${project.name}</h2><span class="muted">${project.location} / ${project.category}</span><div class="progress-compare"><div><span>PLANNED</span><b>${project.plannedProgress}%</b><div class="progress-track"><div class="progress-bar planned" style="width:${project.plannedProgress}%"></div></div></div><div><span>ACTUAL</span><b>${project.actualProgress}%</b><div class="progress-track"><div class="progress-bar ${deviation < 0 ? "warning" : ""}" style="width:${project.actualProgress}%"></div></div></div></div><div class="selected-metrics"><div><span>Deviation</span><b class="${deviation < 0 ? "negative" : "positive"}">${deviation > 0 ? "+" : ""}${deviation}%</b></div><div><span>AI Risk</span>${riskBadge(project.aiRisk || "Low")}</div><div><span>Confidence</span><b>${project.aiConfidence || 89}%</b></div></div><p class="risk-explanation">${project.aiExplanation || "Progress is tracking to plan."}</p><div class="action-grid"><a class="button secondary" href="#/projects/${project.id}">View Evidence</a><button class="button secondary" data-action="assign" data-project-id="${project.id}">Assign Officer</button><button class="button amber" data-action="status" data-project-id="${project.id}">Update Status</button><button class="button" data-action="verify" data-project-id="${project.id}">Verify Completion</button></div>`;
}

function officerProjectRows(projects) {
  return projects.map((project) => {
    const deviation = project.deviation ?? (project.actualProgress - project.plannedProgress);
    return `<tr data-project-row="${project.id}"><td><a class="text-link" href="#/projects/${project.id}">${project.name}</a></td><td>${project.location}</td><td>${project.plannedProgress}%</td><td>${project.actualProgress}%</td><td class="${deviation < 0 ? "negative" : "positive"}">${deviation > 0 ? "+" : ""}${deviation}%</td><td>${badge(project.status)}</td><td>${riskBadge(project.aiRisk || "Low")}</td></tr>`;
  }).join("");
}

function dashboardView() {
  const summary = getDashboardSummary();
  const projects = getProjects();
  const selected = projects[0];

  return layout(`<div class="page dashboard-page">${pageHeading("Government workspace", "Infrastructure command center", "Monitor delivery health, field evidence, and intervention priorities across the district.", `<span class="dashboard-user"><b>Anita Sharma</b><br><span class="muted">District Works Office / Planning cell</span></span>`)}<div class="stat-grid dashboard-stats">${[["Total Projects", summary.total, "total"], ["On Track", summary["On Track"], "on-track"], ["At Risk", summary["At Risk"], "at-risk"], ["Delayed", summary.Delayed, "delayed"], ["Critical", summary.Critical, "critical"], ["Completed", summary.Completed, "completed"]].map(([label, value, kind]) => `<div class="stat status-stat stat-${kind}"><span class="stat-label">${label}</span><div class="stat-value">${String(value).padStart(2, "0")}</div><span class="stat-note">Portfolio status</span></div>`).join("")}</div><div class="dashboard-grid"><section class="panel map-panel"><div class="panel-heading"><div><h2>Geographic project status</h2><span class="muted">Click a marker to inspect its delivery signal</span></div><a class="text-link" href="#/map">Open map</a></div>${officerMap(projects)}<div id="map-selection" class="map-selection"><b>${selected.name}</b><span>${selected.status} / Planned ${selected.plannedProgress}% / Actual ${selected.actualProgress}% / AI risk ${selected.aiRisk}</span></div></section><section class="panel selected-panel"><div class="eyebrow">Selected project</div><div id="selected-project-detail">${selectedProjectDetail(selected)}</div></section></div><section class="panel project-table-panel"><div class="panel-heading"><div><h2>Project register</h2><span class="muted">Search, filter, and intervene on active work</span></div><span class="badge blue">${projects.length} visible / ${projects.length} total</span></div><div class="table-controls"><input id="project-search" type="search" placeholder="Search project or district"><select id="status-filter"><option value="all">All statuses</option>${projectStatusValues.map((status) => `<option value="${status}">${status}</option>`).join("")}</select></div><table class="data-table"><thead><tr><th>Project</th><th>District</th><th>Planned</th><th>Actual</th><th>Deviation</th><th>Status</th><th>AI risk</th></tr></thead><tbody id="project-table-body">${officerProjectRows(projects)}</tbody></table></section></div>`, "dashboard");
}

function projectsView() {
  return layout(`<div class="page">${pageHeading("Government workspace", "All projects", "Track delivery against plan across the district.", `<button class="button amber" data-action="toast">+ Add project</button>`)}<section class="panel"><div class="panel-heading"><h2>Project register <span class="muted">(${getProjects().length})</span></h2><span class="muted">Updated today</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Project</th><th>Progress</th><th>Status</th><th>Officer</th><th>Updated</th></tr></thead><tbody>${getProjects().map((p) => `<tr><td><a class="text-link" href="#/projects/${p.id}">${p.name}</a><br><span class="muted">${p.category} / ${p.location}</span></td><td>${p.actualProgress}% / ${p.plannedProgress}% planned</td><td>${badge(p.status)}</td><td>${p.assignedOfficer}</td><td>${p.updated}</td></tr>`).join("")}</tbody></table></div></section></div>`, "projects");
}

function mapView() {
  return layout(`<div class="page">${pageHeading("Geographic view", "Project map", "Locate active infrastructure work and identify clusters of delivery risk.")}<section class="panel">${mapMarkup()}<div style="display:flex;gap:14px;margin-top:15px;font-size:12px"><span><i style="color:var(--teal)">●</i> On track</span><span><i style="color:var(--amber)">●</i> At risk</span><span><i style="color:var(--red)">●</i> Delayed</span><span><i style="color:#397bb1">●</i> Completed</span></div></section><div class="content-grid"><section class="panel"><div class="panel-heading"><h2>Zone summary</h2></div>${["North district", "East district", "South district", "West district"].map((zone, i) => `<div class="summary-row"><span>${zone}</span><b>${[2, 1, 2, 1][i]} projects</b></div>`).join("")}</section><section class="panel"><div class="panel-heading"><h2>Risk signal</h2></div><p class="muted">West and North districts show the strongest planned-versus-actual variance this month.</p><a class="text-link" href="#/projects/road-zone-a">Review Road Development – Zone A</a></section></div></div>`, "map");
}

function detailView(id) {
  const project = getProject(id) || getProjects()[0];
  if (!project) return layout("<div class='page'><p class='muted'>Project not found.</p></div>", "projects");

  return layout(`<div class="page">${pageHeading("Project details", project.name, `${project.category} / ${project.location}`, `<a class="button secondary" href="#/projects">Back to projects</a>`)}<div class="hero-strip"><div><h2>${["At Risk", "Delayed", "Critical"].includes(project.status) ? "Potential delay detected" : "Delivery is progressing"}</h2><p>Last field update ${project.updated}. Assigned to ${project.assignedOfficer}.</p></div><button class="button amber" data-action="toast">Update status</button></div><div class="stat-grid"><div class="stat"><span class="stat-label">Planned progress</span><div class="stat-value">${project.plannedProgress}%</div></div><div class="stat"><span class="stat-label">Actual progress</span><div class="stat-value">${project.actualProgress}%</div></div><div class="stat"><span class="stat-label">AI confidence</span><div class="stat-value">${project.aiConfidence || 89}%</div></div><div class="stat"><span class="stat-label">Budget</span><div class="stat-value" style="font-size:21px">${project.budget}</div></div></div><div class="content-grid"><section class="panel"><div class="panel-heading"><h2>Evidence timeline</h2><button class="button secondary" data-action="toast">Assign officer</button></div>${activityList()}<div class="panel-heading" style="margin-top:16px"><h2>Latest evidence</h2></div><div class="upload" style="min-height:130px"><strong>${project.evidence?.[0]?.fileName || "Field evidence"}</strong><br>${project.evidence?.[0]?.description || "No evidence uploaded yet."}</div></section><section class="panel"><div class="panel-heading"><h2>Planned vs actual</h2></div><div class="chart">${[55, 62, 67, 74, 80].map((value, i) => `<div class="bar-group"><div class="bar" style="height:${value}%"></div><div class="bar actual" style="height:${[42, 45, 49, 51, 55][i]}%"></div><small>W${i + 1}</small></div>`).join("")}</div><div class="summary"><b>AI review</b><p class="muted" style="margin:4px 0 0;font-size:12px">${project.aiExplanation || "No AI review available."}</p></div><button class="button secondary" data-action="assign" data-project-id="${project.id}">Assign Officer</button></section></div></div>`, "projects");
}

function reportView() {
  return layout(`<div class="page">${pageHeading("Field reporting", "Report project evidence", "Complete the four steps below so the project team can verify your update.")}<div class="stepper"><span class="active">1 Project</span><span>2 Evidence</span><span>3 Location</span><span>4 Review</span></div><div class="form-layout"><form class="form-panel" id="citizen-evidence-form"><h2>Evidence details</h2><div class="field"><label for="project-search">Project or facility</label><input id="project-search" list="project-options" required placeholder="Search by project or facility name"><datalist id="project-options">${getProjects().map((p) => `<option value="${p.name}">${p.category} / ${p.location}</option>`).join("")}</datalist><div id="project-info" class="selection-info">Select a project to see its current status.</div></div><div class="field"><label for="evidence-file">Photo or video evidence</label><div class="upload upload-active"><strong>Drop files here or choose from this device</strong><span>JPG, PNG, WEBP, MP4 up to 25 MB</span><input id="evidence-file" type="file" accept="image/*,video/*" multiple required><div id="evidence-preview" class="evidence-preview"></div><p id="evidence-error" class="form-error" hidden>Please add at least one photo or video before continuing.</p></div></div><div class="field"><label>Location</label><div class="location-box"><strong id="location-status">Location not captured</strong><span id="location-value">Use device location or enter coordinates manually.</span><div class="location-fields"><input id="latitude" type="number" step="any" placeholder="Latitude"><input id="longitude" type="number" step="any" placeholder="Longitude"></div><button class="button secondary" type="button" data-action="locate">Use my current location</button></div></div><div class="field"><label for="description">Observed condition or progress <span class="muted">(20-500 characters)</span></label><textarea id="description" required placeholder="Describe the current condition, progress, or issue visible on site..."></textarea><div class="character-count"><span id="description-count">0</span>/500</div><p id="description-error" class="form-error" hidden>Please enter at least 20 characters.</p></div><div class="review-panel" id="review-panel" hidden><h3>Review before submit</h3><div id="review-content"></div></div><button class="button full" type="button" data-action="review">Review evidence</button><button class="button full" type="submit" style="margin-top:8px">Submit evidence</button><p id="submit-error" class="form-error" hidden>There was a problem submitting your evidence. Please try again.</p></form><aside class="form-panel"><h2>Before you submit</h2><div class="summary"><b>Be specific</b><p class="muted" style="font-size:12px;margin:5px 0 0">Mention the work visible, approximate progress, and anything blocking delivery.</p></div><div class="summary"><b>Keep location on</b><p class="muted" style="font-size:12px;margin:5px 0 0">A location helps the project team verify your report quickly.</p></div><div class="summary"><b>AI review</b><p class="muted" style="font-size:12px;margin:5px 0 0">Your submission will generate a mock AI risk and progress analysis to support officer review.</p></div></aside></div></div>`, "report");
}

function confirmationView() {
  const submission = latestSubmission || state.reports[0];
  return layout(`<div class="page"><div class="confirmation"><section class="panel"><div class="check">✓</div><div class="eyebrow">Submission received</div><h1>Thank you for the update</h1><p class="subhead">Your evidence has been linked to ${submission?.project || "Road Development - Zone A"} and sent to the district works office.</p><div class="summary" style="text-align:left;margin:25px 0"><div class="summary-row"><span>Reference</span><b>${submission?.id || "EVD-2026-0826"}</b></div><div class="summary-row"><span>Location</span><b>${submission?.location || "Captured location"}</b></div><div class="summary-row"><span>Status</span><b>Under review</b></div></div><a class="button" href="#/submission-result">View project and AI analysis</a></section></div></div>`, "submission");
}

function resultView() {
  const analysis = latestAnalysis || { plannedProgress: 80, reportedProgress: 55, deviation: -25, riskLevel: "High", finding: "Potential delay detected", confidence: 89, explanation: "Reported progress is 25 points behind the plan. Officer verification is recommended." };
  return layout(`<div class="page">${pageHeading("Submission result", latestSubmission?.project || "Road Development - Zone A", "Your reported evidence has been added to the project record.")}<section class="panel"><div class="eyebrow">Mock AI-assisted review</div><h2>${analysis.finding}</h2><div class="result-grid"><div><div class="result-label">Planned progress</div><div class="result-value">${analysis.plannedProgress}%</div></div><div><div class="result-label">Reported progress</div><div class="result-value attention">${analysis.reportedProgress}%</div></div><div><div class="result-label">Deviation</div><div class="result-value attention">${analysis.deviation} pts</div></div><div><div class="result-label">AI confidence</div><div class="result-value confidence">${analysis.confidence}%</div></div></div><div class="summary"><b>Risk level: ${analysis.riskLevel}</b><p class="muted" style="margin:4px 0 0;font-size:12px">${analysis.explanation}</p></div><p class="muted">This is a mock decision-support response for the MVP. It is not an actual AI model and must be verified by an officer.</p><a class="button" href="#/report">Report another update</a></section></div>`, "submission-result");
}

function analyticsView() {
  const analytics = analyticsApi.getAnalytics ? analyticsApi.getAnalytics() : { plannedVsActual: [], reportVolume: 0, completionRate: 0 };
  const chartData = analytics.plannedVsActual || [];
  return layout(`<div class="page">${pageHeading("Performance", "Analytics", "Delivery signals across the current project portfolio.")}<div class="content-grid"><section class="panel"><div class="panel-heading"><h2>Portfolio progress</h2><span class="muted">Apr - Aug 2026</span></div><div class="chart">${chartData.length ? chartData.map((item) => `<div class="bar-group"><div class="bar" style="height:${item.planned}%"></div><div class="bar actual" style="height:${item.actual}%"></div><small>${item.label}</small></div>`).join("") : "<p class='muted'>No analytics data available.</p>"}</div></section><section class="panel"><div class="panel-heading"><h2>Signal summary</h2></div>${[["Evidence reviewed", `${analytics.reportVolume || 0}`], ["Average variance", `${Math.round(getProjects().reduce((sum, p) => sum + (p.deviation || 0), 0) / getProjects().length) || 0} pts`], ["Verified completions", `${analytics.completionRate || 0}%`]].map(([label, value]) => `<div class="summary-row"><span>${label}</span><b>${value}</b></div>`).join("")}</section></div></div>`, "analytics");
}

function render() {
  const hash = location.hash || "#/dashboard";
  let view = dashboardView();

  if (role === "citizen" && hash === "#/dashboard") {
    location.hash = "#/report";
    return;
  }

  if (hash === "#/report") view = reportView();
  else if (hash === "#/submissions") view = confirmationView();
  else if (hash === "#/submission-result") view = resultView();
  else if (hash === "#/projects") view = projectsView();
  else if (hash === "#/map") view = mapView();
  else if (hash === "#/analytics") view = analyticsView();
  else if (hash.startsWith("#/projects/")) view = detailView(hash.split("/")[2]);
  else view = dashboardView();

  app.innerHTML = view;
  bindGlobalEvents();

  if (hash === "#/dashboard") bindOfficerEvents();
  if (hash === "#/report") bindCitizenEvents();
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
      setTimeout(() => { button.textContent = "Done"; }, 900);
    });
  });
}

function bindOfficerEvents() {
  const detail = document.querySelector("#selected-project-detail");
  const selection = document.querySelector("#map-selection");
  const search = document.querySelector("#project-search");
  const filter = document.querySelector("#status-filter");
  const tableBody = document.querySelector("#project-table-body");

  const renderSelection = (id) => {
    const project = getProject(id) || getProjects()[0];
    detail.innerHTML = selectedProjectDetail(project);
    selection.innerHTML = `<b>${project.name}</b><span>${project.status} / Planned ${project.plannedProgress}% / Actual ${project.actualProgress}% / AI risk ${project.aiRisk}</span>`;
    bindOfficerActions();
  };

  const filterRows = () => {
    if (!search || !filter || !tableBody) return;
    const query = search.value.toLowerCase();
    const status = filter.value;
    tableBody.innerHTML = officerProjectRows(getProjects().filter((project) => (status === "all" || project.status === status) && `${project.name} ${project.location}`.toLowerCase().includes(query)));
    tableBody.querySelectorAll("[data-project-row]").forEach((row) => row.addEventListener("click", () => renderSelection(row.dataset.projectRow)));
  };

  const bindOfficerActions = () => {
    document.querySelectorAll("[data-map-project]").forEach((button) => {
      button.addEventListener("click", () => renderSelection(button.dataset.mapProject));
    });

    document.querySelectorAll("[data-action='assign']").forEach((button) => {
      button.addEventListener("click", async () => {
        const project = getProject(button.dataset.projectId);
        const officer = await showDialog({
          title: "Assign officer",
          message: `Assign a responsible officer for ${project.name}.`,
          defaultValue: project.assignedOfficer,
          inputLabel: "Officer name",
          confirmText: "Save",
        });
        if (officer) {
          await projectsApi.assignOfficer(button.dataset.projectId, officer);
          render();
        }
      });
    });

    document.querySelectorAll("[data-action='status']").forEach((button) => {
      button.addEventListener("click", async () => {
        const project = getProject(button.dataset.projectId);
        const nextStatus = await showDialog({
          title: "Update project status",
          message: `Choose the next status for ${project.name}.`,
          defaultValue: project.status,
          inputLabel: "Status (On Track, At Risk, Delayed, Critical, or Completed)",
          confirmText: "Update",
        });
        if (nextStatus) {
          await projectsApi.updateProjectStatus(button.dataset.projectId, nextStatus);
          render();
        }
      });
    });

    document.querySelectorAll("[data-action='verify']").forEach((button) => {
      button.addEventListener("click", async () => {
        const confirmed = await showConfirm({
          title: "Verify completion",
          message: "Verify completion for this project? This updates the project record.",
          confirmText: "Verify",
        });
        if (confirmed) {
          await projectsApi.verifyCompletion(button.dataset.projectId);
          render();
        }
      });
    });
  };

  if (search && filter) {
    search.addEventListener("input", filterRows);
    filter.addEventListener("change", filterRows);
  }

  bindOfficerActions();
  if (tableBody) filterRows();
}

function bindCitizenEvents() {
  const form = document.querySelector("#citizen-evidence-form");
  const projectInput = document.querySelector("#project-search");
  const projectInfo = document.querySelector("#project-info");
  const fileInput = document.querySelector("#evidence-file");
  const preview = document.querySelector("#evidence-preview");
  const description = document.querySelector("#description");
  const count = document.querySelector("#description-count");
  const reviewPanel = document.querySelector("#review-panel");
  const evidenceError = document.querySelector("#evidence-error");
  const descriptionError = document.querySelector("#description-error");
  const reviewButton = document.querySelector("[data-action='review']");
  const locateButton = document.querySelector("[data-action='locate']");

  let files = [];

  function selectedProject() {
    return getProjects().find((project) => project.name === projectInput.value) || null;
  }

  function renderProjectInfo() {
    const project = selectedProject();
    projectInfo.innerHTML = project ? `<strong>${project.name}</strong><span>${project.category} / ${project.location} / ${project.actualProgress}% reported progress</span>` : "Select a project to see its current status.";
  }

  function renderPreview() {
    preview.innerHTML = files.map((file, index) => `<div class="evidence-item"><div class="media-preview">${file.type.startsWith("video/") ? `<video src="${URL.createObjectURL(file)}" controls></video>` : `<img src="${URL.createObjectURL(file)}" alt="Evidence preview">`}</div><span>${file.type.startsWith("video/") ? "Video" : "Photo"}: ${file.name}</span><button type="button" data-remove-file="${index}" title="Remove evidence">Remove</button></div>`).join("");
    preview.querySelectorAll("[data-remove-file]").forEach((button) => {
      button.addEventListener("click", () => {
        files.splice(Number(button.dataset.removeFile), 1);
        renderPreview();
      });
    });
  }

  function addFiles(fileList) {
    files = [...files, ...[...fileList].filter((file) => file.type.startsWith("image/") || file.type.startsWith("video/"))].slice(0, 5);
    evidenceError.hidden = files.length > 0;
    renderPreview();
  }

  projectInput.addEventListener("input", renderProjectInfo);
  fileInput.addEventListener("change", () => addFiles(fileInput.files));

  const upload = document.querySelector(".upload-active");
  ["dragenter", "dragover"].forEach((eventName) => upload.addEventListener(eventName, (event) => {
    event.preventDefault();
    upload.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach((eventName) => upload.addEventListener(eventName, (event) => {
    event.preventDefault();
    upload.classList.remove("dragging");
    if (eventName === "drop") addFiles(event.dataTransfer.files);
  }));

  description.addEventListener("input", () => {
    count.textContent = description.value.length;
    descriptionError.hidden = description.value.length === 0 || description.value.length >= 20;
  });

  locateButton.addEventListener("click", () => {
    const status = document.querySelector("#location-status");
    const value = document.querySelector("#location-value");

    if (!navigator.geolocation) {
      status.textContent = "Manual location required";
      value.textContent = "Enter latitude and longitude below.";
      return;
    }

    status.textContent = "Requesting location...";
    navigator.geolocation.getCurrentPosition((position) => {
      document.querySelector("#latitude").value = position.coords.latitude.toFixed(6);
      document.querySelector("#longitude").value = position.coords.longitude.toFixed(6);
      status.textContent = "Location captured";
      value.textContent = `${position.coords.latitude.toFixed(4)} N, ${position.coords.longitude.toFixed(4)} E / Accuracy ${Math.round(position.coords.accuracy)} m`;
    }, () => {
      status.textContent = "Manual location required";
      value.textContent = "Permission unavailable. Enter latitude and longitude below.";
    });
  });

  function valid() {
    const hasLocation = document.querySelector("#latitude").value && document.querySelector("#longitude").value;
    evidenceError.hidden = files.length > 0;
    descriptionError.hidden = description.value.length >= 20;

    if (!selectedProject()) projectInput.focus();
    else if (!files.length) fileInput.focus();
    else if (!hasLocation) document.querySelector("#latitude").focus();
    else if (description.value.length < 20) description.focus();

    return Boolean(selectedProject() && files.length && hasLocation && description.value.length >= 20);
  }

  reviewButton.addEventListener("click", () => {
    if (!valid()) return;
    const project = selectedProject();
    reviewPanel.hidden = false;
    reviewPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    document.querySelector("#review-content").innerHTML = `<div class="review-row"><b>Project</b><span>${project.name}</span></div><div class="review-row"><b>Evidence</b><span>${files.map((file) => file.name).join(", ")}</span></div><div class="review-row"><b>Location</b><span>${document.querySelector("#latitude").value}, ${document.querySelector("#longitude").value}</span></div><div class="review-row"><b>Description</b><span>${description.value}</span></div>`;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!valid()) return;

    const submitButton = form.querySelector("button[type='submit']");
    const submitError = document.querySelector("#submit-error");
    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";
    submitError.hidden = true;

    try {
      const project = selectedProject();
      const reportedProgress = Math.min(100, Math.max(0, project.actualProgress + 5));
      const payload = {
        projectId: project.id,
        project: project.name,
        files: files.map((file) => ({ name: file.name, type: file.type })),
        location: `${document.querySelector("#latitude").value}, ${document.querySelector("#longitude").value}`,
        description: description.value,
        reportedProgress,
        previewUrl: files[0] ? URL.createObjectURL(files[0]) : undefined,
      };

      latestSubmission = await reportsApi.submitReport(payload);
      latestAnalysis = await aiApi.analyzeEvidence({ plannedProgress: project.plannedProgress, reportedProgress });
      location.hash = "#/submissions";
    } catch (error) {
      console.error(error);
      submitError.hidden = false;
      submitButton.disabled = false;
      submitButton.textContent = "Submit evidence";
    }
  });
}

window.addEventListener("hashchange", render);
render();
