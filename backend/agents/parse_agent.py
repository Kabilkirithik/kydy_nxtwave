from crewai import Agent, Task
from pydantic import BaseModel
from typing import List, Optional

class ParsedIntent(BaseModel):
    domain: str
    subdomain: str
    topic: str
    audience: str
    duration_min: int
    objectives: List[str]

def create_parse_agent() -> Agent:
    return Agent(
        role="Intent Parser",
        goal="Extract structured learning intent from natural language prompts",
        backstory="""You are an expert at understanding educational requests. 
        You can identify the domain (science, math, history, etc.), 
        the specific topic, the target audience level, and learning objectives 
        from simple user prompts like 'teach me Ohm's law'.""",
        verbose=True,
        allow_delegation=False,
        llm="gpt-4o"
    )

def create_parse_task(agent: Agent, prompt: str) -> Task:
    return Task(
        description=f"""Parse the following user prompt and extract structured intent:

Prompt: "{prompt}"

You MUST return a valid JSON object with these exact fields:
- domain: The broad subject area (e.g., "physics", "mathematics", "biology")
- subdomain: A more specific area (e.g., "circuits", "algebra", "genetics")
- topic: The specific topic being requested (e.g., "Ohm's law", "quadratic equations")
- audience: The target audience level (e.g., "beginner", "college", "high school")
- duration_min: Recommended lesson duration in minutes (integer, typically 3-10)
- objectives: A list of 2-4 specific learning objectives

Return ONLY the JSON object, no additional text or markdown formatting.""",
        expected_output="""{
  "domain": "string",
  "subdomain": "string", 
  "topic": "string",
  "audience": "string",
  "duration_min": 6,
  "objectives": ["objective1", "objective2"]
}""",
        agent=agent
    )
