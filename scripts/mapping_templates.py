"""Bounded mapping recipes and deterministic, pinned materialization. No runtime IO."""
import copy,re
import validate_contracts as vc
from semantic_lifecycle import digest,timestamp,require
import graph_reuse,logical_structures,source_views,source_codecs
KINDS={'mapping-template','template-application'}
def pin(d):return dict(id=d['id'],version=d['version'],sha256=digest(d))
def source_closure(refs,sources):
 found=set();pending=list(refs)
 while pending:
  ref=pending.pop();key=(ref['id'],ref['version']);require(key in sources,'template.view-parent-missing')
  if key in found:continue
  found.add(key);require(len(found)<=128,'template.source-snapshot-limit');parent=sources[key].get('viewOf')
  if parent is not None:pending.append(parent)
 return found

def signature(s,sources=None):
 sources={(s['id'],s['version']):s} if sources is None else sources
 typ='FixedArray' if s.get('fixedArray') is not None else source_views.value_type(s,sources) if s.get('viewOf') is not None else source_codecs.decoded_type(s) if isinstance(s.get('access'),dict) else s['rawRepresentation']['valueType']
 return dict(rawRepresentation={'valueType':typ},unit=copy.deepcopy(s['unit']),inputStage=s['inputStage'],fixedArray=copy.deepcopy(s.get('fixedArray')))
def key(d):return (d['kind'],d['id'],d['version'])
def schema(d):require(not list(vc.schema_validator(d['kind'],'2.19.0').iter_errors(d)),'template.schema')
def walk(value,fn):
 if isinstance(value,dict):
  for k,v in list(value.items()):
   if not fn(value,k,v):walk(v,fn)
 elif isinstance(value,list):
  for v in value:walk(v,fn)
def clean(d):
 d=copy.deepcopy(d)
 walk(d,lambda parent,k,v:(parent.__setitem__(k,[]) or True) if k=='evidenceRefs' else False)
 return d

def template_check(t):
 schema(t);timestamp(t['authoredAt']);require(all(int(x)<=2147483647 for x in t['version'].split('.')),'template.version');slots=t['slots'];refs=[(s['sourceRef']['id'],s['sourceRef']['version']) for s in slots]
 require(len({s['slotId'] for s in slots})==len(slots) and len(set(refs))==len(refs),'template.slot-duplicate')
 graphs=t['graphs'];grefs={(g['id'],g['version']) for g in graphs};require(len(grefs)==len(graphs) and sum(len(g.get('nodes',[])) for g in graphs)<=1024,'template.graph-limit')
 graph_reuse.order(graphs);logical_structures.layout(t['model'])
 require(t['target'].get('semanticDefinitionRef')==dict(id=t['model']['id'],version=t['model']['version']),'template.model-ref')
 require(t['mapping'].get('targetInstanceRef')==dict(id=t['target']['id'],version=t['target']['version']),'template.target-ref')
 def check_ref(p,k,v):
  if k=='sourceRef':require(isinstance(v,dict) and (v.get('id'),v.get('version')) in refs,'template.slot-reference');return True
  if k=='graphRef':require(isinstance(v,dict) and (v.get('id'),v.get('version')) in grefs,'template.graph-reference');return True
  return False
 for d in graphs+[t['mapping']]:walk(d,check_ref)
 # Validate prototype field shapes with a placeholder evidence locator; materialization uses actual source evidence.
 import p3a_contracts as p3
 ev=[{'artifactId':'template-prototype','locator':{'kind':'text-line','line':1}}]
 for d in [t['model'],t['target']]+graphs+[t['mapping']]:
  c=copy.deepcopy(d);walk(c,lambda p,k,v:(p.__setitem__(k,ev) or True) if k=='evidenceRefs' else False)
  require(not p3.schema_errors(c['kind'],c),'template.prototype-schema')
 return t

