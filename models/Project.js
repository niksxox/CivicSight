const mongoose = require("mongoose");

// Enforced end-to-end per SRS: PLANNED -> ASSIGNED -> IN_PROGRESS -> COMPLETED -> VERIFIED
const STATUS_STEPS = ["PLANNED", "ASSIGNED", "IN_PROGRESS", "COMPLETED", "VERIFIED"];

const evidenceSchema = new mongoose.Schema(
  {
    photoUrl: { type: String, required: true },
    location: {
      lat: { type: Number, required: true },
      lng: { type: Number, required: true },
    },
    description: { type: String, trim: true },
    // Filled in by the AI/analytics service, not by this API directly.
    aiResult: {
      condition: { type: String, default: null },
      issue: { type: String, default: null },
      confidence: { type: Number, default: null }, // 0-1
      needsHumanReview: { type: Boolean, default: true },
    },
    submittedBy: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
    submittedAt: { type: Date, default: Date.now },
  },
  { _id: true }
);

const projectSchema = new mongoose.Schema(
  {
    title: { type: String, required: true, trim: true },
    description: { type: String, trim: true },
    location: {
      lat: { type: Number, required: true },
      lng: { type: Number, required: true },
    },
    status: {
      type: String,
      enum: STATUS_STEPS,
      default: "PLANNED",
    },
    plannedProgress: { type: Number, min: 0, max: 100, default: 0 },
    actualProgress: { type: Number, min: 0, max: 100, default: 0 },
    // Set by the analytics side — this API only stores/exposes it.
    priorityScore: { type: Number, default: null },
    assignedTo: { type: mongoose.Schema.Types.ObjectId, ref: "User", default: null },
    createdBy: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
    evidence: [evidenceSchema],
    beforeImageUrl: { type: String, default: null },
    afterImageUrl: { type: String, default: null },
    statusHistory: [
      {
        status: { type: String, enum: STATUS_STEPS },
        changedBy: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
        changedAt: { type: Date, default: Date.now },
      },
    ],
  },
  { timestamps: true }
);

projectSchema.statics.STATUS_STEPS = STATUS_STEPS;

module.exports = mongoose.model("Project", projectSchema);
