export const aiApi = {
  async analyzeEvidence(data) {
    const plannedProgress = Number(data.plannedProgress ?? 80);
    const reportedProgress = Number(data.reportedProgress ?? 55);
    const deviation = reportedProgress - plannedProgress;
    const riskLevel = deviation <= -10 ? "High" : deviation <= -5 ? "Medium" : "Low";

    return {
      plannedProgress,
      reportedProgress,
      deviation,
      riskLevel,
      finding: deviation <= -10 ? "Potential delay detected" : deviation <= -5 ? "Moderate variance detected" : "On track with minor variance",
      confidence: deviation <= -10 ? 89 : deviation <= -5 ? 82 : 94,
      explanation: deviation <= -10
        ? "Reported progress is behind plan and requires officer verification."
        : deviation <= -5
        ? "Progress is under expected plan but still within a recoverable range."
        : "Reported progress aligns with the project plan and remains stable.",
    };
  },
};
