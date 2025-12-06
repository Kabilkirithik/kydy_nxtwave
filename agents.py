# crewai_method_a_example.py
"""
CrewAI-style example (Method A - LLM prompt-only SVG generation)
Single-file demo: Agents, Tools, expected_output validation, kickoff shim.
Replace LLM api key and adjust model/provider as needed.
"""

import os
import json
import re
import uuid
import uuid as _uuid
from typing import Any, Dict, List, Optional, Tuple

# ---- Import crewai primitives (your environment should have crewai installed) ----
# If your installed crewai package uses different names or signatures, adapt accordingly.
try:
    from crewai import Agent, Task, Crew, LLM
    from crewai.tools import BaseTool
except Exception:
    # Minimal shims (for syntax-only test runs); replace with real crewai in production.
    from types import SimpleNamespace
    class BaseTool(SimpleNamespace): pass
    class Task(SimpleNamespace):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
    class Agent(SimpleNamespace):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
        async def run(self, task):
            return None
    class Crew:
        def __init__(self, **kwargs):
            self.agents = kwargs.get("agents", [])
            self.verbose = kwargs.get("verbose", False)
    class LLM:
        def __init__(self, model=None, api_key=None):
            self.model = model
            self.api_key = api_key
        async def call(self, system, user, temperature=0.0, max_tokens=500):
            raise RuntimeError("LLM shim called; replace with real LLM or install crewai.")

# ---- Security: set your LLM API key in env or here (DO NOT commit real keys) ----
OLLm_API_KEY = os.getenv("OLLM_API_KEY", "AIzaSyB9yrJA2CrqIwQsvd0u7PjAdP6ZMi9H0sE")
# Example LLM instantiation (match provider in your environment)
ollm = LLM(model="gpt-4o-mini", api_key=OLLm_API_KEY)

# -----------------------------
# Tools (Pydantic-friendly fields)
# -----------------------------
from pydantic import Field

class PrimitiveStoreTool(BaseTool):
    """
    Tool that returns allowed primitives for a domain:subdomain key.
    """
    name: str = "primitive_store"
    description: str = "Return allowed primitives and render contracts for a given domain/subdomain"
    mapping: dict = Field(default_factory=lambda: {
        "physics:circuits": {
            "allowed_primitives": [
                "battery.svg", "resistor.svg", "particleStream", "graphLine", "sliderControl", "textBox"
            ],
            "notes": "Demo primitives for circuits"
        }
    })

    def _run(self, domain_subdomain: str) -> Dict[str, Any]:
        return self.mapping.get(domain_subdomain, self.mapping["physics:circuits"])

    def run(self, domain_subdomain: str):
        return self._run(domain_subdomain)


class CDNTool(BaseTool):
    """
    In-memory CDN tool. Use Field(default_factory=dict) to avoid shared mutable defaults.
    """
    name: str = "cdn_uploader"
    description: str = "Uploads sanitized SVG string and returns an asset URL"
    base_url: str = "https://cdn.example.com/auto"
    store: dict = Field(default_factory=dict)

    def _run(self, svg_text: str, filename: Optional[str] = None) -> Dict[str, str]:
        filename = filename or f"svg_{_uuid.uuid4().hex[:8]}.svg"
        self.store[filename] = svg_text
        url = f"{self.base_url}/{filename}"
        return {"asset_id": filename, "asset_url": url}

    def run(self, svg_text: str, filename: Optional[str] = None) -> Dict[str, str]:
        return self._run(svg_text, filename)

# -----------------------------
# Helpers: SVG extraction & sanitization
# -----------------------------
from lxml import etree

ALLOWED_TAGS = {
    "svg", "g", "rect", "circle", "ellipse", "line", "path", "text",
    "defs", "use", "animate", "animateTransform", "title"
}
ATTR_RE = re.compile(r"^[a-zA-Z0-9:\-]+$")

def extract_svg_block(text: str) -> Optional[str]:
    if not isinstance(text, str):
        return None
    start = text.find("<svg")
    if start == -1:
        return None
    end = text.find("</svg>", start)
    if end == -1:
        return None
    return text[start:end + 6]

def sanitize_svg(svg_text: str) -> str:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, remove_comments=True)
    try:
        root = etree.fromstring(svg_text.encode("utf-8"), parser=parser)
    except Exception as e:
        raise ValueError(f"SVG parse error: {e}")

    for el in root.iter():
        tag = etree.QName(el.tag).localname
        if tag not in ALLOWED_TAGS:
            raise ValueError(f"Disallowed SVG tag: {tag}")

    # Remove any script elements (namespaced)
    for script in root.findall('.//{http://www.w3.org/2000/svg}script'):
        parent = script.getparent()
        if parent is not None:
            parent.remove(script)

    # sanitize attributes
    for el in root.iter():
        for a in list(el.attrib):
            if a.lower().startswith("on"):
                del el.attrib[a]; continue
            val = el.attrib[a]
            if isinstance(val, str) and ("http:" in val or "https:" in val or "javascript:" in val):
                del el.attrib[a]; continue
            if not ATTR_RE.match(a):
                del el.attrib[a]; continue

    if "width" not in root.attrib or "height" not in root.attrib:
        raise ValueError("SVG must include width and height attributes on root <svg>")

    cleaned = etree.tostring(root, encoding="utf-8").decode("utf-8")
    return cleaned

