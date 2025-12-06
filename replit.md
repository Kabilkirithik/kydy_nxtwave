# AI Tutoring Platform with Animated Lesson Generation

## Overview

This is an AI-powered learning platform that generates interactive, animated lesson timelines based on natural language prompts. The system uses a multi-agent orchestration architecture (CrewAI) to process user requests like "teach me Ohm's law" and produces structured lesson content with synchronized SVG animations.

The application consists of:
- **Frontend**: React-based UI with TypeScript, Tailwind CSS, and shadcn/ui components
- **Backend**: Express.js API server with PostgreSQL database
- **AI Pipeline**: Python-based orchestration using CrewAI agents and Google's Gemini LLM
- **Visual Generation**: Parametric SVG generation system with safety sanitization

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Technology Stack**: React 18 with TypeScript, Vite as build tool, Wouter for routing

**UI Framework**: shadcn/ui (Radix UI primitives) with Tailwind CSS v4 using the "new-york" style preset

**State Management**: TanStack Query (React Query) for server state, with custom query client configured for API requests

**Design Decisions**:
- Component-based architecture with reusable UI primitives in `client/src/components/ui/`
- Path aliases configured for clean imports (`@/`, `@shared/`, `@assets/`)
- Custom Vite plugins for meta image updates and Replit-specific development features
- Client-side rendering with SPA routing (single-page application)

### Backend Architecture

**API Server**: Express.js with TypeScript, serving both API endpoints and static frontend assets

**Route Structure**: 
- RESTful API at `/api/*` endpoints
- Session management for lesson generation
- Python orchestrator integration via child process spawning

**Key Design Patterns**:
- Repository pattern with storage abstraction layer (`IStorage` interface)
- Database operations separated into `storage.ts` module
- Request logging middleware with response capturing
- Static file serving for production builds

**Development vs Production**:
- Development: Uses Vite dev server with HMR (Hot Module Replacement)
- Production: Serves pre-built static assets from `dist/public`

### Data Storage

**Database**: PostgreSQL with Drizzle ORM

**Schema Design**:
- `users`: User authentication and profiles
- `sessions`: Lesson generation sessions with status tracking and timeline storage
- `primitives`: Visual primitive definitions (SVG templates) with parameter schemas
- `assets`: Generated SVG assets linked to sessions

**Data Models**:
- Sessions store timeline as JSONB, allowing flexible schema evolution
- Primitives use JSONB for params_schema, enabling dynamic validation
- Timeline structure includes segments with layers, animations, and learning objectives

### AI Orchestration Pipeline

**Framework**: CrewAI with sequential task processing

**Agent Architecture** (5 specialized agents):
1. **Parse Agent**: Extracts structured intent from natural language prompts (domain, subdomain, topic, audience, objectives)
2. **Retrieve Agent**: Selects appropriate visual primitives and reference materials based on domain
3. **Timeline Agent**: Composes complete lesson timeline with segments, layers, and animations
4. **SVG Agent**: Generates parametric SVG assets or retrieves from templates
5. **Validator Agent**: Validates timeline schema, timing, primitives, and content safety

**LLM Integration**: Google Gemini 2.5 Flash for all agents (cost-effective, fast inference)

**Process Flow**:
```
User Prompt → Parse Agent → Retrieve Agent → Timeline Agent → SVG Agent → Validator Agent → Final Timeline
```

**Error Handling**: JSON extraction from LLM output with regex fallbacks, graceful degradation on agent failures

### SVG Generation System

**Two-Tier Approach**:
1. **Parametric Generator**: Programmatic templates using Python string formatting (primary method)
2. **LLM-Generated**: Fallback for complex visuals when templates insufficient

**Primitive Store**: Registry of reusable visual components (battery, resistor, wire, arrow, graph, etc.) mapped to domains

**Safety Features** (SVGSanitizer):
- Whitelist of allowed SVG tags (no script, foreign objects)
- Forbidden event handler attributes removed (onclick, onload, etc.)
- Protocol filtering (javascript:, data:, vbscript:)
- Dimension validation and injection

**Parameter Handling**: Type-safe conversion with fallback defaults to handle LLM output variations

### Authentication & Security

**Current State**: Basic user schema exists but no active authentication middleware implemented

**Planned**: Session-based authentication with JWT tokens, user-scoped lesson libraries

**SVG Sanitization**: Critical security layer preventing XSS attacks through generated content

### Build & Deployment

**Build Process** (`script/build.ts`):
- Client: Vite production build to `dist/public`
- Server: esbuild bundling with selective dependency externalization
- Allowlist system for reducing cold start times (bundles frequently-used deps)

**Environment Variables**:
- `DATABASE_URL`: PostgreSQL connection string (required)
- `PYTHON_PATH`: Path to Python interpreter for orchestrator
- `NODE_ENV`: development/production mode switching

**Development Workflow**:
- `npm run dev`: Starts Express server with Vite middleware
- `npm run dev:client`: Vite dev server standalone
- `npm run db:push`: Drizzle schema push to database

## External Dependencies

### Third-Party Services

**AI/LLM**:
- Google Gemini API (gemini-2.5-flash model) via CrewAI integration
- Requires API key configuration in Python backend

### Databases

**PostgreSQL**: 
- Primary data store for users, sessions, primitives, and assets
- Connection managed via `pg` npm package and node-postgres pool
- Drizzle ORM for type-safe queries and migrations

### Python Packages

**CrewAI Framework**: Multi-agent orchestration
- Agent and Task definitions
- Sequential process execution
- LLM integration abstraction

**Pydantic**: Data validation for agent outputs

### NPM Packages (Key Dependencies)

**Frontend**:
- `react`, `react-dom`: UI framework
- `@tanstack/react-query`: Server state management
- `wouter`: Lightweight routing
- `@radix-ui/*`: Headless UI primitives (20+ packages)
- `tailwindcss`: Utility-first CSS
- `zod`: Runtime type validation
- `react-hook-form`: Form state management

**Backend**:
- `express`: Web server framework
- `drizzle-orm`: Database ORM
- `pg`: PostgreSQL client
- `zod`: Schema validation (shared with frontend)
- `nanoid`: Unique ID generation

**Development**:
- `vite`: Build tool and dev server
- `tsx`: TypeScript execution
- `esbuild`: Server bundling
- `@replit/vite-plugin-*`: Replit-specific tooling

### Build Tools & Plugins

**Custom Vite Plugins**:
- `vite-plugin-meta-images`: Updates OpenGraph images for Replit deployments
- `@replit/vite-plugin-runtime-error-modal`: Development error overlay
- `@replit/vite-plugin-cartographer`: Code navigation
- `@replit/vite-plugin-dev-banner`: Development environment indicator

**CSS Processing**: PostCSS with Tailwind CSS and Autoprefixer

### Integration Points

**Python-Node Bridge**: 
- Child process spawning to run `orchestrator.py`
- JSON-based communication via stdout parsing
- Error handling for process failures

**Database Migrations**:
- Drizzle Kit for schema management
- Migration files in `./migrations` directory
- Schema source: `shared/schema.ts`