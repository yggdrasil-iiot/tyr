"""Attribution and impact rule authoring API: listing, plan and apply under revision CAS. Approval stays with Bifrost.

The listing shows what a rule can name: the hierarchy paths of the workspace equipment and every mapping of every mapping set
with its equipment path, metric (the semantic leaf's name), semantic id and value type, plus the authored profiles as the
evidence-artifact ids their references use and the citable evidence ids. Rules and profiles are written here; the checks are
the workspace's (workspace_v2.check -> binding_profiles, attribution_rule, impact_rule).
"""
import copy
import attribution_rule as ar
import impact_rule as ir
import logical_structures as ls
from semantic_lifecycle import digest
from template_authoring import snapshot
SECTIONS=('occupancyBindings','incidentBindings','attributionRules','impactRules')
def require(ok,code):
    if not ok:raise ValueError(code)
def catalog(w):
    """Every mapping of the workspace as a rule member candidate; mappings whose target, model or member does not resolve are left out."""
    hs=w.get('equipmentHierarchies',[])
    try:paths=ar.paths(hs[0]) if hs else {}
    except ValueError:paths={}   # a hierarchy the hierarchy check refuses: the catalog shows no paths, the findings show the hierarchy.* code
    targets={(t['id'],t['version']):t for t in w['targets']};models={(m['id'],m['version']):m for m in w['semantics']};out=[]
    for s in w['mappings']:
        t=targets.get((s['targetInstanceRef']['id'],s['targetInstanceRef']['version']));sem=models.get((t['semanticDefinitionRef']['id'],t['semanticDefinitionRef']['version'])) if t else None
        if sem is None:continue
        for m in s['mappings']:
            try:leaf=ls.resolve(sem,m['memberPath'])
            except ls.StructureError:continue
            out.append({'mappingSetRef':{'id':s['id'],'version':s['version']},'mappingId':m['mappingId'],'equipmentInstanceId':s['equipmentInstanceId'],'equipmentPath':paths.get(s['equipmentInstanceId']),'metric':leaf['name'],'semanticId':leaf['semanticId'],'valueType':leaf['valueType']})
    return out,paths,hs[0] if hs else None
def listing(store,build_package):
    snap=store.read();w=snap['workspace']
    require(w.get('workspaceVersion')=='2.0.0','먼저 객체 식별 마이그레이션을 완료하세요.')
    members,paths,h=catalog(w)
    profiles=lambda section,prefix:[dict(r,artifactId=prefix+r['id']) for r in w.get(section,[])]
    citable=sorted({'manual-'+s['definition']['id'] for s in w['sources']}|{'hierarchy-'+r['id'] for r in w.get('hierarchyEvidence',[])})
    return {'revision':snap['revision'],'hierarchy':{'id':h['id'],'version':h['version'],'paths':paths} if h else None,'members':members,
            'occupancyBindings':profiles('occupancyBindings',ar.PREFIX),'incidentBindings':profiles('incidentBindings',ir.PREFIX),
            'attributionRules':w.get('attributionRules',[]),'impactRules':w.get('impactRules',[]),'citable':citable,
            'findings':[f for f in snap['findings'] if f['ruleCode'].startswith(('attribution','impact','occupancy-binding','incident-binding','rule.envelope'))],'approvalAuthority':'bifrost'}
def candidate(w,req):
    w=copy.deepcopy(w)
    for key in SECTIONS:
        if req[key]:w[key]=copy.deepcopy(req[key])
        else:w.pop(key,None)
    return w
def request(store,req,Conflict):
    require(isinstance(req,dict) and set(req) in ({'revision',*SECTIONS},{'revision',*SECTIONS,'planSha256'}),'attribution-rule.plan-request')
    require(all(isinstance(req[k],list) for k in SECTIONS),'attribution-rule.limit')
    before=snapshot(store,req['revision'],Conflict)['workspace']
    return before,candidate(before,req),digest({'revision':req['revision'],**{k:req[k] for k in SECTIONS}})
def plan(store,req,Conflict,check_state):
    before,w,sha=request(store,req,Conflict)
    check_state(w);__import__('binding_profiles').transition(before,w)
    return {'revision':req['revision'],'planSha256':sha,'valid':True},w
def apply(store,req,Conflict):
    """store.save runs the same state check and every transition rule, so the plan is not re-run here."""
    require('planSha256' in req,'attribution-rule.plan-required')
    _,w,sha=request(store,req,Conflict);require(req['planSha256']==sha,'attribution-rule.plan-changed')
    return {'saved':store.save(req['revision'],w),'planSha256':sha}
