"""Editor-only immutable result schema catalog; published recipes retain existing inline wire schemas."""
import copy,json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
import validate_contracts as vc,record_mappings as rm,mapping_templates as mt
from template_authoring import snapshot,now
D=vc.load(vc.ROOT/'editor-contracts/1.0.0/result-schema-definition.schema.json')
VALIDATOR=Draft202012Validator(D,registry=vc.registry,format_checker=FormatChecker())
RS_VALIDATOR=Draft202012Validator(dict(D['properties']['resultSchema'],**{'$defs':D['$defs']}),registry=vc.registry,format_checker=FormatChecker())
def validate(rs):
 rm.require(not list(RS_VALIDATOR.iter_errors(rs)),'result-schema.shape');fs={f['fieldId']:f for f in rs['fields']};rm.require(len(fs)==len(rs['fields']),'result-schema.duplicate-field');keys=rs['keyFields'];rm.require(len(set(keys))==len(keys) and all(k in fs and fs[k]['valueType']=='String' and not fs[k]['nullable'] for k in keys),'result-schema.key-contract');q=rs['query'];rm.require(q['text'] is None if q['language']=='none' else isinstance(q['text'],str) and bool(q['text'].strip()),'result-schema.query-metadata');return rs

def check(w):
 docs=w.get('resultSchemas',[]);rm.require(isinstance(docs,list) and len(docs)<=256,'result-schema.limit');seen={};groups={};schemas={}
 for d in docs:
  rm.require(not list(VALIDATOR.iter_errors(d)),'result-schema.definition-schema');rm.timestamp(d['authoredAt']);rm.timestamp(d['provenance']['capturedAt']);validate(d['resultSchema']);rm.require(all(int(v)<=2147483647 for v in d['version'].split('.')),'result-schema.version');key=(d['id'],d['version']);rm.require(key not in seen,'result-schema.duplicate');seen[key]=d;rm.require(key==(d['resultSchema']['id'],d['resultSchema']['version']),'result-schema.identity');groups.setdefault(d['id'],[]).append(d);schemas[key]=d['resultSchema']
 for versions in groups.values():
  rm.require(len(versions)<=32,'result-schema.version-limit');versions.sort(key=lambda d:tuple(map(int,d['version'].split('.'))));previous=None
  for d in versions:rm.require(d['previousSchemaRef']==(None if previous is None else mt.pin(previous)),'result-schema.version-chain');previous=d
 catalog_keys=set(schemas)
 for r in w.get('recordMappings',[]):
  rs=r['resultSchema'];key=(rs['id'],rs['version']);rm.require(key not in catalog_keys or schemas[key]==rs,'result-schema.inline-conflict');schemas[key]=rs
 return schemas

def transition(before,after):
 new={(d['id'],d['version']):d for d in after.get('resultSchemas',[])}
 for d in before.get('resultSchemas',[]):rm.require(new.get((d['id'],d['version']))==d,'result-schema.history-immutable')

def listing(store):
 snap=store.read();w=snap['workspace'];schemas=check(w);catalog={(d['id'],d['version']):d for d in w.get('resultSchemas',[])};out=[]
 for key,rs in schemas.items():
  users=[dict(id=r['id'],version=r['version'],label=r['label'],schemaVersion=r['schemaVersion']) for r in w.get('recordMappings',[]) if (r['resultSchema']['id'],r['resultSchema']['version'])==key];d=catalog.get(key);out.append(dict(resultSchema=rs,pin=rm.pin(rs),definition=d,definitionSha256=None if d is None else mt.digest(d),label=d['label'] if d else rs['id'],origin='catalog' if d else 'legacy-inline',usage=users))
 return dict(revision=snap['revision'],schemas=out,definitions=w.get('resultSchemas',[]),execution='excluded')

def plan(store,req,Conflict):
 rm.require(set(req) in ({'revision','definition'},{'revision','definition','planSha256'}),'result-schema.plan-request');w=copy.deepcopy(snapshot(store,req['revision'],Conflict)['workspace']);w.setdefault('resultSchemas',[]).append(copy.deepcopy(req['definition']));check(w);transition(snapshot(store,req['revision'],Conflict)['workspace'],w);d=req['definition'];return dict(revision=req['revision'],definition=d,planSha256=mt.digest(dict(revision=req['revision'],definition=d)),valid=True,resultSchemaPin=rm.pin(d['resultSchema']),persisted=False),w

def apply(store,req,Conflict):
 rm.require('planSha256' in req,'result-schema.plan-required');p,w=plan(store,req,Conflict);rm.require(req['planSha256']==p['planSha256'],'result-schema.plan-changed');return dict(saved=store.save(req['revision'],w),definition=req['definition'],resultSchemaPin=p['resultSchemaPin'])
