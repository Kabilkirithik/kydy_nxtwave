from typing import Dict, Any, Optional
import re

def safe_number(value: Any, default: float = 0) -> float:
    """Safely convert a value to a number, handling string inputs from LLM."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            clean = ''.join(c for c in value if c.isdigit() or c in '.-')
            return float(clean) if clean else default
        except (ValueError, TypeError):
            return default
    return default

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to an integer."""
    return int(safe_number(value, default))

class SVGSanitizer:
    ALLOWED_TAGS = {
        'svg', 'g', 'rect', 'circle', 'ellipse', 'line', 'path', 'polygon', 'polyline',
        'text', 'tspan', 'defs', 'use', 'animate', 'animateTransform', 'animateMotion',
        'clipPath', 'mask', 'linearGradient', 'radialGradient', 'stop', 'filter',
        'feGaussianBlur', 'feOffset', 'feMerge', 'feMergeNode', 'title', 'desc'
    }
    
    FORBIDDEN_ATTRS = {
        'onclick', 'onload', 'onerror', 'onmouseover', 'onmouseout', 'onmousedown',
        'onmouseup', 'onfocus', 'onblur', 'onchange', 'onsubmit', 'onreset',
        'onkeydown', 'onkeypress', 'onkeyup', 'ondblclick', 'oncontextmenu'
    }
    
    @classmethod
    def sanitize(cls, svg_content: str) -> str:
        if not svg_content or not svg_content.strip():
            return ""
        
        svg_content = re.sub(r'<script[^>]*>.*?</script>', '', svg_content, flags=re.DOTALL | re.IGNORECASE)
        
        for attr in cls.FORBIDDEN_ATTRS:
            svg_content = re.sub(rf'\s{attr}\s*=\s*["\'][^"\']*["\']', '', svg_content, flags=re.IGNORECASE)
        
        svg_content = re.sub(r'javascript:', '', svg_content, flags=re.IGNORECASE)
        svg_content = re.sub(r'data:', '', svg_content, flags=re.IGNORECASE)
        svg_content = re.sub(r'vbscript:', '', svg_content, flags=re.IGNORECASE)
        
        if 'width=' not in svg_content.lower():
            svg_content = svg_content.replace('<svg', '<svg width="200"', 1)
        if 'height=' not in svg_content.lower():
            svg_content = svg_content.replace('<svg', '<svg height="150"', 1)
        
        return svg_content.strip()
    
    @classmethod
    def is_valid(cls, svg_content: str) -> bool:
        if not svg_content:
            return False
        if '<script' in svg_content.lower():
            return False
        for attr in cls.FORBIDDEN_ATTRS:
            if attr.lower() in svg_content.lower():
                return False
        if not svg_content.strip().startswith('<svg'):
            return False
        if not svg_content.strip().endswith('</svg>'):
            return False
        return True

