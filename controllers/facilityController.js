const Facility = require("../models/Facility");

// @route GET /api/facilities
// Supports ?district=... &type=... &status=... &minAbandonmentScore=...
const getFacilities = async (req, res, next) => {
  try {
    const filter = {};
    if (req.query.district) filter.district = new RegExp(req.query.district, "i");
    if (req.query.type) filter.type = req.query.type;
    if (req.query.status) filter.officialStatus = req.query.status;
    if (req.query.minAbandonmentScore) {
      filter.abandonmentScore = { $gte: Number(req.query.minAbandonmentScore) };
    }

    const facilities = await Facility.find(filter).sort({ abandonmentScore: -1 });
    res.json(facilities);
  } catch (err) {
    next(err);
  }
};

// @route GET /api/facilities/:id
const getFacilityById = async (req, res, next) => {
  try {
    const facility = await Facility.findById(req.params.id);
    if (!facility) return res.status(404).json({ message: "Facility not found" });
    res.json(facility);
  } catch (err) {
    next(err);
  }
};

// @route POST /api/facilities (OFFICER/ADMIN)
const createFacility = async (req, res, next) => {
  try {
    const { name, type, district, location, officialStatus, populationCatchment, conditionNotes } = req.body;
    if (!name || !type || !district || !location) {
      return res.status(400).json({ message: "name, type, district, and location {lat, lng} are required" });
    }
    const facility = await Facility.create(req.body);
    res.status(201).json(facility);
  } catch (err) {
    next(err);
  }
};

// @route PATCH /api/facilities/:id (OFFICER/ADMIN)
const updateFacility = async (req, res, next) => {
  try {
    const facility = await Facility.findByIdAndUpdate(req.params.id, req.body, { new: true, runValidators: true });
    if (!facility) return res.status(404).json({ message: "Facility not found" });
    res.json(facility);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  getFacilities,
  getFacilityById,
  createFacility,
  updateFacility,
};
