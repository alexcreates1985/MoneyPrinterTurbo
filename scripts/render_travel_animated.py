"""Speech-anchored animated editorial reel; no publishing side effects.

Run from the repository: python scripts/render_travel_animated.py [--frames-only]
The existing review narration is the master clock. Generated illustrations are
atmosphere, not evidence. Sources remain the separate dated register.
"""
import json
import math
import shutil
import subprocess
import sys
import wave
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'storage/traveldecoded-animated-v2'
ART=ROOT/'resource/traveldecoded/animated-v2'
VOICE=ROOT/'storage/traveldecoded-review'
W,H,FPS=1080,1920,24
INK='#103c40'; PAPER='#fff0d4'; GOLD='#ffc36b'; MINT='#a6e4bc'; RED='#ed795f'
OUT.mkdir(parents=True,exist_ok=True)
WORDS=json.loads((VOICE/'words.json').read_text())
def cue(word):
    return next(w['offset']/1e7 for w in WORDS if w['text'].lower().strip('.,?!')==word)
STARTS=[0,cue('first'),cue("singapore's"),cue("bangkok's"),cue('these'),cue("here's"),cue("haven't"),cue('check'),cue("that's")]
# 'check' first occurs at 4.75; the concluding Check is explicitly the final occurrence.
STARTS[7]=[w['offset']/1e7 for w in WORDS if w['text'].lower().strip('.,?!')=='check'][-1]
DURATION=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(VOICE/'narration.mp3')]))
FONT=ROOT/'resource/fonts/BeVietnamPro-Bold.ttf'
if not FONT.exists():FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
@lru_cache(maxsize=100)
def font(s):return ImageFont.truetype(str(FONT),s)
def ease(x):
    x=max(0,min(1,x));return 1-(1-x)**3
def smooth(x):
    x=max(0,min(1,x));return x*x*(3-2*x)
def label(im,s,xy,size=54,fill=PAPER,center=True,maxw=840):
    d=ImageDraw.Draw(im); lines=[]; line=''
    for word in s.split():
        test=(line+' '+word).strip()
        if d.textlength(test,font=font(size))>maxw and line:lines.append(line);line=word
        else:line=test
    if line:lines.append(line)
    for j,l in enumerate(lines):
        x=xy[0]-d.textlength(l,font=font(size))/2 if center else xy[0]
        d.text((x,xy[1]+j*(size+12)),l,font=font(size),fill=fill,stroke_width=0)

@lru_cache(maxsize=1)
def background():
    rng=np.random.default_rng(14)
    a=np.zeros((H,W,3),np.uint8)
    noise=rng.normal(0,1.2,(H,W))
    for c,v in enumerate([16,60,64]):a[:,:,c]=np.clip(v+noise,0,255)
    return Image.fromarray(a)