# -----------------------------
# Agents (create factory functions)
# -----------------------------

def create_parse_agent(llm: LLM) -> Agent:
    role = "Prompt classifier"
    goal = "Extract domain, subdomain, topic, audience, duration_min and objectives; return JSON only."

    async def _run(task: Task):
        prompt_text = getattr(task, "description", None) or (getattr(task, "payload", {}) or {}).get("prompt", "")
        system = ("You are a classifier. Return ONLY a JSON object with keys: "
                  '"domain","subdomain","topic","audience","duration_min","objectives".')
        user = f'Classify this user prompt: "{prompt_text}"\nReturn JSON only.'
        raw = await llm.call(system, user, temperature=0.0, max_tokens=250)
        try:
            return json.loads(raw)
        except Exception:
            return {
                "domain": "physics",
                "subdomain": "circuits",
                "topic": prompt_text,
                "audience": "college",
                "duration_min": 6,
                "objectives": []
            }

    return Agent(role=role, goal=goal, backstory="classifier", run=_run, llm=ollm)

def create_retrieve_agent(primitive_tool: PrimitiveStoreTool) -> Agent:
    role = "Primitive retriever"
    goal = "Given domain:subdomain return allowed primitives via tool."

    async def _run(task: Task):
        payload = getattr(task, "payload", {}) or {}
        domain = payload.get("domain", "physics")
        subdomain = payload.get("subdomain", "circuits")
        key = f"{domain}:{subdomain}"
        doc = primitive_tool.run(key)
        return doc

    return Agent(role=role, goal=goal, backstory="primitive retriever", run=_run, llm=ollm)

def create_timeline_author_agent(llm: LLM) -> Agent:
    role = "Lesson timeline author"
    goal = "Produce LessonTimeline JSON using only allowed primitives."

    async def _run(task: Task):
        payload = getattr(task, "payload", {}) or {}
        topic = payload.get("topic", "Topic")
        audience = payload.get("audience", "college")
        objectives = payload.get("objectives", [])
        allowed_primitives = payload.get("allowed_primitives", [])
        target_duration = payload.get("target_duration_min", 6)

        allowed_text = "\n".join(f"- {p}" for p in allowed_primitives)
        system = ("You are an educational author that must output ONLY a valid JSON object matching the LessonTimeline schema.\n"
                  "Schema: {lessonId, metadata:{title,audience}, timeline:[{id,startOffset_ms,duration_ms,layers:[{type,asset/primitive,params/content}],learningObjective,insertable}], insertPoints:[]}\n"
                  "Constraints: Use ONLY the AllowedPrimitives provided. Each segment duration between 3000 and 30000 ms. Max 12 segments. Return JSON only.")
        user = (f"Topic: {topic}\nAudience: {audience}\nObjectives: {json.dumps(objectives)}\n"
                f"TargetDurationMin: {target_duration}\n\nAllowedPrimitives:\n{allowed_text}\n\nGenerate a LessonTimeline JSON and return it only as JSON.")
        raw = await llm.call(system, user, temperature=0.0, max_tokens=1200)
        try:
            return json.loads(raw)
        except Exception:
            # fallback minimal
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

    return Agent(role=role, goal=goal, backstory="timeline author", run=_run, llm=ollm)

