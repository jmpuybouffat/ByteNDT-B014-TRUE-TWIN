"""Streamlit entry point for the C1 bilingual publication replay."""
from pathlib import Path
import streamlit as st
from publication_view import build_publication_document

st.set_page_config(page_title='BYTE NDT — LSB941 C1 — FR / EN', layout='wide', initial_sidebar_state='collapsed')

@st.cache_resource(show_spinner=False)
def publication_document() -> str:
    return build_publication_document()

st.caption('BYTE NDT · LSB941-C1 · EXTRADOS → INTRADOS · 41 positions · FR / EN')
with st.spinner('Chargement du cycle C1 / Loading the C1 replay…'):
    st.iframe(publication_document(), height=1450, alt="C1 — cycle synchronisé / synchronized replay — FR / EN")

with st.expander('Notice, vidéos et dossier hors ligne / Guide, videos and offline package'):
    root = Path(__file__).resolve().parent
    st.download_button('Notice bilingue PDF / Bilingual PDF guide', (root / 'assets' / 'NOTICE_C1_FR_EN.pdf').read_bytes(),
                       file_name='NOTICE_C1_FR_EN.pdf', mime='application/pdf')
    base = 'https://raw.githubusercontent.com/jmpuybouffat/01_Paut_Training_-/9d93fea/downloads/LSB941_C1_SYNC_FR_EN_V02/'
    st.link_button('Vidéo française / French video', base + 'C1_CYCLE_FR.mp4')
    st.link_button('English video / Vidéo anglaise', base + 'C1_CYCLE_EN.mp4')
    st.link_button('Dossier hors ligne / Offline package', base + 'C1_CYCLE_SYNCHRONISE_FR_EN_V02.zip')
    st.caption('Rejeu numérique de référence, pas une nouvelle acquisition physique. Le passage mécanique du scanner reste à vérifier. / Reference digital replay, not a new physical acquisition. Scanner clearance remains to be checked.')
