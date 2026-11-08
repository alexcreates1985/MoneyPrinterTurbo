"""Animated production and draft review inside MoneyPrinterTurbo."""
import json
import streamlit as st
from app.services import travel_animation as animation
from app.services.travel_release import PLATFORMS

def show():
    st.subheader('Animated production and review')
    st.caption('Current production template: Singapore–Bangkok research explainer. Full S$50 basket episode still needs verified basket data.')
    missing=animation.missing_inputs()
    if missing:
        st.warning('Production assets need restoring on this installation.')
        with st.expander('Missing assets'):st.write(missing)
    if st.button('Render animated draft',disabled=bool(missing),key='render_animated_draft'):
        try:
            with st.spinner('Rendering narration-synchronised animation…'):
                animation.render()
            st.success('Draft rendered. Review it below; no upload has occurred.')
        except (ValueError,RuntimeError,OSError,TimeoutError) as exc:st.error(str(exc))
    video=animation.OUTPUT/animation.VIDEO
    if not video.is_file():
        st.info('No animated MP4 on this installation yet.');return
    st.video(str(video))
    st.download_button('Download animated MP4',video.read_bytes(),animation.VIDEO,'video/mp4')
    caption_file=animation.OUTPUT/'platform-captions.json'
    captions=json.loads(caption_file.read_text()) if caption_file.exists() else {p:'' for p in PLATFORMS}
    with st.expander('Review captions for all four platforms'):
        edited={p:st.text_area(p.title(),value=captions.get(p,''),key='animated_caption_'+p) for p in PLATFORMS}
        if st.button('Stage this version for review',disabled=not all(edited.values())):
            try:
                animation.prepare_review(edited)
                caption_file.write_text(json.dumps(edited,indent=2))
                st.success('Review package staged. Approval is unset and no publishing request was sent.')
            except (ValueError,OSError) as exc:st.error(str(exc))
    review=animation.OUTPUT/'publishing-review.json'
    if review.exists():
        st.download_button('Download exact review manifest',review.read_bytes(),'publishing-review.json','application/json')
    st.warning('Publishing is not connected for this animated workflow. Account selection, human approval and a tested publishing adapter are required before submission.')