def materialize(t,a):
 template_check(t);schema(a);timestamp(a['authoredAt']);require(a['templateRef']==pin(t),'template.pin-mismatch')
 require(a['id']=='application-'+a['applicationId']+'-r'+str(a['revision']) and a['version']=='1.0.0','template.application-identity')
 bindings={b['slotId']:b['sourceRef'] for b in a['bindings']};require(len(bindings)==len(a['bindings']) and set(bindings)=={s['slotId'] for s in t['slots']},'template.bindings')
 sources={(s.get('id'),s.get('version')):s for s in a['sourceSnapshots']};require(len(sources)==len(a['sourceSnapshots']) and set(sources)==source_closure(bindings.values(),sources),'template.source-snapshots')
 substitutions={};evidence={}
 for slot in t['slots']:
  ref=bindings[slot['slotId']];s=sources[(ref['id'],ref['version'])]
  require(s.get('kind')=='source-definition' and s.get('status')=='ready' and s.get('equipmentInstanceId')==a['equipmentInstanceId'],'template.source-context')
  require(signature(s,sources)==slot['signature'],'template.slot-incompatible:'+slot['slotId'])
  substitutions[(slot['sourceRef']['id'],slot['sourceRef']['version'])]=copy.deepcopy(ref)
  for e in s.get('evidenceRefs',[]):evidence[digest(e)]=copy.deepcopy(e)
 for source in sources.values():
  import p3a_contracts as p3
  require(not p3.schema_errors('source-definition',source),'template.source-schema')
  require(source.get('status')=='ready' and source.get('equipmentInstanceId')==a['equipmentInstanceId'],'template.source-context')
  for e in source.get('evidenceRefs',[]):evidence[digest(e)]=copy.deepcopy(e)
 require(evidence,'template.evidence-required');ev=[evidence[k] for k in sorted(evidence)]
 prefix='reuse-'+a['applicationId'];generation=prefix+'-r'+str(a['revision']);version='1.0.'+str(a['revision']-1)
 model=copy.deepcopy(t['model']);model.update(id=generation+'-model',version=version)
 target=copy.deepcopy(t['target']);target.update(id=prefix+'-target',version=version,equipmentInstanceId=a['equipmentInstanceId'],label=a['targetLabel'],semanticDefinitionRef=dict(id=model['id'],version=version))
 graphs=sorted(copy.deepcopy(t['graphs']),key=lambda g:(g['id'],g['version']));gr={(g['id'],g['version']):dict(id=generation+'-g'+str(i),version=version) for i,g in enumerate(graphs)}
 mapping=copy.deepcopy(t['mapping']);mapping.update(id=prefix+'-mapping',version=version,equipmentInstanceId=a['equipmentInstanceId'],targetInstanceRef=dict(id=target['id'],version=version))
 for b in mapping['mappings']:b['mappingId']=prefix+'-b'+digest(b['memberPath'])[:12]
 def replace(parent,k,v):
  if k=='sourceRef':parent[k]=substitutions[(v['id'],v['version'])];return True
  if k=='graphRef':parent[k]=gr[(v['id'],v['version'])];return True
  if k=='evidenceRefs':parent[k]=copy.deepcopy(ev);return True
  return False
 for g in graphs:
  ref=gr[(g['id'],g['version'])];g.update(id=ref['id'],version=version,equipmentInstanceId=a['equipmentInstanceId'])
 for d in [model,target]+graphs+[mapping]:walk(d,replace)
 return [model,target]+graphs+[mapping]

def histories(documents):
 unique={}
 for d in documents:
  if d.get('kind') not in KINDS:continue
  require(key(d) not in unique or unique[key(d)]==d,'template.history-conflict');unique[key(d)]=d
 require(len(unique)<=768,'template.history-limit')
 templates={};applications={}
 for d in unique.values():
  schema(d)
  (templates if d['kind']=='mapping-template' else applications).setdefault(d['id'] if d['kind']=='mapping-template' else d['applicationId'],[]).append(d)
 for id,versions in templates.items():
  require(len(versions)<=64,'template.version-limit');versions.sort(key=lambda d:tuple(map(int,d['version'].split('.'))));previous=None
  for t in versions:template_check(t);require(t['previousTemplateRef']==(None if previous is None else pin(previous)),'template.version-chain');previous=t
 by={(t['id'],t['version']):t for versions in templates.values() for t in versions}
 for id,versions in applications.items():
  versions.sort(key=lambda d:d['revision']);previous=None
  for i,a in enumerate(versions,1):
   require(a['revision']==i and a['previousApplicationRef']==(None if previous is None else pin(previous)),'template.application-chain')
   require(previous is None or a['equipmentInstanceId']==previous['equipmentInstanceId'],'template.application-equipment')
   t=by.get((a['templateRef']['id'],a['templateRef']['version']));require(t is not None,'template.missing-version')
   require(a['generated']==materialize(t,a),'template.materialization-drift');previous=a
 return templates,applications

def validate(documents,history=()):
 docs=list(documents);templates,apps=histories(list(history)+docs);by={key(d):d for d in docs};current={}
 for d in docs:
  if d.get('kind')=='template-application':current.setdefault(d['applicationId'],[]).append(d)
 managed={(g['kind'],g['id']):id for id,versions in apps.items() for a in versions for g in a['generated']}
 for d in docs:
  if d.get('kind') not in KINDS and (d.get('kind'),d.get('id')) in managed:require(managed[(d['kind'],d['id'])] in current,'template.provenance-required')
 for d in docs:
  owner=managed.get((d.get('kind'),d.get('id')))
  if owner is not None:
   matches=[g for a in apps[owner] for g in a['generated'] if key(g)==key(d)]
   require(bool(matches) and all(g==d for g in matches),'template.materialization-drift')
 for id,versions in current.items():
  a=max(versions,key=lambda a:a['revision']);require(a['revision']==apps[id][-1]['revision'],'template.application-stale')
  for old in apps[id]:
   if old==a or any(key(g) in by for g in old['generated']):
    for s in old['sourceSnapshots']:require(by.get(key(s))==s,'template.source-pin-mismatch')
  for generated in a['generated']:require(by.get(key(generated))==generated,'template.materialization-drift')
 return templates,apps

def check_workspace(w):
 docs=w.get('mappingTemplates',[])+w.get('templateApplications',[])
 if not docs:return
 require(isinstance(w.get('mappingTemplates',[]),list) and isinstance(w.get('templateApplications',[]),list),'template.workspace')
 all_docs=docs+[r['definition'] for r in w['sources']]+w['semantics']+w['targets']+w['graphs']+w['mappings']
 require(len({key(d) for d in docs})==len(docs),'template.duplicate');validate(all_docs)
def check_transition(before,after):
 for section in ('mappingTemplates','templateApplications'):
  new={key(d):d for d in after.get(section,[])}
  for d in before.get(section,[]):require(new.get(key(d))==d,'template.history-immutable')