def create_svg_generator_agent(llm: LLM, cdn_tool: CDNTool) -> Agent:
    role = "SVG generator"
    goal = "Generate a single <svg>...</svg> block ONLY and return asset_url after sanitizing/upload."

    async def _run(task: Task):
        payload = getattr(task, "payload", {}) or {}
        instr = payload.get("instruction", "diagram element")
        width = payload.get("width", 800)
        height = payload.get("height", 300)
        system = ("You are a strict SVG generator. Output ONLY a single <svg>...</svg> block and nothing else.\n"
                  "Allowed tags: svg,g,rect,circle,ellipse,line,path,text,defs,use,animate,animateTransform.\n"
                  "No script or external refs. Root SVG must include width and height attributes.")
        user = f"Canvas: width={width} height={height}\nDraw: {instr}\nReturn only the <svg>...</svg> block."
        raw = await llm.call(system, user, temperature=0.0, max_tokens=1200)
        svg_block = extract_svg_block(raw)
        if not svg_block:
            raise ValueError("LLM did not return <svg> block")
        cleaned = sanitize_svg(svg_block)  # may raise
        res = cdn_tool.run(cleaned)
        return {"asset_id": res["asset_id"], "asset_url": res["asset_url"]}

    return Agent(role=role, goal=goal, backstory="svg generator", run=_run, llm=ollm)

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
# Lightweight expected_output comparator & run helper
# -----------------------------
def _is_json_string(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except Exception:
        return False

def compare_expected(actual: Any, expected_spec: Any) -> Tuple[bool, str]:
    if expected_spec is None:
        return True, "no expected_spec"

    if hasattr(actual, "json_dict") and isinstance(actual.json_dict, dict):
        actual = actual.json_dict
    elif hasattr(actual, "raw") and isinstance(actual.raw, str) and _is_json_string(actual.raw):
        actual = json.loads(actual.raw)

    if isinstance(expected_spec, str) and expected_spec.startswith("REGEX:"):
        pat = expected_spec[len("REGEX:"):]
        ok = bool(re.search(pat, str(actual)))
        return ok, f"regex {pat!r} {'matched' if ok else 'did not match'}"

    if isinstance(expected_spec, str) and _is_json_string(expected_spec):
        expected_spec = json.loads(expected_spec)

    def _match(a, e, path=""):
        if e is None:
            return True, ""
        if isinstance(e, dict):
            if not isinstance(a, dict):
                return False, f"expected dict at {path}"
            for k, v in e.items():
                if k not in a:
                    return False, f"missing key {path + '.' + k if path else k}"
                if v == "<ANY>":
                    continue
                ok, msg = _match(a[k], v, path + "." + k if path else k)
                if not ok:
                    return False, msg
            return True, ""
        if isinstance(e, list):
            if not isinstance(a, list):
                return False, f"expected list at {path}"
            if len(a) != len(e):
                return False, f"list length mismatch at {path}: expected {len(e)} got {len(a)}"
            for i, (ai, ei) in enumerate(zip(a, e)):
                ok, msg = _match(ai, ei, f"{path}[{i}]")
                if not ok:
                    return False, msg
            return True, ""
        if a == e:
            return True, ""
        if isinstance(e, (int, float)) and isinstance(a, (int, float)):
            return float(a) == float(e), f"value mismatch at {path}"
        return False, f"value mismatch at {path}: expected {e!r} got {a!r}"

    ok, msg = _match(actual, expected_spec, "")
    return ok, (msg or "ok")

def run_and_assert(crew_obj: Crew, task: Task):
    """
    Calls crew_obj.kickoff(task) and compares output to task.expected_output if provided.
    Raises AssertionError on mismatch.
    """
    res = crew_obj.kickoff(task)
    expected = getattr(task, "expected_output", None)
    ok, msg = compare_expected(res, expected)
    if not ok:
        raise AssertionError(f"Task '{getattr(task,'description',str(task))}' failed expected_output check: {msg}\nResult: {res}")
    return res

# -----------------------------
# Ensure kickoff shim exists (robust)
# -----------------------------
def _ensure_kickoff_on_crew(crew_obj: Crew):
    if not hasattr(crew_obj, "kickoff"):
        def kickoff(task: Task):
            agent = getattr(task, "agent", None)
            if not agent:
                raise RuntimeError("Task missing agent to run in kickoff shim")
            import asyncio
            run_fn = getattr(agent, "run", None)
            if callable(run_fn) and asyncio.iscoroutinefunction(run_fn):
                return asyncio.get_event_loop().run_until_complete(run_fn(task))
            if asyncio.iscoroutinefunction(agent):
                return asyncio.get_event_loop().run_until_complete(agent(task))
            if callable(run_fn):
                return run_fn(task)
            return agent(task)
        setattr(crew_obj, "kickoff", kickoff)

# -----------------------------
# Main orchestration: build_and_run_crew()
# -----------------------------
SESSIONS: Dict[str, Any] = {}

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
    try:
        return json.loads(str(result))
    except:
        return None

def build_and_run_crew(user_prompt: str) -> Dict[str, Any]:
    # Tools
    primitive_tool = PrimitiveStoreTool()
    cdn_tool = CDNTool(base_url="https://cdn.example.com/auto")

    # Agents
    parse_agent = create_parse_agent(ollm)
    retrieve_agent = create_retrieve_agent(primitive_tool)
    timeline_agent = create_timeline_author_agent(ollm)
    svg_agent = create_svg_generator_agent(ollm, cdn_tool)

    # Build Crew
    crew = Crew(agents=[parse_agent, retrieve_agent, timeline_agent, svg_agent], verbose=True)
    _ensure_kickoff_on_crew(crew)

    # Task 1: parse prompt (expected_output provided at construction)
    task_parse = Task(
        description=f"Parse user prompt: {user_prompt}",
        expected_output=json.dumps({
            "domain": "physics",
            "subdomain": "circuits",
            "topic": "Ohm's law" if ("ohm" in user_prompt.lower() or "ohm's" in user_prompt.lower()) else "<ANY>",
            "audience": "<ANY>",
            "duration_min": "<ANY>",
            "objectives": "<ANY>"
        }),
        agent=parse_agent
    )
    parse_result = run_and_assert(crew, task_parse)
    parsed = _extract_json_from_result(parse_result) or {"domain": "physics", "subdomain": "circuits", "topic": user_prompt, "audience": "college", "duration_min": 6, "objectives": []}

    domain = parsed.get("domain", "physics")
    subdomain = parsed.get("subdomain", "circuits")
    topic = parsed.get("topic", user_prompt)
    audience = parsed.get("audience", "college")
    duration_min = parsed.get("duration_min", 6)
    objectives = parsed.get("objectives", [])

    # Task 2: retrieve primitives (expected_output provided at construction)
    task_retrieve = Task(
        description=f"Retrieve primitives for {domain}:{subdomain}",
        payload={"domain": domain, "subdomain": subdomain},
        expected_output=json.dumps({
            "allowed_primitives": [
                "battery.svg",
                "resistor.svg",
                "particleStream"
            ]
        }),
        agent=retrieve_agent
    )
    retrieve_result = run_and_assert(crew, task_retrieve)
    primitives_doc = _extract_json_from_result(retrieve_result) or primitive_tool.run(f"{domain}:{subdomain}")
    allowed_primitives = primitives_doc.get("allowed_primitives", [])

    # Task 3: timeline author (expected_output provided at construction)
    task_timeline = Task(
        description=f"Author timeline for {topic}",
        payload={"topic": topic, "audience": audience, "objectives": objectives, "allowed_primitives": allowed_primitives, "target_duration_min": duration_min},
        expected_output=json.dumps({
            "lessonId": "<ANY>",
            "metadata": {"title": "<ANY>", "audience": "<ANY>"},
            "timeline": "<ANY>",
            "insertPoints": "<ANY>"
        }),
        agent=timeline_agent
    )
    timeline_raw = run_and_assert(crew, task_timeline)
    timeline = _extract_json_from_result(timeline_raw) or {}

    # Validate timeline & generate missing SVGs
    errors = validate_timeline(timeline, allowed_primitives)
    for seg in timeline.get("timeline", []):
        for layer in seg.get("layers", []):
            if layer.get("type") == "svg" and not layer.get("assetUrl"):
                label = layer.get("asset") or f"{topic} element"
                task_svg = Task(
                    description=f"Generate SVG for {label}",
                    payload={"instruction": f"{topic} - draw element {label} as simple diagram icon", "width": 400, "height": 120},
                    expected_output=json.dumps({"asset_url": "REGEX:^https?://.*cdn\\.example\\.com/.*\\.svg$"}),
                    agent=svg_agent
                )
                try:
                    svg_res = run_and_assert(crew, task_svg)
                except AssertionError as e:
                    errors.append(str(e))
                    continue
                svg_doc = _extract_json_from_result(svg_res)
                if svg_doc and isinstance(svg_doc, dict):
                    asset_url = svg_doc.get("asset_url") or svg_doc.get("assetUrl") or svg_doc.get("asset")
                    if asset_url:
                        layer["assetUrl"] = asset_url
                    else:
                        errors.append(f"svg generation returned unexpected shape for {label}: {svg_doc}")
                else:
                    errors.append(f"svg generation failed for layer asset {label}")

    # revalidate
    errors += validate_timeline(timeline, allowed_primitives)
    if errors:
        return {"status": "validation_failed", "errors": errors, "timeline": timeline}

    # persist session
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    SESSIONS[session_id] = {"id": session_id, "prompt": user_prompt, "meta": parsed, "timeline": timeline}
    return {"session_id": session_id, "timeline": timeline}

# -----------------------------
# CLI demo
# -----------------------------
if __name__ == "__main__":
    primitive_tool = PrimitiveStoreTool()
    cdn_tool = CDNTool(base_url="https://cdn.example.com/auto")
    parse_agent = create_parse_agent(ollm)
    retrieve_agent = create_retrieve_agent(primitive_tool)
    timeline_agent = create_timeline_author_agent(ollm)
    svg_agent = create_svg_generator_agent(ollm, cdn_tool)

    crew = Crew(agents=[parse_agent, retrieve_agent, timeline_agent, svg_agent], verbose=True)
    _ensure_kickoff_on_crew(crew)

    user_prompt = "teach me Ohm's law with a slider to change resistance"
    print("Running build_and_run_crew() for prompt:", user_prompt)
    try:
        result = build_and_run_crew(user_prompt)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print("Error during run:", type(e).__name__, e)
