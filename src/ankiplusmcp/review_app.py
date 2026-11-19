"""The production MCP App resource uses the proven, version-pinned SDK bridge."""
from pathlib import Path
URI='ui://ankiplus/review.html'
MIME='text/html;profile=mcp-app'


def html():
    return (Path(__file__).parent/'review_ui/review.html').read_text(encoding='utf-8')
