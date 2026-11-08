"""Prepare a four-network review package without contacting any social service.

Approval binds video, source register, captions, destinations and schedule.
This module deliberately cannot authenticate, upload, or publish. A connected
publishing adapter must validate this package immediately before submission.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PLATFORMS=('tiktok','youtube','facebook','instagram')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def digest(package):
    payload={k:v for k,v in package.items() if k not in ('approval','package_sha256')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def stage(video, sources, captions, *, accounts=None, schedule=None):
    if set(captions)!=set(PLATFORMS):raise ValueError('Exactly four platform captions are required')
    video,sources=Path(video),Path(sources)
    package=dict(version=1,status='awaiting_review',video=dict(file=video.name,sha256=sha(video)),
        sources=dict(file=sources.name,sha256=sha(sources)),
        platforms={p:dict(account_id=(accounts or {}).get(p),caption=captions[p],
            format='short' if p=='youtube' else 'reel' if p in ('facebook','instagram') else 'video',
            schedule=schedule,publication_status='not_submitted') for p in PLATFORMS},
        review_scope='Research-intelligence reel; not a completed S$50 shopping basket comparison',
        approval=None)
    package['package_sha256']=digest(package)
    return package

def readiness(package, folder):
    errors=[];folder=Path(folder)
    if package.get('package_sha256')!=digest(package):errors.append('Package changed after staging')
    for key in ('video','sources'):
        item=package[key];p=folder/item['file']
        if not p.is_file() or sha(p)!=item['sha256']:errors.append(f'{key} missing or changed')
    for platform in PLATFORMS:
        target=package.get('platforms',{}).get(platform,{})
        if not target.get('account_id'):errors.append(f'{platform}: target account not connected and verified')
        if not target.get('caption'):errors.append(f'{platform}: caption missing')
    return errors

def approve(package,folder,*,human_reviewed=False):
    if human_reviewed is not True:raise ValueError('Explicit human review is required')
    errors=readiness(package,folder)
    if errors:raise ValueError('; '.join(errors))
    result=json.loads(json.dumps(package))
    result['approval']=dict(approved_package_sha256=package['package_sha256'],
        approved_at=datetime.now(timezone.utc).isoformat())
    return result

def require_approval(package,folder):
    errors=readiness(package,folder)
    decision=package.get('approval') or {}
    if decision.get('approved_package_sha256')!=package.get('package_sha256'):errors.append('No approval for this exact package')
    if errors:raise ValueError('; '.join(errors))
    return True
