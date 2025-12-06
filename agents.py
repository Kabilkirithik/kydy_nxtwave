# crewai_method_a_example.py
"""
CrewAI-style example (Method A - LLM prompt-only SVG generation)
Follows the pattern you provided: uses `from crewai import Agent, Task, Crew, LLM`
and `from crewai.tools import BaseTool` to define tools and agents,
then constructs Tasks and runs them with Crew.kickoff()-style API.

NOTES:
 - Replace OPENAI_API_KEY / OLLM_API_KEY placeholders with real keys or wire to your LLM.
 - This script intentionally mirrors your example style and returns structured JSON only.
 - It does NOT use FastAPI — pure agent/task/crew orchestration as requested.
"""

import os
import json
import re
import uuid
from typing import Any, Dict, List, Optional

# ---- Import crewai primitives (your environment should have crewai installed) ----
# If your installed crewai package uses different names or signatures, adapt accordingly.
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool

# ---- Security: set your LLM API key in env or here (DO NOT commit real keys) ----
# Example: export OLLM_API_KEY="sk-..."
OLLm_API_KEY = os.getenv("OLLM_API_KEY", "<PUT_YOUR_LLM_API_KEY_HERE>")
# Example LLM instantiation (match model/provider available in your environment)
# Replace model name with whatever your provider supports (Gemini/GPT/Claude/etc).
ollm = LLM(model="gpt-4o-mini", api_key=OLLm_API_KEY)


# -----------------------------
# Tools
# -----------------------------
class PrimitiveStoreTool(BaseTool):
    """
    Simple tool that acts as a primitive/asset registry retriever (RAG stub).
    In production this would query a Vector DB + metadata store.
    """
    name: str = "primitive_store"
    description: str = "Return allowed primitives and render contracts for a given domain/subdomain"

    # _run is the synchronous handler; crewai tools often implement run/_run
    def _run(self, domain_subdomain: str) -> Dict[str, Any]:
        # domain_subdomain like "physics:circuits"
        # For demo, we return a small physics primitives set
        mapping = {
            "physics:circuits": {
                "allowed_primitives": [
                    "battery.svg", "resistor.svg", "particleStream", "graphLine", "sliderControl", "textBox"
                ],
                "notes": "Demo primitives for circuits"
            },
            # add more domain entries as needed
        }
        return mapping.get(domain_subdomain, mapping["physics:circuits"])

    def run(self, domain_subdomain: str):
        return self._run(domain_subdomain)


class CDNTool(BaseTool):
    """
    Simple in-memory 'upload' tool that returns an asset_id and asset_url.
    Replace this with S3/CloudFront/Azure Blob logic in production.
    """
    name: str = "cdn_uploader"
    description: str = "Uploads sanitized SVG string and returns an asset URL"

    def __init__(self, base_url: str = "https://cdn.example.com/auto"):
        self.base_url = base_url
        self._store: Dict[str, str] = {}

    def _run(self, svg_text: str, filename: Optional[str] = None) -> Dict[str, str]:
        filename = filename or f"svg_{uuid.uuid4().hex[:8]}.svg"
        self._store[filename] = svg_text
        url = f"{self.base_url}/{filename}"
        return {"asset_id": filename, "asset_url": url}

    def run(self, svg_text: str, filename: Optional[str] = None):
        return self._run(svg_text, filename)


# -----------------------------
# Helpers: SVG extraction & sanitization
# -----------------------------
from lxml import etree
import re

ALLOWED_TAGS = {
    "svg", "g", "rect", "circle", "ellipse", "line", "path", "text",
    "defs", "use", "animate", "animateTransform", "title"
}
ATTR_RE = re.compile(r"^[a-zA-Z0-9:\-]+$")


def extract_svg_block(text: str) -> Optional[str]:
    start = text.find("<svg")
    if start == -1:
        return None
    end = text.find("</svg>", start)
    if end == -1:
        return None
    return text[start:end + 6]


