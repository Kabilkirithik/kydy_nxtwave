from crewai import Agent, Task
from pydantic import BaseModel
from typing import List, Dict, Any

class RetrievedContext(BaseModel):
    allowed_primitives: List[str]
    reference_docs: List[Dict[str, Any]]
    domain_constraints: Dict[str, Any]

def create_retrieve_agent() -> Agent:
    return Agent(
        role="Context Retriever",
        goal="Retrieve relevant primitives and reference materials for lesson generation",
        backstory="""You are a knowledge retrieval specialist with access to a library 
        of visual primitives (SVG templates) and educational reference materials. 
        You know which primitives are appropriate for different domains and topics,
        and can provide relevant context for lesson creation.""",
        verbose=True,
        allow_delegation=False,
        llm="gpt-4o"
    )

def create_retrieve_task(agent: Agent, parsed_intent: Dict[str, Any], available_primitives: List[str]) -> Task:
    primitives_list = ", ".join(available_primitives) if available_primitives else "battery, resistor, wire, arrow, graph, particleStream, textBox"
    
    return Task(
        description=f"""Based on the parsed learning intent, retrieve appropriate primitives and context.

Parsed Intent:
- Domain: {parsed_intent.get('domain', 'unknown')}
- Subdomain: {parsed_intent.get('subdomain', 'unknown')}
- Topic: {parsed_intent.get('topic', 'unknown')}
- Audience: {parsed_intent.get('audience', 'unknown')}
- Objectives: {parsed_intent.get('objectives', [])}

Available Primitives in the system: {primitives_list}

Your task:
1. Select which primitives from the available list are appropriate for this topic
2. Provide any domain-specific constraints (e.g., color schemes for physics diagrams)
3. Include relevant reference context that will help generate an accurate lesson

Return ONLY a valid JSON object with these fields:
- allowed_primitives: List of primitive IDs suitable for this lesson
- reference_docs: List of brief reference notes relevant to the topic
- domain_constraints: Object with domain-specific rules (colors, styles, etc.)""",
        expected_output="""{
  "allowed_primitives": ["primitive1", "primitive2"],
  "reference_docs": [{"title": "string", "content": "string"}],
  "domain_constraints": {"color_scheme": "string", "style": "string"}
}""",
        agent=agent
    )
