const mongoose = require("mongoose");

const recommendationSchema = new mongoose.Schema(
  {
    type: {
      type: String,
      required: true,
      enum: ["REPAIR", "REPURPOSE", "NEWLY_DEVELOP"],
    },
    urgency: {
      type: String,
      enum: ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
      default: "MEDIUM",
    },
    priorityScore: { type: Number, min: 0, max: 100, default: 80 },
    targetFacilityId: { type: mongoose.Schema.Types.ObjectId, ref: "Facility", default: null },
    targetFacilityName: { type: String, required: true, trim: true },
    district: { type: String, required: true, trim: true },
    affectedPopulation: { type: Number, default: 0 },
    estimatedCost: { type: String, trim: true },
    timelineDays: { type: Number, default: 30 },
    roiScore: { type: Number, default: 8.5 },
    rationale: { type: String, required: true, trim: true },
    proposedUse: { type: String, trim: true },
    actionItems: [{ type: String }],
    status: {
      type: String,
      enum: ["PROPOSED", "IN_REVIEW", "FEASIBILITY_APPROVED", "APPROVED_FOR_TENDER", "APPROVED_BY_OFFICER", "PLANNED", "COMPLETED"],
      default: "PROPOSED",
    },
  },
  { timestamps: true }
);

recommendationSchema.index({ type: 1, district: 1 });

module.exports = mongoose.model("Recommendation", recommendationSchema);
