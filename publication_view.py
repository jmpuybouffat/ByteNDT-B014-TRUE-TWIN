"""Package the validated C1 replay for Streamlit. Display only; no UT computation."""
from __future__ import annotations
import base64
import html
import json
from pathlib import Path

ASSET_FILES = {
    'NOTICE_C1_FR_EN.pdf': 'application/pdf',
    'C1_RAPPORT_REFERENCE.html': 'text/html;charset=utf-8',
    'C1_VALIDATION_REFERENCE.csv': 'text/csv;charset=utf-8',
    'C1_DETECTIONS_REFERENCE.csv': 'text/csv;charset=utf-8',
    'C1_3485_LOIS_FOCALES.csv': 'text/csv;charset=utf-8',
    'C1_ANALYSE_DECISION.csv': 'text/csv;charset=utf-8',
    'C1_CONTEXTE_REFERENCE.json': 'application/json',
}

def build_publication_document(root: Path | None = None) -> str:
    root = root or Path(__file__).resolve().parent / 'assets'
    document = (root / '00_OUVRIR_CYCLE_C1_FR_EN.html').read_text(encoding='utf-8')
    scene = (root / 'SCENE_C1_SYNCHRONISEE.html').read_text(encoding='utf-8')
    # srcdoc keeps the scene local to the component, with the same postMessage clock.
    original = 'src="SCENE_C1_SYNCHRONISEE.html"'
    assert document.count(original) == 1
    document = document.replace(original, 'srcdoc="' + html.escape(scene, quote=True) + '"')
    assets = {name: {'mime': mime, 'base64': base64.b64encode((root / name).read_bytes()).decode('ascii')}
              for name, mime in ASSET_FILES.items()}
    bootstrap = '''<script>
const embeddedAssets = __ASSETS__;
const assetURLs = {};
for (const [name, value] of Object.entries(embeddedAssets)) {
  const bytes = Uint8Array.from(atob(value.base64), c => c.charCodeAt(0));
  assetURLs[name] = URL.createObjectURL(new Blob([bytes], {type: value.mime}));
}
for (const a of document.querySelectorAll('a[href]')) {
  const relative = a.getAttribute('href');
  if (assetURLs[relative]) {
    a.href = assetURLs[relative];
    if (a.hasAttribute('download')) a.download = relative;
  }
}
</script>'''.replace('__ASSETS__', json.dumps(assets, separators=(',', ':')))
    marker = '<script>const GUIDE='
    assert document.count(marker) == 1
    document = document.replace(marker, bootstrap + marker)
    old_guide = "document.querySelector('[data-t=guidePdf]').href='NOTICE_C1_FR_EN.pdf'+(lang==='en'?'#page=2':'#page=1');"
    new_guide = "document.querySelector('[data-t=guidePdf]').href=assetURLs['NOTICE_C1_FR_EN.pdf']+(lang==='en'?'#page=2':'#page=1');"
    assert old_guide in document
    document = document.replace(old_guide, new_guide)
    return document
