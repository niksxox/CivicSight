const mongoose = require("mongoose");

const facilitySchema = new mongoose.Schema(
  {
    name: { type: String, required: true, trim: true },
    type: {
      type: String,
      required: true,
      enum: ["school", "toilet", "water", "health", "transport", "community", "government"],
    },
    district: { type: String, required: true, trim: true },
    location: {
      lat: { type: Number, required: true },
      lng: { type: Number, required: true },
    },
    officialStatus: {
      type: String,
      enum: ["OPERATIONAL", "UNDERUTILIZED", "ABANDONED", "DEFUNCT"],
      default: "OPERATIONAL",
    },
    abandonmentScore: { type: Number, min: 0, max: 100, default: 0 },
    populationCatchment: { type: Number, default: 0 },
    establishedYear: { type: Number },
    lastInspection: { type: String, default: "Not recorded" },
    conditionNotes: { type: String, trim: true },
    citizenReportCount: { type: Number, default: 0 },
    recommendedAction: {
      type: String,
      enum: ["MAINTAIN", "REPAIR", "REPURPOSE", "NEWLY_DEVELOP"],
      default: "MAINTAIN",
    },
    proposedUse: { type: String, trim: true },
  },
  { timestamps: true }
);

facilitySchema.index({ district: 1, type: 1 });
facilitySchema.index({ "location.lat": 1, "location.lng": 1 });

module.exports = mongoose.model("Facility", facilitySchema);
