from crewai import Agent, Task
from typing import Dict, Any, List
import json

def create_validator_agent() -> Agent:
    return Agent(
        role="Timeline Validator",
        goal="Validate lesson timelines against schema and safety requirements",
        backstory="""You are a quality assurance specialist who validates 
        educational content and ensures all generated timelines meet strict 
        schema requirements and safety standards. You check for proper 
        structure, valid primitives, safe SVG content, and educational quality.""",
        verbose=True,
        allow_delegation=False,
        llm="gemini/gemini-2.5-flash"
    )

def create_validator_task(
    agent: Agent, 
    timeline: Dict[str, Any], 
    allowed_primitives: List[str]
) -> Task:
    return Task(
        description=f"""Validate the following lesson timeline:

Timeline JSON:
{json.dumps(timeline, indent=2)}

Allowed Primitives: {', '.join(allowed_primitives)}

Validation checks to perform:
1. Schema Validation:
   - lessonId exists and is a string
   - metadata contains title, audience, duration_min
   - timeline is an array with at least 1 segment
   - Each segment has id, startOffset_ms, duration_ms, layers

2. Timing Validation:
   - startOffset_ms >= 0
   - duration_ms between 1000 and 60000
   - Segments don't overlap inappropriately

3. Layer Validation:
   - Each layer has valid type (svg, primitive, text)
   - Primitives used are in the allowed list
   - Positions have valid x, y coordinates

4. Content Validation:
   - No empty text content
   - Learning objectives are meaningful
   - Appropriate number of layers per segment

Return a JSON object with:
- valid: boolean
- errors: array of error messages (empty if valid)
- warnings: array of non-critical issues
- score: quality score 0-100""",
        expected_output="""{
  "valid": true,
  "errors": [],
  "warnings": ["optional warning messages"],
  "score": 85
}""",
        agent=agent
    )
