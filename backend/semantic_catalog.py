"""Read-only workspace comparison. Registry trust and signature verification belong to Bifrost."""
import copy
import logical_structures as logical
import sample_quality as sq
import publication

def report(store,adapter):
    snapshot=store.read();workspace=snapshot['workspace'];catalog=None
    if adapter.configured:
        catalog=adapter.call('catalog',adapter.registry)
        publication.require(catalog.get('kind')=='semantic-catalog','Bifrost catalog unavailable: '+str(catalog.get('error','invalid response')))
        publication.require(not list(publication.vc.schema_validator('semantic-catalog','2.16.0').iter_errors(catalog)),'Invalid Bifrost catalog schema')
        unhashed=copy.deepcopy(catalog);claimed=unhashed.pop('catalogSha256')
        publication.require(sq.digest(unhashed)==claimed,'Bifrost catalog digest mismatch')
    known={e['semanticId']:e for e in catalog['entries']} if catalog else {}
    grouped={}
    def authored(nodes,path=()):
        for n in nodes:
            here=path+(n['memberId'],)
            yield n,list(here)
            yield from authored(n.get('members',[]),here)
    publication.require(workspace.get('workspaceVersion')=='2.0.0','Migrate workspace before catalog comparison')
    for d in workspace['semantics']:
        logical.layout(d)
        for n,path in authored(d['members']):
            uri=n['semanticId'];entry=grouped.setdefault(uri,{'semanticId':uri,'variants':[]})
            signature=logical.signature(n)
            variant=next((x for x in entry['variants'] if x['signature']==signature),None)
            if variant is None:
                variant={'signature':signature,'occurrences':[]};entry['variants'].append(variant)
            variant['occurrences'].append({'definitionId':d['id'],'definitionVersion':d['version'],'memberId':n['memberId'],'definitionPath':path,'label':n['name']})
    entries=[]
    for uri,e in sorted(grouped.items()):
        registered=known.get(uri)
        if len(e['variants'])!=1:status='workspace-conflict'
        elif not catalog:status='registry-unavailable'
        elif registered and (not registered['compatible'] or registered['variants'][0]['signature']!=e['variants'][0]['signature']):status='registry-conflict'
        else:status='compatible' if registered else 'new'
        entries.append(dict(e,status=status,registry=copy.deepcopy(registered)))
    return {'kind':'workspace-semantic-catalog','version':1,'workspaceRevision':snapshot['revision'],'workspaceSha256':sq.digest(workspace),
            'configured':adapter.configured,'catalog':catalog,'entries':entries,'approvalAuthority':'bifrost','execution':'excluded','activation':'not-performed'}
