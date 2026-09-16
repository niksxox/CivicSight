const express = require("express");
const {
  getRecommendations,
  createRecommendation,
  updateRecommendationStatus,
} = require("../controllers/recommendationController");
const { protect, authorize } = require("../middleware/authMiddleware");

const router = express.Router();

router.get("/", getRecommendations);
router.post("/", protect, authorize("OFFICER", "ADMIN"), createRecommendation);
router.patch("/:id/status", protect, authorize("OFFICER", "ADMIN"), updateRecommendationStatus);

module.exports = router;
