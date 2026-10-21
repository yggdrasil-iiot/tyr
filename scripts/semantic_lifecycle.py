"""Immutable URI governance records. No device IO or runtime activation."""
import copy
import logical_structures as logical
import re,json,hashlib
from datetime import datetime,timezone

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-](?:0[0-9]|1[0-9]|2[0-3]):[0-5][0-9])",value):
        raise ValueError("Explicit timestamp with offset, up to six fractional digits required")
    # RFC3339 -00:00 denotes an unknown local offset, not a known UTC clock.
    if value.endswith("-00:00"):raise ValueError("Unknown local offset -00:00")
    return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)


import validate_contracts as vc

def require(ok,code):
    if not ok:raise ValueError(code)

def signatures(documents):
    out={}
    for d in documents:
        if d.get('kind')=='semantic-definition':
            for n in logical.layout(d)['definitions']:
                uri=n['semanticId'];sig=logical.signature(n)
                require(uri not in out or out[uri]==sig,'lifecycle.signature-conflict');out[uri]=sig
    return out

def replay(events,known):
    unique={};grouped={}
    for e in events:
        require(not list(vc.schema_validator('semantic-lifecycle','2.18.0').iter_errors(e)),'lifecycle.schema')
        timestamp(e['authoredAt'])
        key=(e['id'],e['version']);require(key not in unique or unique[key]==e,'lifecycle.event-conflict');unique[key]=e
    require(len(unique)<=1024,'lifecycle.limit')
    for e in unique.values():grouped.setdefault(e['semanticId'],[]).append(e)
    states={}
    for uri,history in sorted(grouped.items()):
        require(uri in known,'lifecycle.uri-missing');history.sort(key=lambda e:e['revision']);state='active';previous=None;replacement=None
        for i,e in enumerate(history,1):
            require(e['revision']==i,'lifecycle.revision-conflict')
            ref=None if previous is None else dict(id=previous['id'],version=previous['version'],sha256=digest(previous))
            require(e['previousEvent']==ref,'lifecycle.previous-conflict')
            require(e['signatureSha256']==digest(known[uri]),'lifecycle.signature-drift')
            require(previous is None or timestamp(e['authoredAt'])>=timestamp(previous['authoredAt']),'lifecycle.time-order')
            require(state!='retired','lifecycle.retired-terminal')
            if e['action']=='deprecate':require(state=='active','lifecycle.transition');state='deprecated'
            elif e['action']=='retire':require(state=='deprecated','lifecycle.transition');state='retired'
            if e['action'] in ('revise','retire'):require(e['replacementSemanticId']==replacement,'lifecycle.replacement-immutable')
            else:replacement=e['replacementSemanticId']
            require(replacement is None or replacement!=uri and replacement in known,'lifecycle.replacement-missing')
            previous=e
        states[uri]={'semanticId':uri,'state':state,'revision':len(history),'replacementSemanticId':replacement,'history':copy.deepcopy(history)}
    for uri,s in states.items():
        seen={uri};nxt=s['replacementSemanticId']
        while nxt is not None:
            require(nxt not in seen,'lifecycle.replacement-cycle');seen.add(nxt)
            require(states.get(nxt,{}).get('state')!='retired','lifecycle.replacement-retired')
            nxt=states.get(nxt,{}).get('replacementSemanticId')
    return states

def impacts(documents):
    docs=list(documents);byref={(d.get('kind'),d.get('id'),d.get('version')):d for d in docs};out=[]
    for d in docs:
        if d.get('kind') not in ('mapping-set','write-definition'):continue
        target=byref.get(('target-instance',d['targetInstanceRef']['id'],d['targetInstanceRef']['version']))
        if target is None:continue
        ref=target['semanticDefinitionRef'];sem=byref.get(('semantic-definition',ref['id'],ref['version']))
        if sem is None:continue
        bindings=d['mappings'] if d['kind']=='mapping-set' else [d]
        for b in bindings:
            nodes=sem['members'];uris=[]
            for step in b.get('memberPath',[]):
                if step['kind']!='member':continue
                n=next((n for n in nodes if n['memberId']==step['memberId']),None)
                if n is None:break
                uris.append(n['semanticId']);nodes=n.get('members',[])
            for uri in uris:out.append({'semanticId':uri,'kind':d['kind'],'id':d['id'],'version':d['version'],'bindingId':b.get('mappingId',d['id']),'targetInstanceId':target['id'],'equipmentInstanceId':d['equipmentInstanceId'],'memberPath':copy.deepcopy(b.get('memberPath',[]))})
    return out

def validate(documents,history=(),known=None):
    docs=list(documents);sigs=dict(known or {});local=signatures(docs)
    for uri,sig in local.items():require(uri not in sigs or sigs[uri]==sig,'lifecycle.signature-drift');sigs[uri]=sig
    states=replay(list(history)+[d for d in docs if d.get('kind')=='semantic-lifecycle'],sigs)
    return states,[dict(i,ruleCode='lifecycle.retired-binding',path=i['id']+'/'+i['bindingId']) for i in impacts(docs) if states.get(i['semanticId'],{}).get('state')=='retired']

def check_transition(before,after):
    current={(e['id'],e['version']):e for e in after.get('semanticLifecycles',[])}
    for e in before.get('semanticLifecycles',[]):require(current.get((e['id'],e['version']))==e,'lifecycle.history-immutable')
