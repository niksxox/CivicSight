const Project = require("../models/Project");

const STATUS_STEPS = Project.STATUS_STEPS; // ["PLANNED","ASSIGNED","IN_PROGRESS","COMPLETED","VERIFIED"]

// @route PATCH /api/projects/:id/status   (OFFICER/ADMIN)
// Body: { status: "IN_PROGRESS" }
// Only allows moving forward one step at a time, or backward for corrections by ADMIN.
const updateStatus = async (req, res, next) => {
  try {
    const { status } = req.body;
    if (!STATUS_STEPS.includes(status)) {
      return res.status(400).json({ message: `status must be one of ${STATUS_STEPS.join(", ")}` });
    }

    const project = await Project.findById(req.params.id);
    if (!project) return res.status(404).json({ message: "Project not found" });

    const currentIndex = STATUS_STEPS.indexOf(project.status);
    const targetIndex = STATUS_STEPS.indexOf(status);

    // Officers can only move forward one step at a time.
    // Admins can correct backward if something was marked wrong.
    const isForwardStep = targetIndex === currentIndex + 1;
    const isAdminOverride = req.user.role === "ADMIN";

    if (!isForwardStep && !isAdminOverride) {
      return res.status(400).json({
        message: `Invalid transition: ${project.status} -> ${status}. Must move forward one step at a time.`,
        allowedNext: STATUS_STEPS[currentIndex + 1] || null,
      });
    }

    // VERIFIED requires a before/after comparison per the MVP checklist.
    if (status === "VERIFIED" && (!project.beforeImageUrl || !project.afterImageUrl)) {
      return res.status(400).json({
        message: "Cannot verify: beforeImageUrl and afterImageUrl must be set first.",
      });
    }

    project.status = status;
    project.statusHistory.push({ status, changedBy: req.user._id });
    await project.save();

    res.json(project);
  } catch (err) {
    next(err);
  }
};

// @route GET /api/projects/:id/status-history
const getStatusHistory = async (req, res, next) => {
  try {
    const project = await Project.findById(req.params.id)
      .select("statusHistory status")
      .populate("statusHistory.changedBy", "name email");

    if (!project) return res.status(404).json({ message: "Project not found" });
    res.json(project);
  } catch (err) {
    next(err);
  }
};

module.exports = { updateStatus, getStatusHistory };
