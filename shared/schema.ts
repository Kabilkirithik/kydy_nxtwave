import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, jsonb, integer } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

export const sessions = pgTable("sessions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id"),
  prompt: text("prompt").notNull(),
  status: varchar("status", { length: 50 }).notNull().default("pending"),
  timeline: jsonb("timeline"),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const insertSessionSchema = createInsertSchema(sessions).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertSession = z.infer<typeof insertSessionSchema>;
export type Session = typeof sessions.$inferSelect;

export const primitives = pgTable("primitives", {
  id: varchar("id").primaryKey(),
  type: varchar("type", { length: 50 }).notNull(),
  name: varchar("name", { length: 100 }).notNull(),
  domain: varchar("domain", { length: 100 }),
  paramsSchema: jsonb("params_schema").notNull(),
  renderContract: text("render_contract"),
  svgTemplate: text("svg_template"),
});

export const insertPrimitiveSchema = createInsertSchema(primitives);

export type InsertPrimitive = z.infer<typeof insertPrimitiveSchema>;
export type Primitive = typeof primitives.$inferSelect;

export const assets = pgTable("assets", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  sessionId: varchar("session_id").references(() => sessions.id),
  primitiveId: varchar("primitive_id"),
  assetUrl: text("asset_url"),
  svgContent: text("svg_content"),
  params: jsonb("params"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertAssetSchema = createInsertSchema(assets).omit({
  id: true,
  createdAt: true,
});

export type InsertAsset = z.infer<typeof insertAssetSchema>;
export type Asset = typeof assets.$inferSelect;

export const timelineLayerSchema = z.object({
  type: z.enum(["svg", "primitive", "text"]),
  asset: z.string().optional(),
  assetUrl: z.string().optional(),
  primitive: z.string().optional(),
  params: z.record(z.any()).optional(),
  content: z.string().optional(),
  position: z.object({
    x: z.number(),
    y: z.number(),
  }).optional(),
});

export const timelineSegmentSchema = z.object({
  id: z.string(),
  startOffset_ms: z.number(),
  duration_ms: z.number(),
  layers: z.array(timelineLayerSchema),
  learningObjective: z.string().optional(),
  insertable: z.boolean().optional(),
});

export const lessonTimelineSchema = z.object({
  lessonId: z.string(),
  metadata: z.object({
    title: z.string(),
    audience: z.string().optional(),
    duration_min: z.number().optional(),
  }),
  timeline: z.array(timelineSegmentSchema),
  insertPoints: z.array(z.string()).optional(),
});

export type TimelineLayer = z.infer<typeof timelineLayerSchema>;
export type TimelineSegment = z.infer<typeof timelineSegmentSchema>;
export type LessonTimeline = z.infer<typeof lessonTimelineSchema>;