class SVGGenerator:
    @staticmethod
    def generate_battery(params: Dict[str, Any]) -> str:
        width = safe_number(params.get('width'), 60)
        height = safe_number(params.get('height'), 30)
        voltage = str(params.get('voltage', '9V'))
        color = str(params.get('color', '#333'))
        
        return f'''<svg width="{width + 20}" height="{height + 20}" xmlns="http://www.w3.org/2000/svg">
  <rect x="5" y="5" width="{width}" height="{height}" fill="none" stroke="{color}" stroke-width="2" rx="2"/>
  <rect x="{width + 5}" y="{height/3 + 5}" width="8" height="{height/3}" fill="{color}"/>
  <line x1="15" y1="{height/2 + 5}" x2="25" y2="{height/2 + 5}" stroke="{color}" stroke-width="3"/>
  <line x1="{width - 10}" y1="{height/3 + 5}" x2="{width - 10}" y2="{2*height/3 + 5}" stroke="{color}" stroke-width="2"/>
  <line x1="{width - 15}" y1="{height/2.5 + 5}" x2="{width - 15}" y2="{height/1.5 + 5}" stroke="{color}" stroke-width="2"/>
  <text x="{width/2}" y="{height + 18}" text-anchor="middle" font-size="10" fill="{color}">{voltage}</text>
</svg>'''

    @staticmethod
    def generate_resistor(params: Dict[str, Any]) -> str:
        width = safe_number(params.get('width'), 80)
        height = safe_number(params.get('height'), 20)
        resistance = str(params.get('resistance', '100Ω'))
        color = str(params.get('color', '#8B4513'))
        
        zigzag_points = []
        segments = 6
        seg_width = (width - 20) / segments
        for i in range(segments + 1):
            x = 10 + i * seg_width
            y = height/2 if i % 2 == 0 else (5 if i % 4 == 1 else height - 5)
            zigzag_points.append(f"{x},{y}")
        
        return f'''<svg width="{width}" height="{height + 15}" xmlns="http://www.w3.org/2000/svg">
  <line x1="0" y1="{height/2}" x2="10" y2="{height/2}" stroke="{color}" stroke-width="2"/>
  <polyline points="{' '.join(zigzag_points)}" fill="none" stroke="{color}" stroke-width="2"/>
  <line x1="{width - 10}" y1="{height/2}" x2="{width}" y2="{height/2}" stroke="{color}" stroke-width="2"/>
  <text x="{width/2}" y="{height + 12}" text-anchor="middle" font-size="9" fill="{color}">{resistance}</text>
</svg>'''

    @staticmethod
    def generate_wire(params: Dict[str, Any]) -> str:
        length = safe_number(params.get('length'), 100)
        thickness = safe_number(params.get('thickness'), 2)
        color = str(params.get('color', '#333'))
        
        return f'''<svg width="{length}" height="10" xmlns="http://www.w3.org/2000/svg">
  <line x1="0" y1="5" x2="{length}" y2="5" stroke="{color}" stroke-width="{thickness}"/>
</svg>'''

    @staticmethod
    def generate_arrow(params: Dict[str, Any]) -> str:
        length = safe_number(params.get('length'), 50)
        direction = str(params.get('direction', 'right'))
        color = str(params.get('color', '#007bff'))
        label = str(params.get('label', ''))
        
        if direction == 'right':
            path = f"M0,10 L{length-10},10 L{length-10},5 L{length},12.5 L{length-10},20 L{length-10},15 L0,15 Z"
        elif direction == 'left':
            path = f"M{length},10 L10,10 L10,5 L0,12.5 L10,20 L10,15 L{length},15 Z"
        elif direction == 'up':
            path = f"M10,{length} L10,10 L5,10 L12.5,0 L20,10 L15,10 L15,{length} Z"
        else:
            path = f"M10,0 L10,{length-10} L5,{length-10} L12.5,{length} L20,{length-10} L15,{length-10} L15,0 Z"
        
        label_svg = f'<text x="{length/2}" y="35" text-anchor="middle" font-size="10" fill="{color}">{label}</text>' if label else ''
        
        return f'''<svg width="{length + 10}" height="45" xmlns="http://www.w3.org/2000/svg">
  <path d="{path}" fill="{color}"/>
  {label_svg}
</svg>'''

    @staticmethod
    def generate_particle_stream(params: Dict[str, Any]) -> str:
        speed = safe_number(params.get('speed'), 0.5)
        count = safe_int(params.get('count'), 10)
        color = str(params.get('color', '#00ff00'))
        direction = str(params.get('direction', 'right'))
        
        particles = []
        for i in range(min(count, 20)):
            cx = 10 + (i * 15) % 180
            cy = 15 + (i * 7) % 20
            delay = i * 0.1
            dur = 2 / max(speed, 0.1)
            particles.append(f'''<circle cx="{cx}" cy="{cy}" r="3" fill="{color}" opacity="0.7">
    <animate attributeName="cx" values="{cx};{cx + 50};{cx}" dur="{dur}s" repeatCount="indefinite" begin="{delay}s"/>
    <animate attributeName="opacity" values="0.7;1;0.7" dur="{dur}s" repeatCount="indefinite" begin="{delay}s"/>
  </circle>''')
        
        return f'''<svg width="200" height="50" xmlns="http://www.w3.org/2000/svg">
  {''.join(particles)}
</svg>'''

    @staticmethod
    def generate_graph(params: Dict[str, Any]) -> str:
        width = safe_number(params.get('width'), 200)
        height = safe_number(params.get('height'), 150)
        xlabel = str(params.get('xlabel', 'x'))
        ylabel = str(params.get('ylabel', 'y'))
        
        return f'''<svg width="{width + 40}" height="{height + 40}" xmlns="http://www.w3.org/2000/svg">
  <line x1="30" y1="10" x2="30" y2="{height + 10}" stroke="#333" stroke-width="2"/>
  <line x1="30" y1="{height + 10}" x2="{width + 30}" y2="{height + 10}" stroke="#333" stroke-width="2"/>
  <polygon points="30,5 25,15 35,15" fill="#333"/>
  <polygon points="{width + 35},{height + 10} {width + 25},{height + 5} {width + 25},{height + 15}" fill="#333"/>
  <text x="15" y="{height/2 + 10}" text-anchor="middle" font-size="12" fill="#333" transform="rotate(-90, 15, {height/2 + 10})">{ylabel}</text>
  <text x="{width/2 + 30}" y="{height + 35}" text-anchor="middle" font-size="12" fill="#333">{xlabel}</text>
</svg>'''

    @staticmethod
    def generate_text_box(params: Dict[str, Any]) -> str:
        text = str(params.get('text', ''))
        font_size = safe_number(params.get('fontSize'), 16)
        font_color = str(params.get('fontColor', '#000'))
        bg_color = str(params.get('backgroundColor', 'transparent'))
        padding = safe_number(params.get('padding'), 10)
        
        width = max(len(text) * font_size * 0.6 + padding * 2, 50)
        height = font_size + padding * 2
        
        return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{width}" height="{height}" fill="{bg_color}" rx="4"/>
  <text x="{padding}" y="{height/2 + font_size/3}" font-size="{font_size}" fill="{font_color}">{text}</text>
