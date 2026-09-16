const CivicReport = require("../models/CivicReport");
const Facility = require("../models/Facility");

// @route GET /api/civic-reports
const getCivicReports = async (req, res, next) => {
  try {
    const filter = {};
    if (req.query.issueType) filter.issueType = req.query.issueType;
    if (req.query.district) filter.district = new RegExp(req.query.district, "i");
    if (req.query.status) filter.status = req.query.status;

    const reports = await CivicReport.find(filter).sort({ createdAt: -1 });
    res.json(reports);
  } catch (err) {
    next(err);
  }
};

// @route POST /api/civic-reports
const createCivicReport = async (req, res, next) => {
  try {
    const { facilityId, facilityName, issueType, district, location, description } = req.body;
    if (!facilityName || !issueType || !district || !location || !description) {
      return res.status(400).json({ message: "facilityName, issueType, district, location, and description are required" });
    }

    const report = await CivicReport.create({
      ...req.body,
      reportedBy: req.user ? req.user.name : req.body.reportedBy || "Citizen Contributor",
    });

    // If linked to a facility, update the facility's report count and risk score
    if (facilityId) {
      await Facility.findByIdAndUpdate(facilityId, {
        $inc: { citizenReportCount: 1, abandonmentScore: 5 },
      });
    }

    res.status(201).json(report);
  } catch (err) {
    next(err);
  }
};

// @route PATCH /api/civic-reports/:id/verify (OFFICER/ADMIN)
const verifyResolution = async (req, res, next) => {
  try {
    const { afterImageUrl, verificationScore, inspectionReport } = req.body;
    const report = await CivicReport.findById(req.params.id);
    if (!report) return res.status(404).json({ message: "Report not found" });

    report.status = "RESOLVED";
    report.resolution = {
      ...report.resolution,
      afterImageUrl: afterImageUrl || report.resolution?.afterImageUrl,
      resolvedBy: req.user ? req.user.name : "Field Officer",
      resolvedAt: new Date(),
      verifiedBy: req.user ? req.user.name : "Inspecting Engineer",
      verificationScore: verificationScore || 95,
      inspectionReport: inspectionReport || "Physical verification complete and confirmed resolved.",
    };

    await report.save();
    res.json(report);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  getCivicReports,
  createCivicReport,
  verifyResolution,
};