def sanitize_svg(svg_text: str) -> str:
    """
    Parse/validate/sanitize a generated SVG. Raises ValueError on invalid/unsafe.
    Keep this conservative.
    """
    parser = etree.XMLParser(resolve_entities=False, no_network=True, remove_comments=True)
    try:
        root = etree.fromstring(svg_text.encode("utf-8"), parser=parser)
    except Exception as e:
        raise ValueError(f"SVG parse error: {e}")

    # Tag allow-list
    for el in root.iter():
        tag = etree.QName(el.tag).localname
        if tag not in ALLOWED_TAGS:
            raise ValueError(f"Disallowed SVG tag: {tag}")

    # Remove script elements explicitly (just in case)
    for script in root.findall('.//{http://www.w3.org/2000/svg}script'):
        parent = script.getparent()
        if parent is not None:
            parent.remove(script)

    # Sanitize attributes
    for el in root.iter():
        for a in list(el.attrib):
            if a.lower().startswith("on"):  # event handlers
                del el.attrib[a]; continue
            val = el.attrib[a]
            if isinstance(val, str) and ("http:" in val or "https:" in val or "javascript:" in val):
                del el.attrib[a]; continue
            if not ATTR_RE.match(a):
                del el.attrib[a]; continue

    # root width/height required
    if "width" not in root.attrib or "height" not in root.attrib:
        raise ValueError("SVG must include width and height attributes on root <svg>")

    cleaned = etree.tostring(root, encoding="utf-8").decode("utf-8")
    return cleaned


# -----------------------------
# Agents
# -----------------------------
# We'll create a set of agents using Agent(...) pattern similar to your example.
# Each Agent is constructed with role/goal/backstory/tools/llm and will be used in Tasks.

def create_parse_agent(llm: LLM) -> Agent:
    """
    Agent: parse_prompt
    - Input: prompt text
    - Output: JSON dict with domain/subdomain/topic/audience/duration_min/objectives
    """
    role = "Prompt classifier"
    goal = "Extract domain, subdomain, topic, audience, duration_min and learning objectives from user prompt; return JSON only."
    backstory = "Lightweight classifier for educational topics. Prefer short outputs and valid JSON."

    async def _run(task: Task):
        prompt_text = task.description if hasattr(task, "description") else task.payload.get("prompt", "")
        system = (
            "You are a classifier. Return ONLY a JSON object with keys: "
            '"domain","subdomain","topic","audience","duration_min","objectives".'
        )
        user = f'Classify this user prompt: "{prompt_text}"\nReturn JSON only.'
        raw = await llm.call(system, user, temperature=0.0, max_tokens=250)
        try:
            return json.loads(raw)
        except Exception:
            # fallback heuristic
            return {
                "domain": "physics",
                "subdomain": "circuits",
                "topic": prompt_text,
                "audience": "college",
                "duration_min": 6,
                "objectives": []
            }

    return Agent(role=role, goal=goal, backstory=backstory, run=_run, llm=ollm)


def create_retrieve_agent(primitive_tool: PrimitiveStoreTool) -> Agent:
    """
    Agent: retrieve_primitives
    - Input: domain/subdomain string
    - Output: allowed_primitives doc
    """

    role = "Primitive retriever"
    goal = "Given domain:subdomain return allowed primitives and metadata (via tool)."

    async def _run(task: Task):
        domain = task.payload.get("domain", "physics")
        subdomain = task.payload.get("subdomain", "circuits")
        key = f"{domain}:{subdomain}"
        # Use tool to get primitives
        doc = primitive_tool.run(key)
        return doc

    return Agent(role=role, goal=goal, backstory="RAG stub", run=_run, llm=ollm)


def create_timeline_author_agent(llm: LLM) -> Agent:
    """
    Agent: timeline_author
    - Input: topic, audience, objectives, allowed_primitives, target_duration_min
    - Output: LessonTimeline JSON (strict)
    """
    role = "Lesson timeline author"
    goal = "Produce a LessonTimeline JSON (only JSON) using only the allowed primitives."

    async def _run(task: Task):
        payload = task.payload
        topic = payload.get("topic", "Topic")
        audience = payload.get("audience", "college")
        objectives = payload.get("objectives", [])
        allowed_primitives = payload.get("allowed_primitives", [])
        target_duration = payload.get("target_duration_min", 6)

        allowed_text = "\n".join(f"- {p}" for p in allowed_primitives)
        system = (
            "You are an educational author that must output ONLY a valid JSON object matching the LessonTimeline schema."
            "Schema: {lessonId, metadata:{title,audience}, timeline:[{id,startOffset_ms,duration_ms,layers:[{type,asset/primitive,params/content}],learningObjective,insertable}], insertPoints:[]}"
            "Constraints: Use ONLY the AllowedPrimitives provided. Each segment duration between 3000 and 30000 ms. Max 12 segments. Return JSON only."
        )
        user = (
            f"Topic: {topic}\nAudience: {audience}\nObjectives: {json.dumps(objectives)}\n"
            f"TargetDurationMin: {target_duration}\n\nAllowedPrimitives:\n{allowed_text}\n\n"
            "Generate a LessonTimeline JSON and return it only as JSON."
        )
        raw = await llm.call(system, user, temperature=0.0, max_tokens=1200)
        try:
            return json.loads(raw)
        except Exception:
            # fallback minimal timeline
            return {
                "lessonId": f"{topic.replace(' ', '_')}_{uuid.uuid4().hex[:6]}",
                "metadata": {"title": topic, "audience": audience},
                "timeline": [
                    {
                        "id": "seg-1",
                        "startOffset_ms": 0,
                        "duration_ms": 8000,
                        "layers": [
                            {"type": "svg", "asset": "battery.svg", "position": {"x": 80, "y": 120}},
                            {"type": "svg", "asset": "resistor.svg", "position": {"x": 300, "y": 120}},
                            {"type": "primitive", "primitive": "particleStream", "params": {"speed": 0.6, "count": 25, "direction": "leftToRight"}},
                            {"type": "text", "content": "V = I × R"}
                        ],
                        "learningObjective": "Introduce circuit and observe current flow",
                        "insertable": True
                    }
                ],
                "insertPoints": ["seg-1"]
            }

    return Agent(role=role, goal=goal, backstory="Composes timeline JSON", run=_run, llm=ollm)


