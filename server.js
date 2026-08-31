require("dotenv").config();
const express = require("express");
const cors = require("cors");
const morgan = require("morgan");
const connectDB = require("./config/db");
const { notFound, errorHandler } = require("./middleware/errorMiddleware");

const authRoutes = require("./routes/authRoutes");
const projectRoutes = require("./routes/projectRoutes");

const app = express();
const PORT = Number(process.env.PORT) || 5000;
const HOST = process.env.HOST || "0.0.0.0";
const isProduction = process.env.NODE_ENV === "production";

if (!process.env.MONGO_URI) {
  if (isProduction) {
    console.error("MONGO_URI is required in production");
    process.exit(1);
  }
  console.warn("MONGO_URI not set — starting without MongoDB connection");
} else {
  connectDB();
}

app.disable("x-powered-by");
app.set("trust proxy", 1);
app.use(express.json({ limit: "10mb" }));
app.use(morgan(isProduction ? "combined" : "dev"));

const allowedOrigins = (process.env.CORS_ORIGIN || "")
  .split(",")
  .map((o) => o.trim())
  .filter(Boolean);

app.use(
  cors({
    origin: allowedOrigins.length ? allowedOrigins : isProduction ? false : true,
    credentials: true,
  })
);

app.get("/api/health", (req, res) =>
  res.json({
    status: "ok",
    service: "civsight-node-api",
    mongo: process.env.MONGO_URI ? "configured" : "not_configured",
  })
);

app.use("/api/auth", authRoutes);
app.use("/api/projects", projectRoutes);

app.use(notFound);
app.use(errorHandler);

const server = app.listen(PORT, HOST, () =>
  console.log(`Server running on ${HOST}:${PORT}`)
);

const shutdown = (signal) => {
  console.log(`${signal} received — shutting down`);
  server.close(() => {
    const mongoose = require("mongoose");
    mongoose.connection.close(false).finally(() => process.exit(0));
  });
};

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
