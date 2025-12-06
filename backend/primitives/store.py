from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class PrimitiveMetadata(BaseModel):
    id: str
    type: str
    name: str
    domain: Optional[str] = None
    params_schema: Dict[str, Any]
    render_contract: str
    svg_template: Optional[str] = None

PRIMITIVE_REGISTRY: Dict[str, PrimitiveMetadata] = {
    "battery": PrimitiveMetadata(
        id="battery",
        type="svg_template",
        name="Battery",
        domain="physics",
        params_schema={
            "width": {"type": "number", "default": 60},
            "height": {"type": "number", "default": 30},
            "voltage": {"type": "string", "default": "9V"},
            "color": {"type": "string", "default": "#333"}
        },
        render_contract="must accept width, height, voltage label"
    ),
    "resistor": PrimitiveMetadata(
        id="resistor",
        type="svg_template",
        name="Resistor",
        domain="physics",
        params_schema={
            "width": {"type": "number", "default": 80},
            "height": {"type": "number", "default": 20},
            "resistance": {"type": "string", "default": "100Ω"},
            "color": {"type": "string", "default": "#8B4513"}
        },
        render_contract="must accept width, height, resistance label"
    ),
    "wire": PrimitiveMetadata(
        id="wire",
        type="svg_template",
        name="Wire",
        domain="physics",
        params_schema={
            "length": {"type": "number", "default": 100},
            "thickness": {"type": "number", "default": 2},
            "color": {"type": "string", "default": "#333"}
        },
        render_contract="must accept length, thickness, color"
    ),
    "arrow": PrimitiveMetadata(
        id="arrow",
        type="svg_template",
        name="Arrow",
        domain="general",
        params_schema={
            "length": {"type": "number", "default": 50},
            "direction": {"type": "string", "default": "right"},
            "color": {"type": "string", "default": "#007bff"},
            "label": {"type": "string", "default": ""}
        },
        render_contract="must accept length, direction, color, optional label"
    ),
    "particleStream": PrimitiveMetadata(
        id="particleStream",
        type="animated",
        name="Particle Stream",
        domain="physics",
        params_schema={
            "speed": {"type": "number", "default": 0.5},
            "count": {"type": "number", "default": 10},
            "color": {"type": "string", "default": "#00ff00"},
            "direction": {"type": "string", "default": "right"}
        },
        render_contract="must accept speed, count, particle color, direction"
    ),
    "graph": PrimitiveMetadata(
        id="graph",
        type="svg_template",
        name="Graph",
        domain="mathematics",
        params_schema={
            "width": {"type": "number", "default": 200},
            "height": {"type": "number", "default": 150},
            "xlabel": {"type": "string", "default": "x"},
            "ylabel": {"type": "string", "default": "y"},
            "data": {"type": "array", "default": []}
        },
        render_contract="must accept dimensions, axis labels, data points"
    ),
    "textBox": PrimitiveMetadata(
        id="textBox",
        type="svg_template",
        name="Text Box",
        domain="general",
        params_schema={
            "text": {"type": "string", "default": ""},
            "fontSize": {"type": "number", "default": 16},
            "fontColor": {"type": "string", "default": "#000"},
            "backgroundColor": {"type": "string", "default": "transparent"},
            "padding": {"type": "number", "default": 10}
        },
        render_contract="must accept text, font settings, background"
    ),
    "capacitor": PrimitiveMetadata(
        id="capacitor",
        type="svg_template",
        name="Capacitor",
        domain="physics",
        params_schema={
            "width": {"type": "number", "default": 40},
            "height": {"type": "number", "default": 60},
            "capacitance": {"type": "string", "default": "10μF"},
            "color": {"type": "string", "default": "#333"}
        },
        render_contract="must accept width, height, capacitance label"
    ),
    "ammeter": PrimitiveMetadata(
        id="ammeter",
        type="svg_template",
        name="Ammeter",
        domain="physics",
        params_schema={
            "size": {"type": "number", "default": 40},
            "value": {"type": "string", "default": "0A"},
            "color": {"type": "string", "default": "#333"}
        },
        render_contract="must accept size, display value"
    ),
    "voltmeter": PrimitiveMetadata(
        id="voltmeter",
        type="svg_template",
        name="Voltmeter",
        domain="physics",
        params_schema={
            "size": {"type": "number", "default": 40},
            "value": {"type": "string", "default": "0V"},
            "color": {"type": "string", "default": "#333"}
        },
        render_contract="must accept size, display value"
    )
}

class PrimitiveStore:
    def __init__(self):
        self.primitives = PRIMITIVE_REGISTRY.copy()
    
    def get_primitive(self, primitive_id: str) -> Optional[PrimitiveMetadata]:
        return self.primitives.get(primitive_id)
    
    def get_primitives_by_domain(self, domain: str) -> List[PrimitiveMetadata]:
        return [p for p in self.primitives.values() if p.domain == domain or p.domain == "general"]
    
    def get_all_primitives(self) -> List[PrimitiveMetadata]:
        return list(self.primitives.values())
    
    def get_primitive_ids(self) -> List[str]:
        return list(self.primitives.keys())
    
    def get_params_schema(self, primitive_id: str) -> Optional[Dict[str, Any]]:
        primitive = self.get_primitive(primitive_id)
        return primitive.params_schema if primitive else None
    
    def register_primitive(self, metadata: PrimitiveMetadata) -> None:
        self.primitives[metadata.id] = metadata
