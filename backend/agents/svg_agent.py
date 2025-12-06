from crewai import Agent, Task
from typing import Dict, Any, List

def create_svg_agent() -> Agent:
    return Agent(
        role="SVG Asset Generator",
        goal="Generate or retrieve SVG assets for lesson visualization",
        backstory="""You are a visual asset specialist who can generate 
        SVG markup for educational diagrams. You understand parametric 
        SVG generation and can create clean, animatable SVG code for 
        various educational primitives like circuits, graphs, arrows, 
        and scientific diagrams.""",
        verbose=True,
        allow_delegation=False,
        llm="gemini/gemini-2.5-flash"
    )

def create_svg_task(agent: Agent, primitive_id: str, params: Dict[str, Any]) -> Task:
    return Task(
        description=f"""Generate an SVG asset for the following primitive:

Primitive ID: {primitive_id}
Parameters: {params}

Requirements:
1. Generate clean, valid SVG markup
2. Include width and height attributes on the root svg element
3. Use only safe SVG elements (svg, g, rect, circle, ellipse, line, path, text, defs, use, animate, animateTransform)
4. NO script tags or on* event handlers
5. Include basic styling that can be animated
6. Make elements identifiable with id attributes for animation targeting

Return ONLY the SVG markup, starting with <svg and ending with </svg>.
Do not include any markdown code blocks or additional text.""",
        expected_output="""<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
  <!-- SVG content here -->
</svg>""",
        agent=agent
    )

def create_batch_svg_task(agent: Agent, layers_needing_assets: List[Dict[str, Any]]) -> Task:
    layers_desc = "\n".join([
        f"- {i+1}. Type: {layer.get('type')}, Asset: {layer.get('asset', layer.get('primitive', 'N/A'))}, Params: {layer.get('params', {})}"
        for i, layer in enumerate(layers_needing_assets)
    ])
    
    return Task(
        description=f"""Generate SVG assets for the following timeline layers:

{layers_desc}

For each layer that needs an SVG asset, generate clean, valid SVG markup.

Requirements for each SVG:
1. Include width="200" height="150" on root svg element
2. Use only safe elements: svg, g, rect, circle, ellipse, line, path, text, defs, use, animate
3. NO script tags or event handlers
4. Make elements animatable with CSS classes or id attributes

Return a JSON object where keys are the layer indices (1, 2, 3...) and values are the SVG strings.
Example: {{"1": "<svg>...</svg>", "2": "<svg>...</svg>"}}""",
        expected_output="""{
  "1": "<svg width='200' height='150'>...</svg>",
  "2": "<svg width='200' height='150'>...</svg>"
}""",
        agent=agent
    )
