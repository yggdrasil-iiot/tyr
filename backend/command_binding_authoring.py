"""Command-binding authoring API: listing, plan and apply under revision CAS. Approval stays with Bifrost.

The listing shows each imported read binding as the reviewer will approve it: the profile text, its digest and the
result of reconciling it against the workspace. Each imported server certificate is shown with the thumbprint and
subjectAltName URI derived from its DER, the values a link's endpointRef must carry. Tyr writes the links; profiles and
certificates are imported, never edited.
"""
import base64,copy,tempfile
from pathlib import Path
import validate_contracts as vc
import read_bindings as rb
import server_certificates as scs
import command_binding as cb
from semantic_lifecycle import digest
from template_authoring import snapshot
def require(ok,code):
    if not ok:raise ValueError(code)
def reconciled(w,build_package):
    """Per imported record: 'ok', or the refusal code reconciliation gives for that profile alone."""
    out={}
    with tempfile.TemporaryDirectory(prefix='tyr-command-binding-') as t:
        root=Path(t);build_package(w,root);p=vc.load(root/'proposal.json')
        docs=[vc.load(root/e['path']) for e in p['files']];hs=[d for d in docs if d['kind']=='equipment-hierarchy']
        for r in w.get('readBindings',[]):
            try:
                require(len(hs)==1,'command-binding.unresolved')
                cb.reconcile(cb.profile(rb.raw(r),'read-binding.profile'),docs,hs[0]);out[r['id']]='ok'
            except ValueError as e:out[r['id']]=str(e)
    return out
KEYS=('readBindings','serverCertificates','commandBindings')
def derived(r):
    try:t,u=scs.derive(scs.raw(r));return {'thumbprintSha1':t,'applicationUri':u}
    except ValueError as e:return {'thumbprintSha1':None,'applicationUri':None,'refusal':str(e)}
def listing(store,build_package):
    snap=store.read();w=snap['workspace']
    require(w.get('workspaceVersion')=='2.0.0','먼저 객체 식별 마이그레이션을 완료하세요.')
    status=reconciled(w,build_package)
    profiles=[{'id':r['id'],'version':r['version'],'artifactId':cb.PREFIX+r['id'],'label':r['label'],'origin':r['origin'],'reviewer':r['reviewer'],'sha256':r['sha256'],
               'text':base64.b64decode(r['bytesBase64']).decode('utf-8',errors='replace'),'reconciliation':status.get(r['id'])} for r in w.get('readBindings',[])]
    citable=sorted({'manual-'+s['definition']['id'] for s in w['sources']})
    hs=w.get('equipmentHierarchies',[])
    certificates=[{'id':r['id'],'version':r['version'],'artifactId':cb.sc.PREFIX+r['id'],'label':r['label'],'origin':r['origin'],'reviewer':r['reviewer'],'sha256':r['sha256'],'scope':r['scope'],**derived(r)}
                  for r in w.get('serverCertificates',[])]
    return {'revision':snap['revision'],'readBindings':w.get('readBindings',[]),'profiles':profiles,'serverCertificates':w.get('serverCertificates',[]),'certificates':certificates,'commandBindings':w.get('commandBindings',[]),
            'hierarchy':{'id':hs[0]['id'],'version':hs[0]['version'],'equipment':[n['equipmentInstanceId'] for n in hs[0]['nodes']]} if hs else None,'units':sorted(cb.ucum()),'citable':citable,
            'findings':[f for f in snap['findings'] if f['ruleCode'].startswith(('command-binding','read-binding','server-certificate'))],'approvalAuthority':'bifrost'}
def candidate(w,req):
    w=copy.deepcopy(w)
    for key in KEYS:
        if req[key]:w[key]=copy.deepcopy(req[key])
        else:w.pop(key,None)
    return w
def request(store,req,Conflict):
    require(isinstance(req,dict) and set(req) in ({'revision',*KEYS},{'revision',*KEYS,'planSha256'}),'command-binding.plan-request')
    require(all(isinstance(req[k],list) for k in KEYS),'command-binding.limit')
    before=snapshot(store,req['revision'],Conflict)['workspace']
    return before,candidate(before,req),digest({'revision':req['revision'],**{k:req[k] for k in KEYS}})
def plan(store,req,Conflict,check_state):
    before,w,sha=request(store,req,Conflict)
    check_state(w);rb.transition(before,w);scs.transition(before,w)
    return {'revision':req['revision'],'planSha256':sha,'valid':True},w
def apply(store,req,Conflict):
    """store.save runs the same state check and every transition rule, so the plan is not re-run here."""
    require('planSha256' in req,'command-binding.plan-required')
    _,w,sha=request(store,req,Conflict);require(req['planSha256']==sha,'command-binding.plan-changed')
    return {'saved':store.save(req['revision'],w),'planSha256':sha}
