"""Streamlit entry point for the C1 bilingual publication replay."""
from pathlib import Path
import streamlit as st
from publication_view import build_publication_document

st.set_page_config(page_title='BYTE NDT — LSB941 C1 — FR / EN', layout='wide', initial_sidebar_state='collapsed')

RELEASE_ID = 'C1-27_6-GORGE1-R3'

st.info('C1 · Première gorge · 27,6 mm · R3')
st.caption('BYTE NDT · LSB941-C1 · INTRADOS → première gorge EXTRADOS · réf. 27,6 mm · 41 positions · FR / EN')
st.caption('Rejeu UT reconstruit dans les poses mécaniques recalées ; résultats sources conservés, sans nouvelle validation physique. / UT replay reconstructed in registered mechanical poses; source results retained, without a new physical validation.')
assets_root = Path(__file__).resolve().parent / 'assets'
# Check the actual deployment files before building the viewer. Never reuse an
# HTML document cached by a previous server revision.
import hashlib
import json
manifest = json.loads((Path(__file__).resolve().parent / 'reference' / 'MANIFESTE_ASSETS_PUBLIES.json').read_text())
mismatches = [name for name, expected in manifest.items()
              if not (assets_root / name).is_file()
              or hashlib.sha256((assets_root / name).read_bytes()).hexdigest() != expected]
if mismatches:
    st.error('Les fichiers de cette version sont incomplets. Redémarrer l’application dans Manage app → Reboot. / Incomplete release files; reboot the app.')
    st.stop()

with st.spinner('Chargement du cycle C1 / Loading the C1 replay…'):
    st.iframe(build_publication_document(assets_root), height="content", alt="C1 — cycle synchronisé / synchronized replay — FR / EN")

with st.expander('Version actuelle et notice / Current version and guide'):
    root = Path(__file__).resolve().parent
    st.download_button('Notice bilingue PDF / Bilingual PDF guide', (root / 'assets' / 'NOTICE_C1_FR_EN.pdf').read_bytes(),
                       file_name='NOTICE_C1_FR_EN.pdf', mime='application/pdf')
    st.download_button('C1 actuel — ZIP FR/EN / Current C1 — FR/EN ZIP', (root / 'downloads' / 'C1_FINAL_FR_EN.zip').read_bytes(), file_name='C1_FINAL_FR_EN.zip', mime='application/zip')

with st.expander('Archives vidéo V02 / V02 video archives'):
    st.caption('Présentation précédente ; le nouveau volume calculé est dans l’interface actuelle. / Previous presentation; the new computed volume is in the current interface.')
    base = 'https://raw.githubusercontent.com/jmpuybouffat/01_Paut_Training_-/9d93fea/downloads/LSB941_C1_SYNC_FR_EN_V02/'
    st.link_button('Vidéo française / French video', base + 'C1_CYCLE_FR.mp4')
    st.link_button('English video / Vidéo anglaise', base + 'C1_CYCLE_EN.mp4')
    st.caption('Rejeu numérique de référence, pas une nouvelle acquisition physique. Le passage mécanique du scanner reste à vérifier. / Reference digital replay, not a new physical acquisition. Scanner clearance remains to be checked.')
