"""Dashboard entry point for the existing, source-checked animated review render."""
import json
import subprocess
import sys
from pathlib import Path
from app.services.travel_release import stage

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'storage/traveldecoded-animated-v2'
VIDEO='TravelDecoded_Animated_Draft_v2.mp4'

def missing_inputs():
    paths=['resource/traveldecoded/animated-v2/singapore.png','resource/traveldecoded/animated-v2/bangkok.png',
           'storage/traveldecoded-review/narration.mp3','storage/traveldecoded-review/words.json',
           'storage/traveldecoded-review/captions.srt','docs/travel/business/ledger.json']
    return [p for p in paths if not (ROOT/p).is_file()]

def render():
    missing=missing_inputs()
    if missing:raise ValueError('Restore production assets first: '+', '.join(missing))
    OUTPUT.mkdir(parents=True,exist_ok=True)
    lock=OUTPUT/'.render.lock'
    try:handle=lock.open('x')
    except FileExistsError:raise ValueError('A render is already running. Check its process before removing the render lock.')
    try:
        handle.close()
        # An older decision never carries over to a newly rendered video.
        decision=OUTPUT/'publishing-review.json'
        if decision.exists():
            old=json.loads(decision.read_text());old['approval']=None;old['status']='rendering';decision.write_text(json.dumps(old,indent=2))
        with (OUTPUT/'render.log').open('w') as log:
            result=subprocess.run([sys.executable,str(ROOT/'scripts/render_travel_animated.py')],cwd=ROOT,
                                  stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        if result.returncode:raise RuntimeError('Render failed; inspect storage/traveldecoded-animated-v2/render.log')
        return OUTPUT/VIDEO
    finally:lock.unlink(missing_ok=True)

def prepare_review(captions):
    package=stage(OUTPUT/VIDEO,OUTPUT/'source-register.json',captions)
    (OUTPUT/'publishing-review.json').write_text(json.dumps(package,indent=2))
    return package
