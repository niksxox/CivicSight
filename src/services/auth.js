// CivicSight Government Authentication & Role-Based Access Control (RBAC)
// Enforces official hierarchy: Citizen vs. District Officer vs. State Admin vs. National Director

export const GOV_ROLES = {
  CITIZEN: "citizen",
  DISTRICT_OFFICER: "district_officer",
  STATE_ADMIN: "state_admin",
  NATIONAL_DIRECTOR: "national_director",
};

export const DEMO_CREDENTIALS = [
  {
    username: "officer.district",
    email: "officer@district.gov.in",
    password: "Gov@District2026",
    role: GOV_ROLES.DISTRICT_OFFICER,
    name: "Er. Rajesh Sharma",
    designation: "Executive Engineer & District Works Officer",
    department: "District Urban Development Authority (DUDA)",
    level: "District Level",
    jurisdiction: "Visakhapatnam & North Coastal Districts",
    approvalLimit: "₹15 Lakhs (Repair Tenders & Sign-offs)",
    badgeColor: "amber",
  },
  {
    username: "admin.state",
    email: "admin@state.gov.in",
    password: "Gov@State2026",
    role: GOV_ROLES.STATE_ADMIN,
    name: "Smt. K. Sunitha, IAS",
    designation: "Principal Secretary, Urban Development & Panchayati Raj",
    department: "Municipal Administration & Urban Development Secretariat",
    level: "State Level",
    jurisdiction: "All Districts (State-wide)",
    approvalLimit: "₹50 Lakhs (Repurposing & Capital Transfers)",
    badgeColor: "blue",
  },
  {
    username: "director.national",
    email: "director@moua.gov.in",
    password: "Gov@National2026",
    role: GOV_ROLES.NATIONAL_DIRECTOR,
    name: "Dr. Vikram Malhotra, IAS",
    designation: "Joint Secretary & National Mission Director",
    department: "Ministry of Housing & Urban Affairs (MoHUA), Govt of India",
    level: "National Apex Level",
    jurisdiction: "Pan-India (All 28 States & 8 UTs)",
    approvalLimit: "Unlimited (Full National Sanctions & Policy)",
    badgeColor: "green",
  },
];

const STORAGE_KEY = "civicsight_auth_user";

export const authApi = {
  getCurrentUser() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) return JSON.parse(stored);
    } catch {}
    return {
      role: GOV_ROLES.CITIZEN,
      name: "Public Citizen",
      email: null,
      level: "Public Citizen",
      department: "Community Contributor",
    };
  },

  setCurrentUser(user) {
    try {
      if (user) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {}
  },

  isGovernment() {
    const u = this.getCurrentUser();
    return u && u.role !== GOV_ROLES.CITIZEN;
  },

  getUserRole() {
    return this.getCurrentUser()?.role || GOV_ROLES.CITIZEN;
  },

  canAccessGovData() {
    return this.isGovernment();
  },

  // Hierarchy rules
  canApproveRepair() {
    const role = this.getUserRole();
    return [
      GOV_ROLES.DISTRICT_OFFICER,
      GOV_ROLES.STATE_ADMIN,
      GOV_ROLES.NATIONAL_DIRECTOR,
    ].includes(role);
  },

  canApproveRepurpose() {
    const role = this.getUserRole();
    return [
      GOV_ROLES.STATE_ADMIN,
      GOV_ROLES.NATIONAL_DIRECTOR,
    ].includes(role);
  },

  canApproveDevelop() {
    const role = this.getUserRole();
    return role === GOV_ROLES.NATIONAL_DIRECTOR;
  },

  canSignOffResolution() {
    return this.isGovernment();
  },

  login(usernameOrEmail, password) {
    const normalizedInput = (usernameOrEmail || "").trim().toLowerCase();
    const account = DEMO_CREDENTIALS.find(
      (acc) =>
        (acc.username.toLowerCase() === normalizedInput || acc.email.toLowerCase() === normalizedInput) &&
        acc.password === password
    );

    if (!account) {
      return {
        success: false,
        message: "Invalid government credentials. Please check your username/password or use the 1-click demo logins below.",
      };
    }

    this.setCurrentUser(account);
    return {
      success: true,
      user: account,
    };
  },

  loginDemo(role) {
    const account = DEMO_CREDENTIALS.find((a) => a.role === role) || DEMO_CREDENTIALS[0];
    this.setCurrentUser(account);
    return {
      success: true,
      user: account,
    };
  },

  logout() {
    this.setCurrentUser(null);
  },
};
