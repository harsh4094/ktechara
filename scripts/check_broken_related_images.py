from pathlib import Path
import re

ROOT = Path(__file__).parent.parent
broken = []
for path in sorted((ROOT / 'blog').glob('*/*/index.html')):
    text = path.read_text(encoding='utf-8', errors='replace')
    if 'Related blogs' not in text:
        continue
    # find loop section after heading
    section = text.split('Related blogs', 1)[1]
    for match in re.finditer(r'<img[^>]+src="([^"]+)"', section):
        src = match.group(1)
        if src.startswith('http://') or src.startswith('https://') or src.startswith('data:'):
            continue
        if src.startswith('/'):
            file_path = ROOT / src.lstrip('/')
        else:
            file_path = path.parent / src
        if not file_path.exists():
            broken.append((path.relative_to(ROOT), src, file_path))

print(f"checked {len(list((ROOT / 'blog').glob('*/*/index.html')))} pages")
print(f"broken references: {len(broken)}")
for p, src, fp in broken[:50]:
    print(p, src, fp)
