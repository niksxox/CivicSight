const express = require("express");
const {
  getFacilities,
  getFacilityById,
  createFacility,
  updateFacility,
} = require("../controllers/facilityController");
const { protect, authorize } = require("../middleware/authMiddleware");

const router = express.Router();

// Public read access for map and citizen reporting
router.get("/", getFacilities);
router.get("/:id", getFacilityById);

// Government write operations
router.post("/", protect, authorize("OFFICER", "ADMIN"), createFacility);
router.patch("/:id", protect, authorize("OFFICER", "ADMIN"), updateFacility);

module.exports = router;