</svg>'''

    @staticmethod
    def generate_capacitor(params: Dict[str, Any]) -> str:
        width = safe_number(params.get('width'), 40)
        height = safe_number(params.get('height'), 60)
        capacitance = str(params.get('capacitance', '10μF'))
        color = str(params.get('color', '#333'))
        
        return f'''<svg width="{width + 20}" height="{height + 15}" xmlns="http://www.w3.org/2000/svg">
  <line x1="{width/2 + 10}" y1="0" x2="{width/2 + 10}" y2="{height/3}" stroke="{color}" stroke-width="2"/>
  <line x1="10" y1="{height/3}" x2="{width + 10}" y2="{height/3}" stroke="{color}" stroke-width="3"/>
  <line x1="10" y1="{2*height/3}" x2="{width + 10}" y2="{2*height/3}" stroke="{color}" stroke-width="3"/>
  <line x1="{width/2 + 10}" y1="{2*height/3}" x2="{width/2 + 10}" y2="{height}" stroke="{color}" stroke-width="2"/>
  <text x="{width/2 + 10}" y="{height + 12}" text-anchor="middle" font-size="9" fill="{color}">{capacitance}</text>
</svg>'''

    @staticmethod
    def generate_ammeter(params: Dict[str, Any]) -> str:
        size = safe_number(params.get('size'), 40)
        value = str(params.get('value', '0A'))
        color = str(params.get('color', '#333'))
        
        return f'''<svg width="{size + 10}" height="{size + 15}" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{size/2 + 5}" cy="{size/2 + 5}" r="{size/2}" fill="none" stroke="{color}" stroke-width="2"/>
  <text x="{size/2 + 5}" y="{size/2 + 8}" text-anchor="middle" font-size="{size/3}" font-weight="bold" fill="{color}">A</text>
  <text x="{size/2 + 5}" y="{size + 12}" text-anchor="middle" font-size="9" fill="{color}">{value}</text>
</svg>'''

    @staticmethod
    def generate_voltmeter(params: Dict[str, Any]) -> str:
        size = safe_number(params.get('size'), 40)
        value = str(params.get('value', '0V'))
        color = str(params.get('color', '#333'))
        
        return f'''<svg width="{size + 10}" height="{size + 15}" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{size/2 + 5}" cy="{size/2 + 5}" r="{size/2}" fill="none" stroke="{color}" stroke-width="2"/>
  <text x="{size/2 + 5}" y="{size/2 + 8}" text-anchor="middle" font-size="{size/3}" font-weight="bold" fill="{color}">V</text>
  <text x="{size/2 + 5}" y="{size + 12}" text-anchor="middle" font-size="9" fill="{color}">{value}</text>
</svg>'''

    @classmethod
    def generate(cls, primitive_id: str, params: Optional[Dict[str, Any]] = None) -> Optional[str]:
        params = params or {}
        generators = {
            'battery': cls.generate_battery,
            'resistor': cls.generate_resistor,
            'wire': cls.generate_wire,
            'arrow': cls.generate_arrow,
            'particleStream': cls.generate_particle_stream,
            'graph': cls.generate_graph,
            'textBox': cls.generate_text_box,
            'capacitor': cls.generate_capacitor,
            'ammeter': cls.generate_ammeter,
            'voltmeter': cls.generate_voltmeter,
        }
        generator = generators.get(primitive_id)
        if generator:
            svg = generator(params)
            return SVGSanitizer.sanitize(svg)
        return None
    
    @classmethod
    def can_generate(cls, primitive_id: str) -> bool:
        supported = {'battery', 'resistor', 'wire', 'arrow', 'particleStream', 
                     'graph', 'textBox', 'capacitor', 'ammeter', 'voltmeter'}
        return primitive_id in supported
