import pytest
from app.services.travel_release import stage,approve,require_approval,PLATFORMS

@pytest.fixture
def staged(tmp_path):
    video=tmp_path/'draft.mp4';video.write_bytes(b'test fixture, not real video')
    source=tmp_path/'sources.json';source.write_text('{}')
    p=stage(video,source,{x:'Review caption' for x in PLATFORMS},accounts={x:'test-target-'+x for x in PLATFORMS})
    return p,tmp_path

def test_human_review_required(staged):
    p,f=staged
    with pytest.raises(ValueError,match='Explicit human'):approve(p,f)
    with pytest.raises(ValueError,match='No approval'):require_approval(p,f)

@pytest.mark.parametrize('change',['caption','account','schedule','video','source'])
def test_changes_invalidate_approval(staged,change):
    p,f=staged;p=approve(p,f,human_reviewed=True);assert require_approval(p,f)
    if change=='video':(f/'draft.mp4').write_bytes(b'new video')
    elif change=='source':(f/'sources.json').write_text('{"changed":true}')
    else:p['platforms']['facebook'][{'caption':'caption','account':'account_id','schedule':'schedule'}[change]]='changed'
    with pytest.raises(ValueError):require_approval(p,f)

def test_unconnected_accounts_block_approval(staged):
    p,f=staged
    p=stage(f/'draft.mp4',f/'sources.json',{x:'Review caption' for x in PLATFORMS})
    with pytest.raises(ValueError,match='not connected'):approve(p,f,human_reviewed=True)