def create_svg_generator_agent(llm: LLM, cdn_tool: CDNTool) -> Agent:
    """
    Agent: svg_generator (Method A)
    - Input: instruction (string), width, height
    - Output: {asset_id, asset_url}
    """
    role = "SVG generator"
    goal = "Generate a single <svg>...</svg> block ONLY and return asset URL after sanitizing and uploading."

    async def _run(task: Task):
        instr = task.payload.get("instruction", "diagram element")
        width = task.payload.get("width", 800)
        height = task.payload.get("height", 300)
        system = (
            "You are a strict SVG generator. Output ONLY a single <svg>...</svg> block and nothing else. Allowed tags:"
            " svg,g,rect,circle,ellipse,line,path,text,defs,use,animate,animateTransform. No script or external refs."
            " Root SVG must include width and height attributes."
        )
        user = f"Canvas: width={width} height={height}\nDraw: {instr}\nReturn only the <svg>...</svg> block."
        raw = await llm.call(system, user, temperature=0.0, max_tokens=1200)
        svg_block = extract_svg_block(raw)
        if not svg_block:
            raise ValueError("LLM did not return <svg> block")
        cleaned = sanitize_svg(svg_block)  # may raise ValueError
        # upload to CDN
        res = cdn_tool.run(cleaned)
        # return asset metadata
        return {"asset_id": res["asset_id"], "asset_url": res["asset_url"]}

    return Agent(role=role, goal=goal, backstory="Generates and uploads SVG", run=_run, llm=ollm)


# -----------------------------
# Validator helper (not an Agent)
# -----------------------------
def validate_timeline(tl: Dict[str, Any], allowed_primitives: List[str]) -> List[str]:
    errors: List[str] = []
    for seg in tl.get("timeline", []):
        dur = seg.get("duration_ms", 0)
        if dur < 3000 or dur > 30000:
            errors.append(f"segment {seg.get('id')} duration out of bounds: {dur}")
        for layer in seg.get("layers", []):
            if layer.get("type") == "primitive":
                prim = layer.get("primitive")
                if prim not in allowed_primitives and prim not in ["particleStream", "graphLine", "sliderControl", "textBox"]:
                    errors.append(f"primitive {prim} not allowed")
            if layer.get("type") == "svg":
                if not layer.get("assetUrl") and not layer.get("asset"):
                    errors.append(f"svg layer missing asset/assetUrl in segment {seg.get('id')}")
    return errors