@lru_cache(maxsize=2)
def artwork(name):return Image.open(ART/(name+'.png')).convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
def scenic(name,elapsed,length):
    # A single continuous, deliberate camera push through each illustrative shot.
    z=1.04+.06*smooth(elapsed/length);sw,sh=round(W*z),round(H*z)
    src=artwork(name).resize((sw,sh),Image.Resampling.BICUBIC)
    return src.crop(((sw-W)//2,(sh-H)//2,(sw+W)//2,(sh+H)//2))

def pill(im,txt,x,y,width=800,height=96,fill=PAPER,textfill=INK,size=38):
    d=ImageDraw.Draw(im);d.rounded_rectangle((x-width/2+7,y+10,x+width/2+7,y+height+10),radius=15,fill='#09282b')
    d.rounded_rectangle((x-width/2,y,x+width/2,y+height),radius=15,fill=fill)
    label(im,txt,(x,y+(height-size)/2-6),size,textfill,maxw=width-30)

def caption(im,t):
    # Four words per cue; word-level highlighting uses returned speech timestamps.
    idx=next((i for i,w in enumerate(WORDS) if w['offset']/1e7<=t<(w['offset']+w['duration'])/1e7+.04),None)
    if idx is None:return
    group=WORDS[(idx//4)*4:(idx//4)*4+4]
    texts=[w['text'] for w in group];f=font(49);d=ImageDraw.Draw(im)
    lines=[];line=[]
    for w in group:
        candidate=' '.join(v['text'] for v in line+[w])
        if d.textlength(candidate,font=f)>800 and line:lines.append(line);line=[w]
        else:line.append(w)
    if line:lines.append(line)
    y=1420
    for line in lines:
        total=d.textlength(' '.join(w['text'] for w in line),font=f)
        x=(W-total)/2
        d.rounded_rectangle((x-18,y-9,x+total+18,y+66),radius=10,fill='#092b2e')
        for w in line:
            active=w['offset']/1e7<=t<(w['offset']+w['duration'])/1e7+.04
            d.text((x,y),w['text'],font=f,fill=GOLD if active else PAPER)
            x+=d.textlength(w['text']+' ',font=f)
        y+=79

def frame(t):
    i=max(j for j,a in enumerate(STARTS) if a<=t);u=t-STARTS[i]
    im=background().copy();d=ImageDraw.Draw(im)
    if i==0:
        # The budget enters as the question; concentric cut-paper layers resolve.
        for j,r in enumerate([720,560,420]):
            p=ease((u-j*.12)/.65);rr=r*p
            d.ellipse((540-rr,800-rr,540+rr,800+rr),fill=['#16484c','#206068','#28747a'][j])
        label(im,'ONE BUDGET.',(540,330),62)
        label(im,'S$50',(540,660+round(70*(1-ease(u/.6)))) ,185,GOLD)
        if u>.8:label(im,'TWO CITIES.',(540,970),72)
        if u>1.6:label(im,'What changes the price?',(540,1120),43)
    elif i==1:
        label(im,'START WITH THE CONDITIONS',(540,300),44,GOLD)
        # Explicit schematic: position encodes narrative order, not geography.
        x0,y0,x1,y1=290,650,750,1080
        d.ellipse((x0-78,y0-78,x0+78,y0+78),fill=MINT)
        d.ellipse((x1-78,y1-78,x1+78,y1+78),fill=GOLD)
        p=ease(u/1.25)
        d.line((x0+60,y0+60,x0+60+(x1-x0-120)*p,y0+60+(y1-y0-120)*p),fill=PAPER,width=9)
        label(im,'SG',(x0,y0-34),50,INK);label(im,'BKK',(x1,y1-32),43,INK)
        label(im,'Singapore',(310,790),38);label(im,'Bangkok',(710,1200),38)
        label(im,'Schematic city pairing • not a route map',(540,1280),27)
    elif i==2:
        im=scenic('singapore',u,STARTS[3]-STARTS[2]);d=ImageDraw.Draw(im)
        label(im,'SINGAPORE',(540,270),68)
        label(im,'National Gallery',(540,365),43)
        # Price flips only when the voice changes eligibility, not a sale animation.
        local=t>=cue('free');change=cue('free')-STARTS[2]
        if t>=cue('twenty'):
            flip=abs(1-2*smooth((u-change)/.55)) if 0<u-change<.55 else 1
            card=Image.new('RGBA',(800,260));dc=ImageDraw.Draw(card);dc.rounded_rectangle((0,0,799,259),radius=18,fill=PAPER)
            label(card,'FREE' if local else 'S$20',(400,20),100,INK)
            label(card,'Citizens + PRs' if local else 'Other nationalities',(400,159),39,INK)
            cw=max(4,round(800*flip));card=card.resize((cw,260),Image.Resampling.BICUBIC);im.paste(card,(540-cw//2,520),card)
        pill(im,'General admission • eligibility matters',540,1210,height=82,size=32)
        label(im,'AI illustration • not documentary imagery',(540,1320),25)
    elif i==3:
        im=scenic('bangkok',u,STARTS[4]-STARTS[3]);d=ImageDraw.Draw(im)
        label(im,'BANGKOK',(540,270),68)
        label(im,'Grand Palace',(540,365),44)
        if t>=cue('five'):
            p=ease((t-cue('five'))/.35);pill(im,'THB 500',540,510+round(45*(1-p)),height=155,size=93)
            pill(im,'Foreign visitor admission',540,1210,height=82,size=33)
        label(im,'AI illustration • not documentary imagery',(540,1320),25)
    elif i==4:
        label(im,'COMPARE THE EXPERIENCE',(540,310),43,GOLD)
        p=ease(u/.5)
        d.ellipse((100-250*(1-p),620,490-250*(1-p),1010),fill=MINT)
        d.polygon([(650+250*(1-p),620),(1000+250*(1-p),1010),(560+250*(1-p),1010)],fill=GOLD)
        label(im,'GALLERY',(295-250*(1-p),790),38,INK)
        label(im,'PALACE',(770+250*(1-p),840),37,INK)
        if u>1:
            d.line((475,1130,605,1130),fill=PAPER,width=12);d.line((475,1170,605,1170),fill=PAPER,width=12);d.line((500,1200,580,1100),fill=RED,width=15)
        if u>2:label(im,'Different experiences',(540,1250),45)
    elif i==5:
        label(im,'THE EXCHANGE CATCH',(540,270),53,GOLD)
        label(im,'Each tile represents S$50',(540,375),35)
        # Six equal units explain why a minimum of 300 does not validate 50.
        for j in range(6):
            x=240+(j%3)*270;y=560+(j//3)*250
            p=ease((u-.18*j)/.45)
            xx=x+round((1-p)*1050)
            d.rounded_rectangle((xx-100,y,xx+100,y+180),radius=10,fill=MINT if j==0 else GOLD)
            label(im,'S$50',(xx,y+52),47,INK)
        if t>=cue('three'):
            label(im,'S$300 minimum',(540,1100),66,GOLD)
            label(im,'Your S$50 is only one tile',(540,1210),37)
        label(im,'Saleem listing • quote dated 7 Nov 2026',(540,1320),28)
    elif i==6:
        label(im,'NO VERIFIED S$50 QUOTE',(540,300),45,GOLD)
        label(im,'S$50',(540,600),140)
        # Motion stops at the missing input instead of producing a fake conversion.
        p=min(1,u/1.2)
        d.line((540,820,540,820+260*p),fill=MINT,width=12)
        if p==1:d.line((460,1090,620,1090),fill=RED,width=16)
        label(im,'? THB',(540,1130),95,GOLD)
        if u>2:label(im,'No invented conversion. No winner.',(540,1290),32)
    elif i==7:
        label(im,'BEFORE YOU TRUST A BUDGET',(540,290),43,GOLD)
        for j,txt in enumerate(['WHO GETS THE PRICE?','WHAT IS THE MINIMUM?','WHEN WAS IT CHECKED?']):
            p=ease((u-j*1.2)/.35)
            if p>0:
                x=540-round(100*(1-p));y=590+j*225
                pill(im,txt,x,y,height=125,size=35,fill=[PAPER,MINT,GOLD][j])
        if u>3.5:label(im,'Sources checked 8 Nov 2026',(540,1300),31)
    else:
        label(im,'ALEX',(540,520),67,MINT)
        label(im,'TRAVEL',(540,660),116)
        label(im,'DECODED',(540,800),116,GOLD)
        d.line((230,1015,230+620*ease(u/.6),1015),fill=MINT,width=10)
        label(im,'Know what your money buys.',(540,1120),38)
    # Review label remains legible but does not become a slide footer.
    pill(im,'DRAFT v2 • REVIEW BEFORE PUBLISHING',540,1670,width=820,height=64,size=26,fill=INK,textfill=MINT)
    caption(im,t)
    return im

def sound():
    rate=48000;audio=np.zeros(math.ceil(DURATION*rate),np.float32)
    for k,s in enumerate([STARTS[1],STARTS[2],cue('free'),STARTS[3],STARTS[5],STARTS[6],STARTS[8]]):
        n=int(.18*rate);t=np.arange(n)/rate
        # Quiet original synthesized cue, no sampled music or creator audio.
        accent=.045*np.sin(2*np.pi*(360+50*k)*t)*np.exp(-32*t)*np.minimum(1,t/.012)
        at=int(s*rate);audio[at:at+n]+=accent[:len(audio[at:at+n])]
    with wave.open(str(OUT/'sound-design.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes((audio*32767).astype('<i2').tobytes())

def main():
    for t in [1.8,5.8,11.8,15.3,20,24.5,32,37,46,50]:frame(t).save(OUT/f'frame-{t}.jpg',quality=91)
    frame(1.8).save(OUT/'cover.png')
    style=dict(direction='Paper-cut editorial travel explainer',palette=dict(ink=INK,paper=PAPER,accent=GOLD,eligibility=MINT,stop=RED),fps=FPS,width=W,height=H,font=str(FONT.relative_to(ROOT)),captions='4-word groups, speech-timed highlighting, safe central lower band',transitions='Hard cuts; internal eligibility flip, schematic trace, six-unit minimum build',illustrations='AI-generated atmospheric city art; not photographic evidence',approval='Not approved')
    (OUT/'style.json').write_text(json.dumps(style,indent=2))
    names=['Budget hook','City pairing','Eligibility flip','Bangkok admission','Different experiences','Six unit minimum','Conversion blocked','Checks','Brand close']
    timeline=[dict(name=n,start=s,settled=s+.5,cue=s,hold_end=(STARTS[i+1] if i+1<len(STARTS) else DURATION),end=(STARTS[i+1] if i+1<len(STARTS) else DURATION)) for i,(n,s) in enumerate(zip(names,STARTS))]
    (OUT/'timeline.json').write_text(json.dumps(timeline,indent=2))
    if '--frames-only' in sys.argv:return
    sound()
    cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
        '-i',str(VOICE/'narration.mp3'),'-i',str(OUT/'sound-design.wav'),'-filter_complex','[1:a][2:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]',
        '-map','0:v','-map','[a]','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(OUT/'TravelDecoded_Animated_Draft_v2.mp4')]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for f in range(math.ceil(DURATION*FPS)):proc.stdin.write(frame(f/FPS).tobytes())
    proc.stdin.close()
    if proc.wait()!=0:raise RuntimeError('Render failed')
    for src,dst in [(VOICE/'captions.srt',OUT/'captions-original-transcript.srt'),(VOICE/'narration.mp3',OUT/'narration.mp3'),(ROOT/'docs/travel/business/ledger.json',OUT/'source-register.json')]:shutil.copy(src,dst)
    # Export the actual four-word caption grouping used on screen.
    def stamp(t):
        m=round(t*1000);return f'{m//3600000:02}:{m//60000%60:02}:{m//1000%60:02},{m%1000:03}'
    cues=[]
    for i in range(0,len(WORDS),4):
        g=WORDS[i:i+4];cues.append(f"{len(cues)+1}\n{stamp(g[0]['offset']/1e7)} --> {stamp((g[-1]['offset']+g[-1]['duration'])/1e7)}\n"+' '.join(w['text'] for w in g))
    (OUT/'captions.srt').write_text('\n\n'.join(cues))
    print(str(OUT/'TravelDecoded_Animated_Draft_v2.mp4'))

if __name__=='__main__':main()
