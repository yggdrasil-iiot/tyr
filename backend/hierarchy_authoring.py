"""Equipment-hierarchy authoring API: listing, plan and apply under revision CAS. Approval stays with Bifrost."""
import copy,json,tempfile
from pathlib import Path
import validate_contracts as vc
import import_files
import hierarchy_evidence as he
from semantic_lifecycle import digest
from template_authoring import snapshot
SCHEMA=vc.load(vc.ROOT/'contracts/2.23.0/equipment-hierarchy.schema.json')
PREVIEW_LINES=500
PREVIEW_CELLS=2000
def require(ok,code):
    if not ok:raise ValueError(code)
def levels():return SCHEMA['properties']['nodes']['items']['properties']['equipmentLevel']['enum']
def preview(art,root):
    """What a reviewer can cite: numbered lines for text, filled cells for xlsx."""
    media=art['file']['mediaType'];b=vc.safe(root,art['file']['path']).read_bytes()
    if media.startswith('text/'):
        lines=b.decode('utf-8').splitlines();return {'kind':'text-line','lines':lines[:PREVIEW_LINES],'lineCount':len(lines)}
    if media==he.MEDIA['xlsx']:
        cells=import_files.xlsx(b)[1];return {'kind':'xlsx-cell','cells':[[s,c,v['value']] for (s,c),v in list(cells.items())[:PREVIEW_CELLS]],'cellCount':len(cells)}
    return {'kind':'json-pointer'}
def listing(store,build_package):
    snap=store.read();w=snap['workspace']
    require(w.get('workspaceVersion')=='2.0.0','먼저 객체 식별 마이그레이션을 완료하세요.')
    artifacts=[]
    with tempfile.TemporaryDirectory(prefix='tyr-hierarchy-') as t:
        root=Path(t);build_package(w,root);p=vc.load(root/'proposal.json')
        for e in p['files']:
            if e['kind']!='evidence-artifact':continue
            art=vc.load(root/e['path'])
            try:pv=preview(art,root)
            except (OSError,ValueError,KeyError) as ex:pv={'kind':'unreadable','error':str(ex)}
            artifacts.append({'artifactId':art['id'],'version':art['version'],'mediaType':art['file']['mediaType'],'scope':art['scope'],'origin':art['origin'],'source':'hierarchy' if art['id'].startswith(he.PREFIX) else 'import' if art['id'].startswith('import-') else 'manual','preview':pv})
    hs=w.get('equipmentHierarchies',[])
    return {'revision':snap['revision'],'equipment':w['equipment'],'hierarchy':hs[0] if hs else None,'evidence':w.get('hierarchyEvidence',[]),
            'artifacts':artifacts,'levels':levels(),'findings':[f for f in snap['findings'] if f['ruleCode'].startswith(('hierarchy','evidence'))],'approvalAuthority':'bifrost'}
def candidate(w,req):
    w=copy.deepcopy(w)
    if req['hierarchy'] is None:w.pop('equipmentHierarchies',None)
    else:w['equipmentHierarchies']=[copy.deepcopy(req['hierarchy'])]
    if req['evidence']:w['hierarchyEvidence']=copy.deepcopy(req['evidence'])
    else:w.pop('hierarchyEvidence',None)
    return w
def request(store,req,Conflict):
    require(isinstance(req,dict) and set(req) in ({'revision','hierarchy','evidence'},{'revision','hierarchy','evidence','planSha256'}),'hierarchy.plan-request')
    require(isinstance(req['evidence'],list),'hierarchy-evidence.limit')
    before=snapshot(store,req['revision'],Conflict)['workspace']
    return before,candidate(before,req),digest({'revision':req['revision'],'hierarchy':req['hierarchy'],'evidence':req['evidence']})
def plan(store,req,Conflict,check_state):
    before,w,sha=request(store,req,Conflict)
    check_state(w);he.transition(before,w)
    return {'revision':req['revision'],'planSha256':sha,'valid':True},w
def apply(store,req,Conflict):
    """store.save runs the same state check and every transition rule, so the plan is not re-run here."""
    require('planSha256' in req,'hierarchy.plan-required')
    _,w,sha=request(store,req,Conflict);require(req['planSha256']==sha,'hierarchy.plan-changed')
    return {'saved':store.save(req['revision'],w),'planSha256':sha}
