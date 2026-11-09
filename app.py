"""Streamlit entry point for the C1 bilingual publication replay."""
from pathlib import Path
import streamlit as st
from publication_view import build_publication_document

st.set_page_config(page_title='BYTE NDT — LSB941 C1 — FR / EN', layout='wide', initial_sidebar_state='collapsed')

@st.cache_resource(show_spinner=False)
def publication_document(asset_version: tuple) -> str:
    return build_publication_document()

st.caption('BYTE NDT · LSB941-C1 · INTRADOS → EXTRADOS · 41 positions · FR / EN')
assets_root = Path(__file__).resolve().parent / 'assets'
asset_version = tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in sorted(assets_root.iterdir()) if f.is_file())

with st.spinner('Chargement du cycle C1 / Loading the C1 replay…'):
    st.iframe(publication_document(asset_version), height="content", alt="C1 — cycle synchronisé / synchronized replay — FR / EN")

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
