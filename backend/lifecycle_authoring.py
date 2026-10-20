"""Local lifecycle drafts; Bifrost remains the approval and publication authority."""
import copy,uuid
from datetime import datetime,timezone
import semantic_lifecycle as lc
from sample_quality import digest

def report(store,adapter):
    snap=store.read();w=snap['workspace'];known=lc.signatures(w['semantics']);published=None
    if adapter.configured:
        published=adapter.call('lifecycle',adapter.registry)
        lc.require(published.get('kind')=='semantic-lifecycle-catalog' and published.get('schemaVersion')=='2.18.0','lifecycle.registry-unavailable')
        unhashed=copy.deepcopy(published);claimed=unhashed.pop('catalogSha256',None)
        lc.require(claimed==digest(unhashed),'lifecycle.registry-digest')
        for e in published['entries']:
            uri=e['semanticId'];lc.require(uri not in known or known[uri]==e['signature'],'lifecycle.signature-drift');known[uri]=e['signature']
    local=w.get('semanticLifecycles',[]);history=published['events'] if published else []
    states=lc.replay(history+local,known);impacts=lc.impacts(w['semantics']+w['targets']+w['mappings']+w.get('writes',[])+__import__('record_mappings').governance(__import__('record_mappings').workspace_docs(w)));entries=[]
    local_known=lc.signatures(w['semantics'])
    for uri,sig in sorted(known.items()):
        s=states.get(uri,dict(semanticId=uri,state='active',revision=0,replacementSemanticId=None,history=[]))
        entries.append(dict(s,publishedEventOrigins=[o for o in (published or {}).get("eventReleases",[]) if o["semanticId"]==uri],editable=uri in local_known,signature=sig,signatureSha256=digest(sig),localImpacts=[i for i in impacts if i['semanticId']==uri],publishedImpacts=[i for i in (published or {}).get('impacts',[]) if i['semanticId']==uri]))
    return dict(kind='workspace-semantic-lifecycle',workspaceRevision=snap['revision'],entries=entries,published=published,localEvents=local,approvalAuthority='bifrost',execution='excluded',activation='not-performed')

def apply(store,request,Conflict,adapter):
    lc.require(set(request)=={'revision','semanticId','action','replacementSemanticId','label','description','reason','authoredBy'},'lifecycle.request')
    snap=store.read()
    if snap['revision']!=request['revision']:raise Conflict('최신 저장본을 다시 여세요.')
    w=copy.deepcopy(snap['workspace']);known=lc.signatures(w['semantics']);uri=request['semanticId'];lc.require(uri in known,'lifecycle.uri-missing')
    r=report(store,adapter);local=w.setdefault('semanticLifecycles',[]);ids={(e['id'],e['version']) for e in local}
    # Import verified chains only for URIs explicitly present in this workspace.
    for e in (r['published'] or {}).get('events',[]):
        if e['semanticId'] in known and (e['id'],e['version']) not in ids:local.append(copy.deepcopy(e));ids.add((e['id'],e['version']))
    states=lc.replay(local,known);s=states.get(uri,{'history':[],'revision':0});previous=s['history'][-1] if s['history'] else None
    event=dict(kind='semantic-lifecycle',schemaVersion='2.18.0',id='lifecycle-'+uuid.uuid4().hex,version='1.0.0',semanticId=uri,revision=s['revision']+1,previousEvent=None if previous is None else dict(id=previous['id'],version=previous['version'],sha256=digest(previous)),signatureSha256=digest(known[uri]),authoredAt=datetime.now(timezone.utc).isoformat(),**{k:request[k] for k in ('action','replacementSemanticId','label','description','reason','authoredBy')})
    local.append(event)
    return dict(saved=store.save(request['revision'],w),event=event)
