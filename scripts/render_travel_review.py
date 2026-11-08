"""Original price-intelligence review video, separate from the blocked basket pilot."""
import asyncio, json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import edge_tts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'storage/traveldecoded-review'
OUT.mkdir(parents=True,exist_ok=True)
script=(ROOT/'docs/travel/business/pilot-script.txt').read_text().strip()

async def narrate():
    if (OUT/'narration.mp3').exists() and (OUT/'words.json').exists(): return
    events=[]
    with (OUT/'narration.mp3').open('wb') as f:
        async for chunk in edge_tts.Communicate(script,'en-SG-WayneNeural',boundary='WordBoundary').stream():
            if chunk['type']=='audio': f.write(chunk['data'])
            elif chunk['type']=='WordBoundary': events.append(chunk)
    (OUT/'words.json').write_text(json.dumps(events,indent=2))

def stamp(t):
    ms=round(t*1000); return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

def main():
    asyncio.run(narrate())
    words=json.loads((OUT/'words.json').read_text())
    if not words: raise ValueError('No returned word timings')
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(OUT/'narration.mp3')]))
    cues=[]
    for i in range(0,len(words),5):
        group=words[i:i+5]; start=group[0]['offset']/1e7
        end=(group[-1]['offset']+group[-1]['duration'])/1e7
        cues.append((start,end,' '.join(x['text'] for x in group)))
    (OUT/'captions.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{t}' for i,(a,b,t) in enumerate(cues)))
    def cue(token):
        for w in words:
            if w['text'].lower().strip('.,?!')==token: return w['offset']/1e7
        raise ValueError('Missing spoken anchor '+token)
    starts=[0,cue("singapore's"),cue("bangkok's"),cue('these'),cue("here's"),cue("haven't"),cue('eligibility')]
    # Each chapter changes the evidence or shows the condition that changes the result.
    titles=['S$50. TWO CITIES.','SINGAPORE','BANGKOK','DIFFERENT EXPERIENCES','THE EXCHANGE CATCH','NO VERIFIED CONVERSION','CHECK BEFORE COMPARING']
    values=['Who gets the price?','S$20 / S$0','THB 500','No like-for-like winner','S$300 minimum','S$50 = ? THB','Eligibility. Minimum. Date.']
    details=['Research preview • not a complete basket','Other nationalities: S$20. Citizens and PRs: free general admission.','Grand Palace • foreign visitor admission','A gallery and a palace offer different things','Saleem listing • 7 Nov 2026, 20:11 SGT','Fees and S$50 applicability remain unconfirmed','Alex TravelDecoded • sources checked 8 Nov 2026']
    fontfile=ROOT/'resource/fonts/BeVietnamPro-Bold.ttf'
    if not fontfile.exists(): fontfile=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    fonts={s:ImageFont.truetype(str(fontfile),s) for s in [30,34,42,48,56,72,88]}
    def text(draw,txt,y,size=48,color='#f4efe5',maxwidth=810):
        f=fonts[size]; lines=[]; line=''
        for word in txt.split():
            candidate=(line+' '+word).strip()
            if draw.textlength(candidate,font=f)>maxwidth and line:lines.append(line);line=word
            else:line=candidate
        if line:lines.append(line)
        for n,line in enumerate(lines):draw.text((540-draw.textlength(line,font=f)/2,y+n*(size+15)),line,font=f,fill=color)
    fps=24
    cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r',str(fps),'-i','-',
         '-i',str(OUT/'narration.mp3'),'-map','0:v','-map','1:a','-c:v','libx264','-preset','fast','-crf','20',
         '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-movflags','+faststart',str(OUT/'TravelDecoded_Bangkok_Research_Review.mp4')]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for frame in range(math.ceil(duration*fps)):
        t=frame/fps; scene=max(i for i,s in enumerate(starts) if s<=t)
        elapsed=t-starts[scene]; p=min(1,elapsed/.7)
        im=Image.new('RGB',(1080,1920),'#112d30');d=ImageDraw.Draw(im)
        text(d,titles[scene],430,34,'#a6e4bc')
        if scene==1:
            # Same admission product; change eligibility, not city.
            width=round(680*(1-min(1,max(0,elapsed-4)/.8)))
            d.rectangle((200,850,880,910),fill='#254448')
            if width:d.rectangle((200,850,200+width,910),fill='#f6bb67')
        elif scene==4:
            d.rectangle((200,850,880,910),fill='#254448')
            d.rectangle((200,850,200+round(680*p),910),fill='#f6bb67')
            text(d,'S$50 budget is below this minimum',955,34)
        text(d,values[scene],610,72 if scene not in (0,3,6) else 56,'#f6bb67')
        text(d,details[scene],1060,30,maxwidth=760)
        active=next((c for c in cues if c[0]<=t<c[1]+.08),None)
        if active:text(d,active[2],1320,48,maxwidth=820)
        text(d,'REVIEW ONLY • NOT APPROVED FOR PUBLICATION',1720,30,'#a6e4bc',900)
        if frame in {round((s+1)*fps) for s in starts}:
            im.save(OUT/f'frame-{scene}.png')
        proc.stdin.write(im.tobytes())
    proc.stdin.close()
    if proc.wait()!=0: raise RuntimeError('FFmpeg failed')
    (OUT/'production.json').write_text(json.dumps(dict(duration=duration,width=1080,height=1920,fps=fps,
        voice='en-SG-WayneNeural',engine='edge-tts',speech_speed=1,caption_timing='Returned WordBoundary metadata',
        listening_review='not_performed',visuals='Original Python typography and proportional diagrams',
        music='None',status='Research review; full S$50 basket pilot blocked by missing research',
        scene_starts=starts),indent=2))
    print(json.dumps({'duration':duration,'output':str(OUT/'TravelDecoded_Bangkok_Research_Review.mp4')}))

if __name__=='__main__': main()
