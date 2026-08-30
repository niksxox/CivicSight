const Project = require("../models/Project");

// @route POST /api/projects   (OFFICER/ADMIN)
const createProject = async (req, res, next) => {
  try {
    const { title, description, location, plannedProgress } = req.body;

    if (!title || !location || location.lat === undefined || location.lng === undefined) {
      return res.status(400).json({ message: "title and location {lat, lng} are required" });
    }

    const project = await Project.create({
      title,
      description,
      location,
      plannedProgress: plannedProgress || 0,
      createdBy: req.user._id,
      statusHistory: [{ status: "PLANNED", changedBy: req.user._id }],
    });

    res.status(201).json(project);
  } catch (err) {
    next(err);
  }
};

// @route GET /api/projects
// Supports ?status=IN_PROGRESS and ?assignedTo=<userId> filters
const getProjects = async (req, res, next) => {
  try {
    const filter = {};
    if (req.query.status) filter.status = req.query.status;
    if (req.query.assignedTo) filter.assignedTo = req.query.assignedTo;

    const projects = await Project.find(filter)
      .populate("assignedTo", "name email")
      .populate("createdBy", "name email")
      .sort({ createdAt: -1 });

    res.json(projects);
  } catch (err) {
    next(err);
  }
};

// @route GET /api/projects/:id
const getProjectById = async (req, res, next) => {
  try {
    const project = await Project.findById(req.params.id)
      .populate("assignedTo", "name email")
      .populate("createdBy", "name email");

    if (!project) return res.status(404).json({ message: "Project not found" });
    res.json(project);
  } catch (err) {
    next(err);
  }
};

// @route PATCH /api/projects/:id   (OFFICER/ADMIN)
const updateProject = async (req, res, next) => {
  try {
    const allowedFields = ["title", "description", "location", "plannedProgress", "actualProgress"];
    const updates = {};
    for (const field of allowedFields) {
      if (req.body[field] !== undefined) updates[field] = req.body[field];
    }

    const project = await Project.findByIdAndUpdate(req.params.id, updates, {
      new: true,
      runValidators: true,
    });

    if (!project) return res.status(404).json({ message: "Project not found" });
    res.json(project);
  } catch (err) {
    next(err);
  }
};

// @route DELETE /api/projects/:id   (ADMIN)
const deleteProject = async (req, res, next) => {
  try {
    const project = await Project.findByIdAndDelete(req.params.id);
    if (!project) return res.status(404).json({ message: "Project not found" });
    res.json({ message: "Project deleted" });
  } catch (err) {
    next(err);
  }
};

// @route POST /api/projects/:id/assign   (OFFICER/ADMIN)
const assignProject = async (req, res, next) => {
  try {
    const { userId } = req.body;
    if (!userId) return res.status(400).json({ message: "userId is required" });

    const project = await Project.findById(req.params.id);
    if (!project) return res.status(404).json({ message: "Project not found" });

    project.assignedTo = userId;
    if (project.status === "PLANNED") {
      project.status = "ASSIGNED";
      project.statusHistory.push({ status: "ASSIGNED", changedBy: req.user._id });
    }
    await project.save();

    res.json(project);
  } catch (err) {
    next(err);
  }
};

// @route POST /api/projects/:id/evidence   (CITIZEN or field OFFICER)
// This is the "citizen submits evidence with photo, location, description" MVP item.
// aiResult is left null here — the AI/analytics service fills it in via updateEvidenceAiResult.
const submitEvidence = async (req, res, next) => {
  try {
    const { photoUrl, location, description } = req.body;
    if (!photoUrl || !location) {
      return res.status(400).json({ message: "photoUrl and location are required" });
    }

    const project = await Project.findById(req.params.id);
    if (!project) return res.status(404).json({ message: "Project not found" });

    project.evidence.push({
      photoUrl,
      location,
      description,
      submittedBy: req.user._id,
    });
    await project.save();

    res.status(201).json(project.evidence[project.evidence.length - 1]);
  } catch (err) {
    next(err);
  }
};

// @route PATCH /api/projects/:id/evidence/:evidenceId/ai-result
// Internal endpoint for the AI/analytics service to write back its result.
// Protect this with a service-to-service key, not a normal user token (see README).
const updateEvidenceAiResult = async (req, res, next) => {
  try {
    const { condition, issue, confidence, needsHumanReview } = req.body;

    const project = await Project.findById(req.params.id);
    if (!project) return res.status(404).json({ message: "Project not found" });

    const evidenceItem = project.evidence.id(req.params.evidenceId);
    if (!evidenceItem) return res.status(404).json({ message: "Evidence not found" });

    evidenceItem.aiResult = { condition, issue, confidence, needsHumanReview };
    await project.save();

    res.json(evidenceItem);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  createProject,
  getProjects,
  getProjectById,
  updateProject,
  deleteProject,
  assignProject,
  submitEvidence,
  updateEvidenceAiResult,
};
