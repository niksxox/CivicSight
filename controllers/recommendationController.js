const Recommendation = require("../models/Recommendation");

// @route GET /api/recommendations
const getRecommendations = async (req, res, next) => {
  try {
    const filter = {};
    if (req.query.type) filter.type = req.query.type;
    if (req.query.district) filter.district = new RegExp(req.query.district, "i");
    if (req.query.urgency) filter.urgency = req.query.urgency;

    const recommendations = await Recommendation.find(filter).sort({ priorityScore: -1 });
    res.json(recommendations);
  } catch (err) {
    next(err);
  }
};

// @route POST /api/recommendations (OFFICER/ADMIN)
const createRecommendation = async (req, res, next) => {
  try {
    const { type, targetFacilityName, district, rationale } = req.body;
    if (!type || !targetFacilityName || !district || !rationale) {
      return res.status(400).json({ message: "type, targetFacilityName, district, and rationale are required" });
    }

    const recommendation = await Recommendation.create(req.body);
    res.status(201).json(recommendation);
  } catch (err) {
    next(err);
  }
};

// @route PATCH /api/recommendations/:id/status (OFFICER/ADMIN)
const updateRecommendationStatus = async (req, res, next) => {
  try {
    const { status } = req.body;
    const recommendation = await Recommendation.findByIdAndUpdate(
      req.params.id,
      { status },
      { new: true, runValidators: true }
    );
    if (!recommendation) return res.status(404).json({ message: "Recommendation not found" });
    res.json(recommendation);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  getRecommendations,
  createRecommendation,
  updateRecommendationStatus,
};
