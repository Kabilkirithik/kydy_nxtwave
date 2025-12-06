import os
import json
import sys
from typing import Dict, Any, Optional
from crewai import Crew, Process

from agents import (
    create_parse_agent, create_parse_task,
    create_retrieve_agent, create_retrieve_task,
    create_timeline_agent, create_timeline_task,
    create_svg_agent, create_svg_task,
    create_validator_agent, create_validator_task
)
from primitives import PrimitiveStore, SVGGenerator, SVGSanitizer

class LessonOrchestrator:
    def __init__(self):
        self.primitive_store = PrimitiveStore()
        
    def generate_lesson(self, prompt: str, session_id: str) -> Dict[str, Any]:
        try:
            parse_agent = create_parse_agent()
            parse_task = create_parse_task(parse_agent, prompt)
            
            parse_crew = Crew(
                agents=[parse_agent],
                tasks=[parse_task],
                process=Process.sequential,
                verbose=True
            )
            
            parse_result = parse_crew.kickoff()
            parsed_intent = self._extract_json(str(parse_result))
            
            if not parsed_intent:
                return {"error": "Failed to parse prompt intent", "session_id": session_id}
            
            domain = parsed_intent.get('domain', 'general')
            domain_primitives = self.primitive_store.get_primitives_by_domain(domain)
            available_primitive_ids = [p.id for p in domain_primitives]
            
            if not available_primitive_ids:
                available_primitive_ids = self.primitive_store.get_primitive_ids()
            
            retrieve_agent = create_retrieve_agent()
            retrieve_task = create_retrieve_task(retrieve_agent, parsed_intent, available_primitive_ids)
            
            retrieve_crew = Crew(
                agents=[retrieve_agent],
                tasks=[retrieve_task],
                process=Process.sequential,
                verbose=True
            )
            
            retrieve_result = retrieve_crew.kickoff()
            retrieved_context = self._extract_json(str(retrieve_result))
            
            allowed_primitives = retrieved_context.get('allowed_primitives', available_primitive_ids) if retrieved_context else available_primitive_ids
            reference_docs = retrieved_context.get('reference_docs', []) if retrieved_context else []
            
            timeline_agent = create_timeline_agent()
            timeline_task = create_timeline_task(timeline_agent, parsed_intent, allowed_primitives, reference_docs)
            
            timeline_crew = Crew(
                agents=[timeline_agent],
                tasks=[timeline_task],
                process=Process.sequential,
                verbose=True
            )
            
            timeline_result = timeline_crew.kickoff()
            timeline = self._extract_json(str(timeline_result))
            
            if not timeline:
                return {"error": "Failed to generate timeline", "session_id": session_id}
            
            if 'lessonId' not in timeline:
                timeline['lessonId'] = session_id
            
            timeline = self._generate_svg_assets(timeline, session_id)
            
            validator_agent = create_validator_agent()
            validator_task = create_validator_task(validator_agent, timeline, allowed_primitives)
            
            validator_crew = Crew(
                agents=[validator_agent],
                tasks=[validator_task],
                process=Process.sequential,
                verbose=True
            )
            
            validator_result = validator_crew.kickoff()
            validation = self._extract_json(str(validator_result))
            
            if validation and not validation.get('valid', True):
                return {
                    "error": "Timeline validation failed",
                    "validation_errors": validation.get('errors', []),
                    "session_id": session_id
                }
            
            return {
                "session_id": session_id,
                "status": "ready",
                "timeline": timeline,
                "parsed_intent": parsed_intent,
                "validation": validation
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "session_id": session_id,
                "status": "error"
            }
    
    def _generate_svg_assets(self, timeline: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        segments = timeline.get('timeline', [])
        
        for segment in segments:
            layers = segment.get('layers', [])
            for layer in layers:
                if layer.get('type') == 'primitive':
                    primitive_id = layer.get('primitive')
                    params = layer.get('params', {})
                    
                    if SVGGenerator.can_generate(primitive_id):
                        svg_content = SVGGenerator.generate(primitive_id, params)
                        if svg_content:
                            layer['assetUrl'] = f"/api/v1/assets/{session_id}/{primitive_id}.svg"
                            layer['svgContent'] = svg_content
                
                elif layer.get('type') == 'svg':
                    asset_name = layer.get('asset', '')
                    if asset_name:
                        primitive_id = asset_name.replace('.svg', '')
                        if SVGGenerator.can_generate(primitive_id):
                            svg_content = SVGGenerator.generate(primitive_id, {})
                            if svg_content:
                                layer['assetUrl'] = f"/api/v1/assets/{session_id}/{primitive_id}.svg"
                                layer['svgContent'] = svg_content
        
        return timeline
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        import re
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if isinstance(match, str):
                        clean_match = match.strip()
                        if clean_match.startswith('{'):
                            return json.loads(clean_match)
                except json.JSONDecodeError:
                    continue
        
        return None

def run_orchestrator(prompt: str, session_id: str) -> str:
    orchestrator = LessonOrchestrator()
    result = orchestrator.generate_lesson(prompt, session_id)
    return json.dumps(result)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: python orchestrator.py <prompt> <session_id>"}))
        sys.exit(1)
    
    prompt = sys.argv[1]
    session_id = sys.argv[2]
    
    result = run_orchestrator(prompt, session_id)
    print(result)
