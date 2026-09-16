const express = require("express");
const {
  getCivicReports,
  createCivicReport,
  verifyResolution,
} = require("../controllers/civicReportController");
const { protect, authorize } = require("../middleware/authMiddleware");

const router = express.Router();

router.get("/", getCivicReports);
router.post("/", createCivicReport); // Open to citizen ground submissions
router.patch("/:id/verify", protect, authorize("OFFICER", "ADMIN"), verifyResolution);

module.exports = router;
