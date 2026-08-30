const express = require("express");
const {
  createProject,
  getProjects,
  getProjectById,
  updateProject,
  deleteProject,
  assignProject,
  submitEvidence,
  updateEvidenceAiResult,
} = require("../controllers/projectController");
const { updateStatus, getStatusHistory } = require("../controllers/statusController");
const { protect, authorize } = require("../middleware/authMiddleware");

const router = express.Router();

// Core CRUD
router.post("/", protect, authorize("OFFICER", "ADMIN"), createProject);
router.get("/", protect, getProjects);
router.get("/:id", protect, getProjectById);
router.patch("/:id", protect, authorize("OFFICER", "ADMIN"), updateProject);
router.delete("/:id", protect, authorize("ADMIN"), deleteProject);

// Assignment
router.post("/:id/assign", protect, authorize("OFFICER", "ADMIN"), assignProject);

// Status workflow
router.patch("/:id/status", protect, authorize("OFFICER", "ADMIN"), updateStatus);
router.get("/:id/status-history", protect, getStatusHistory);

// Citizen evidence submission
router.post("/:id/evidence", protect, submitEvidence);

// AI service writes its result back here (see README for securing this)
router.patch("/:id/evidence/:evidenceId/ai-result", protect, authorize("ADMIN"), updateEvidenceAiResult);

module.exports = router;
