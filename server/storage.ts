import { 
  type User, type InsertUser,
  type Session, type InsertSession,
  type Primitive, type InsertPrimitive,
  type Asset, type InsertAsset,
  type LessonTimeline,
  users, sessions, primitives, assets
} from "@shared/schema";
import { db } from "./db";
import { eq } from "drizzle-orm";

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  createSession(session: InsertSession): Promise<Session>;
  getSession(id: string): Promise<Session | undefined>;
  updateSessionStatus(id: string, status: string): Promise<Session | undefined>;
  updateSessionTimeline(id: string, timeline: LessonTimeline): Promise<Session | undefined>;
  getSessionsByUser(userId: string): Promise<Session[]>;
  
  createPrimitive(primitive: InsertPrimitive): Promise<Primitive>;
  getPrimitive(id: string): Promise<Primitive | undefined>;
  getPrimitivesByDomain(domain: string): Promise<Primitive[]>;
  getAllPrimitives(): Promise<Primitive[]>;
  
  createAsset(asset: InsertAsset): Promise<Asset>;
  getAsset(id: string): Promise<Asset | undefined>;
  getAssetsBySession(sessionId: string): Promise<Asset[]>;
}

export class DatabaseStorage implements IStorage {
  async getUser(id: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db.insert(users).values(insertUser).returning();
    return user;
  }

  async createSession(insertSession: InsertSession): Promise<Session> {
    const [session] = await db.insert(sessions).values(insertSession).returning();
    return session;
  }

  async getSession(id: string): Promise<Session | undefined> {
    const [session] = await db.select().from(sessions).where(eq(sessions.id, id));
    return session;
  }

  async updateSessionStatus(id: string, status: string): Promise<Session | undefined> {
    const [session] = await db
      .update(sessions)
      .set({ status, updatedAt: new Date() })
      .where(eq(sessions.id, id))
      .returning();
    return session;
  }

  async updateSessionTimeline(id: string, timeline: LessonTimeline): Promise<Session | undefined> {
    const [session] = await db
      .update(sessions)
      .set({ 
        timeline: timeline as any,
        metadata: timeline.metadata as any,
        status: "ready",
        updatedAt: new Date()
      })
      .where(eq(sessions.id, id))
      .returning();
    return session;
  }

  async getSessionsByUser(userId: string): Promise<Session[]> {
    return db.select().from(sessions).where(eq(sessions.userId, userId));
  }

  async createPrimitive(insertPrimitive: InsertPrimitive): Promise<Primitive> {
    const [primitive] = await db.insert(primitives).values(insertPrimitive).returning();
    return primitive;
  }

  async getPrimitive(id: string): Promise<Primitive | undefined> {
    const [primitive] = await db.select().from(primitives).where(eq(primitives.id, id));
    return primitive;
  }

  async getPrimitivesByDomain(domain: string): Promise<Primitive[]> {
    return db.select().from(primitives).where(eq(primitives.domain, domain));
  }

  async getAllPrimitives(): Promise<Primitive[]> {
    return db.select().from(primitives);
  }

  async createAsset(insertAsset: InsertAsset): Promise<Asset> {
    const [asset] = await db.insert(assets).values(insertAsset).returning();
    return asset;
  }

  async getAsset(id: string): Promise<Asset | undefined> {
    const [asset] = await db.select().from(assets).where(eq(assets.id, id));
    return asset;
  }

  async getAssetsBySession(sessionId: string): Promise<Asset[]> {
    return db.select().from(assets).where(eq(assets.sessionId, sessionId));
  }
}

export const storage = new DatabaseStorage();
