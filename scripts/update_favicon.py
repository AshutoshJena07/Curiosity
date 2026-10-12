import base64
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
png_path = PROJECT_ROOT / "frontend-react" / "public" / "favicon.png"
with open(png_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 760" width="100%" height="100%">
  <image width="760" height="760" href="data:image/png;base64,{b64}"/>
</svg>"""

react_svg = PROJECT_ROOT / "frontend-react" / "public" / "favicon.svg"
prod_svg = PROJECT_ROOT / "frontend" / "favicon.svg"

react_svg.write_text(svg_content, encoding="utf-8")
prod_svg.write_text(svg_content, encoding="utf-8")

print("Favicon SVG created successfully!")