# -----------------------------
# Assemble Crew and Tasks and run
# -----------------------------
def build_and_run_crew(user_prompt: str) -> Dict[str, Any]:
    # Tools
    primitive_tool = PrimitiveStoreTool()
    cdn_tool = CDNTool(base_url="https://cdn.example.com/auto")  # placeholder

    # Agents
    parse_agent = create_parse_agent(ollm)
    retrieve_agent = create_retrieve_agent(primitive_tool)
    timeline_agent = create_timeline_author_agent(ollm)
    svg_agent = create_svg_generator_agent(ollm, cdn_tool)

    # Build Crew
    crew = Crew(agents=[parse_agent, retrieve_agent, timeline_agent, svg_agent], verbose=True)

    # Task 1: parse prompt
    task_parse = Task(
        description=f"Parse user prompt: {user_prompt}",
        agent=parse_agent
    )

    # Kick off parse agent synchronously via crew (some crew implementations use kickoff())
    parse_result = crew.kickoff(task_parse)  # use crew.kickoff as in your example
    # extract parse_result to dict (depends on crew output shape)
    # We'll attempt similar extraction logic you used earlier:
    def _extract_json_from_result(result):
        if hasattr(result, "json_dict") and isinstance(result.json_dict, dict):
            return result.json_dict
        if hasattr(result, "raw") and isinstance(result.raw, str):
            try:
                return json.loads(result.raw)
            except:
                pass
        if isinstance(result, dict):
            return result
        # fallback: try str parse
        try:
            return json.loads(str(result))
        except:
            return None

    parsed = _extract_json_from_result(parse_result) or {"domain": "physics", "subdomain": "circuits", "topic": user_prompt, "audience": "college", "duration_min": 6, "objectives": []}

    domain = parsed.get("domain", "physics")
    subdomain = parsed.get("subdomain", "circuits")
    topic = parsed.get("topic", user_prompt)
    audience = parsed.get("audience", "college")
    duration_min = parsed.get("duration_min", 6)
    objectives = parsed.get("objectives", [])

    # Task 2: retrieve primitives
    task_retrieve = Task(
        description=f"Retrieve primitives for {domain}:{subdomain}",
        payload={"domain": domain, "subdomain": subdomain},
        agent=retrieve_agent
    )
    retrieve_result = crew.kickoff(task_retrieve)
    primitives_doc = _extract_json_from_result(retrieve_result) or primitive_tool.run(f"{domain}:{subdomain}")
    allowed_primitives = primitives_doc.get("allowed_primitives", [])

    # Task 3: author timeline
    task_timeline = Task(
        description=f"Author timeline for {topic}",
        payload={
            "topic": topic,
            "audience": audience,
            "objectives": objectives,
            "allowed_primitives": allowed_primitives,
            "target_duration_min": duration_min
        },
        agent=timeline_agent
    )
    timeline_raw = crew.kickoff(task_timeline)
    timeline = _extract_json_from_result(timeline_raw) or {}

    # Validate timeline & auto-generate missing SVGs
    errors = validate_timeline(timeline, allowed_primitives)
    for seg in timeline.get("timeline", []):
        for layer in seg.get("layers", []):
            if layer.get("type") == "svg" and not layer.get("assetUrl"):
                # call svg generator agent to produce asset_url
                label = layer.get("asset") or f"{topic} element"
                task_svg = Task(
                    description=f"Generate SVG for {label}",
                    payload={"instruction": f"{topic} - draw element {label} as simple diagram icon", "width": 400, "height": 120},
                    agent=svg_agent
                )
                svg_res = crew.kickoff(task_svg)
                svg_doc = _extract_json_from_result(svg_res)
                if svg_doc and isinstance(svg_doc, dict) and svg_doc.get("asset_url"):
                    layer["assetUrl"] = svg_doc["asset_url"]
                else:
                    errors.append(f"svg generation failed for layer asset {label}")

    # revalidate
    errors += validate_timeline(timeline, allowed_primitives)
    if errors:
        return {"status": "validation_failed", "errors": errors, "timeline": timeline}

    # persist session (in-memory)
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    SESSIONS[session_id] = {"id": session_id, "prompt": user_prompt, "meta": parsed, "timeline": timeline}

    return {"session_id": session_id, "timeline": timeline}


# -----------------------------
# Helper: Crew.kickoff shim for environments where Crew expects it
# -----------------------------
# If crew.kickoff isn't a method in your Crew implementation, you can add a small wrapper:
def _ensure_kickoff_on_crew(crew_obj: Crew):
    if not hasattr(crew_obj, "kickoff"):
        # Add a simple kickoff that runs the provided Task synchronously
        def kickoff(task: Task):
            # Attempt to find agent from task.agent attribute and run it
            agent = getattr(task, "agent", None)
            if not agent:
                raise RuntimeError("Task missing agent to run in kickoff shim")
            # If agent has run method call it, else call directly
            if hasattr(agent, "run"):
                coro = agent.run(task)
            else:
                coro = agent(task)
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)
        setattr(crew_obj, "kickoff", kickoff)


# -----------------------------
# ENTRYPOINT / Example usage
# -----------------------------
if __name__ == "__main__":
    # Build demo crew instance and ensure kickoff exists
    primitive_tool = PrimitiveStoreTool()
    cdn_tool = CDNTool(base_url="https://cdn.example.com/auto")
    parse_agent = create_parse_agent(ollm)
    retrieve_agent = create_retrieve_agent(primitive_tool)
    timeline_agent = create_timeline_author_agent(ollm)
    svg_agent = create_svg_generator_agent(ollm, cdn_tool)

    crew = Crew(agents=[parse_agent, retrieve_agent, timeline_agent, svg_agent], verbose=True)
    _ensure_kickoff_on_crew(crew)  # add kickoff if missing

    # Example prompt - change to test other topics
    user_prompt = "teach me Ohm's law with a slider to change resistance"
    result = build_and_run_crew(user_prompt)
    print(json.dumps(result, indent=2))
