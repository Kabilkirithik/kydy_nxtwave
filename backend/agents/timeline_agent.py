from crewai import Agent, Task
from typing import Dict, Any, List

def create_timeline_agent() -> Agent:
    return Agent(
        role="Lesson Timeline Composer",
        goal="Create structured, animated lesson timelines using visual primitives",
        backstory="""You are an expert educational content designer who creates 
        engaging animated lesson timelines. You understand how to sequence 
        educational content, layer visual elements effectively, and create 
        clear learning progressions. You always use the primitives provided 
        to create visually rich, educational animations.""",
        verbose=True,
        allow_delegation=False,
        llm="gemini/gemini-2.5-flash"
    )

def create_timeline_task(
    agent: Agent, 
    parsed_intent: Dict[str, Any], 
    allowed_primitives: List[str],
    reference_docs: List[Dict[str, Any]]
) -> Task:
    refs_text = "\n".join([f"- {doc.get('title', 'Reference')}: {doc.get('content', '')}" for doc in reference_docs]) if reference_docs else "No additional references"
    
    return Task(
        description=f"""Create a complete lesson timeline for the following educational content:

Topic: {parsed_intent.get('topic', 'unknown')}
Domain: {parsed_intent.get('domain', 'unknown')}
Audience: {parsed_intent.get('audience', 'unknown')}
Duration: {parsed_intent.get('duration_min', 6)} minutes
Learning Objectives: {parsed_intent.get('objectives', [])}

Allowed Primitives: {', '.join(allowed_primitives)}

Reference Context:
{refs_text}

Create a LessonTimeline JSON with:
1. A unique lessonId
2. Metadata with title, audience, and duration
3. Timeline array with 3-6 segments, each containing:
   - id: unique segment identifier
   - startOffset_ms: when segment starts (in milliseconds)
   - duration_ms: segment duration (in milliseconds, typically 5000-15000)
   - layers: array of visual layers (svg, primitive, or text types)
   - learningObjective: what this segment teaches
   - insertable: boolean indicating if user can insert content here

Each layer should have:
- type: "svg" | "primitive" | "text"
- For svg: asset (filename), position (x, y coordinates)
- For primitive: primitive (name), params (configuration object)
- For text: content (the text to display), position (x, y)

Return ONLY valid JSON matching this schema.""",
        expected_output="""{
  "lessonId": "string",
  "metadata": {"title": "string", "audience": "string", "duration_min": 6},
  "timeline": [
    {
      "id": "string",
      "startOffset_ms": 0,
      "duration_ms": 8000,
      "layers": [
        {"type": "svg", "asset": "string", "position": {"x": 0, "y": 0}},
        {"type": "primitive", "primitive": "string", "params": {}},
        {"type": "text", "content": "string", "position": {"x": 0, "y": 0}}
      ],
      "learningObjective": "string",
      "insertable": true
    }
  ],
  "insertPoints": ["segment-id"]
}""",
        agent=agent
    )
