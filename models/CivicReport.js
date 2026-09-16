const mongoose = require("mongoose");

const civicReportSchema = new mongoose.Schema(
  {
    facilityId: { type: mongoose.Schema.Types.ObjectId, ref: "Facility", default: null },
    facilityName: { type: String, required: true, trim: true },
    issueType: {
      type: String,
      required: true,
      enum: ["LOCKED_TOILET", "ABANDONED_SCHOOL", "DEFUNCT_WATER", "DEFUNCT_FACILITY", "DAMAGED_INFRASTRUCTURE", "OTHER"],
    },
    issueTitle: { type: String, trim: true },
    district: { type: String, required: true, trim: true },
    location: {
      lat: { type: Number, required: true },
      lng: { type: Number, required: true },
    },
    description: { type: String, required: true, trim: true },
    photoUrls: [{ type: String }],
    reportedBy: { type: String, default: "Citizen Ground Contributor" },
    conditionSeverity: {
      type: String,
      enum: ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
      default: "MEDIUM",
    },
    aiTags: [{ type: String }],
    aiConfidence: { type: Number, default: 85 },
    status: {
      type: String,
      enum: ["PENDING", "CONFIRMED_ISSUE", "UNDER_INSPECTION", "RESOLVED"],
      default: "CONFIRMED_ISSUE",
    },
    resolution: {
      beforeImageUrl: { type: String, default: null },
      afterImageUrl: { type: String, default: null },
      resolvedBy: { type: String, default: null },
      resolvedAt: { type: Date, default: null },
      verifiedBy: { type: String, default: null },
      verificationScore: { type: Number, default: null },
      inspectionReport: { type: String, default: null },
    },
  },
  { timestamps: true }
);

civicReportSchema.index({ district: 1, issueType: 1 });
civicReportSchema.index({ "location.lat": 1, "location.lng": 1 });

module.exports = mongoose.model("CivicReport", civicReportSchema);
