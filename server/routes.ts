import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertSessionSchema, lessonTimelineSchema, type LessonTimeline } from "@shared/schema";
import { spawn } from "child_process";
import path from "path";

async function runPythonOrchestrator(prompt: string, sessionId: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHON_PATH || "python3";
    const orchestratorPath = path.join(process.cwd(), "backend", "orchestrator.py");
    
    const pythonProcess = spawn(pythonPath, [orchestratorPath, prompt, sessionId], {
      cwd: path.join(process.cwd(), "backend"),
      env: { ...process.env, PYTHONPATH: path.join(process.cwd(), "backend") }
    });
    
    let stdout = "";
    let stderr = "";
    
    pythonProcess.stdout.on("data", (data) => {
      stdout += data.toString();
    });
    
    pythonProcess.stderr.on("data", (data) => {
      stderr += data.toString();
    });
    
    pythonProcess.on("close", (code) => {
      if (code !== 0) {
        console.error("Python orchestrator stderr:", stderr);
        reject(new Error(`Orchestrator exited with code ${code}: ${stderr}`));
        return;
      }
      
      try {
        const lines = stdout.trim().split("\n");
        const lastLine = lines[lines.length - 1];
        const result = JSON.parse(lastLine);
        resolve(result);
      } catch (e) {
        reject(new Error(`Failed to parse orchestrator output: ${stdout}`));
      }
    });
    
    pythonProcess.on("error", (err) => {
      reject(err);
    });
  });
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  app.post("/api/v1/sessions", async (req: Request, res: Response) => {
    try {
      const { prompt, user_id } = req.body;
      
      if (!prompt || typeof prompt !== "string") {
        res.status(400).json({ error: "Prompt is required" });
        return;
      }
      
      const session = await storage.createSession({
        prompt,
        userId: user_id || null,
        status: "pending",
        timeline: null,
        metadata: null
      });
      
      res.json({
        session_id: session.id,
        status: "pending",
        message: "Session created. Use GET /api/v1/sessions/:id to check status."
      });
      
      runPythonOrchestrator(prompt, session.id)
        .then(async (result) => {
          if (result.error) {
            await storage.updateSessionStatus(session.id, "error");
          } else if (result.timeline) {
            await storage.updateSessionTimeline(session.id, result.timeline);
          }
        })
        .catch(async (err) => {
          console.error("Orchestrator error:", err);
          await storage.updateSessionStatus(session.id, "error");
        });
      
    } catch (error) {
      console.error("Session creation error:", error);
      res.status(500).json({ error: "Failed to create session" });
    }
  });

  app.get("/api/v1/sessions/:id", async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      
      const session = await storage.getSession(id);
      
      if (!session) {
        res.status(404).json({ error: "Session not found" });
        return;
      }
      
      res.json({
        session_id: session.id,
        status: session.status,
        timeline: session.timeline,
        metadata: session.metadata,
        created_at: session.createdAt,
        updated_at: session.updatedAt
      });
      
    } catch (error) {
      console.error("Session fetch error:", error);
      res.status(500).json({ error: "Failed to fetch session" });
    }
  });

  app.get("/api/v1/primitives", async (_req: Request, res: Response) => {
    try {
      const primitives = await storage.getAllPrimitives();
      res.json({ primitives });
    } catch (error) {
      console.error("Primitives fetch error:", error);
      res.status(500).json({ error: "Failed to fetch primitives" });
    }
  });

  app.get("/api/v1/assets/:sessionId/:assetName", async (req: Request, res: Response) => {
    try {
      const { sessionId, assetName } = req.params;
      
      const assets = await storage.getAssetsBySession(sessionId);
      const asset = assets.find(a => 
        a.primitiveId === assetName.replace('.svg', '') || 
        a.id === assetName.replace('.svg', '')
      );
      
      if (asset && asset.svgContent) {
        res.setHeader('Content-Type', 'image/svg+xml');
        res.send(asset.svgContent);
        return;
      }
      
      res.status(404).json({ error: "Asset not found" });
      
    } catch (error) {
      console.error("Asset fetch error:", error);
      res.status(500).json({ error: "Failed to fetch asset" });
    }
  });

  return httpServer;
}
