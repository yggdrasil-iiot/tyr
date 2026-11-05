"""2.25 command binding: the link from one imported Vor read binding to one OPC UA Method of the same equipment.

Tyr never writes the read binding. Its bytes come from data-edge commissioning and are carried as an evidence-artifact;
Tyr reads profile 0.1.0 with its own parser and reconciles every field it can derive from the package (mapping set,
mapping, target, semantic member, source node, unit, hierarchy path). group, edge and governedDefinitionRef are
deployment facts it cannot see and takes as given; streamId is checked against the export stream at publication.
The command-binding.* codes are the ones Bifrost's publish check uses; read-binding.* are Tyr's reconciliation.
From 2.26 a link names the OPC UA server it may reach (endpointRef): every listed certificate must resolve to an imported
server-certificate artifact whose DER yields the listed thumbprint and the link's applicationUri.
"""
import json,functools
from semantic_lifecycle import require
import validate_contracts as vc
import server_certificate as sc
KIND='command-binding'
VERSION='2.26.0'
PROFILE='0.1.0'
PREFIX='read-binding-'
FIELDS={'profileVersion','streamId','mappingSetRef','mappingId','equipmentInstanceId','semanticId','group','edge','device','metric','governedDefinitionRef','projection'}
TEXT=('streamId','mappingId','equipmentInstanceId','semanticId','group','edge','device','metric')

@functools.cache
def ucum(version=VERSION):
 return set(vc.load(vc.ROOT/'contracts'/version/'common.schema.json')['$defs']['unit']['oneOf'][0]['properties']['code']['enum'])

def text(d,k):return isinstance(d.get(k),str) and d[k]!=''

def profile(raw,code='command-binding.unresolved'):
 """Profile 0.1.0 from its bytes: exactly the twelve fields, identity projection, non-empty strings."""
 try:b=json.loads(raw.decode('utf-8'))
 except (UnicodeDecodeError,ValueError) as e:raise ValueError(code) from e
 require(isinstance(b,dict) and set(b)==FIELDS and b['profileVersion']==PROFILE and b['projection']=='identity',code)
 require(all(text(b,k) for k in TEXT),code)
 s,d=b['mappingSetRef'],b['governedDefinitionRef']
 require(isinstance(s,dict) and set(s)=={'id','version'} and text(s,'id') and text(s,'version'),code)
 require(isinstance(d,dict) and set(d)=={'templateRef','version','sha256'} and text(d,'templateRef') and text(d,'version'),code)
 require(isinstance(d['sha256'],str) and len(d['sha256'])==64 and all(c in '0123456789abcdef' for c in d['sha256']),code)
 return b

def find(docs,kind,ref):
 return next((d for d in docs if d.get('kind')==kind and d.get('id')==ref.get('id') and d.get('version')==ref.get('version')),None)

def path(h,equipment):
 """Root first, joined with ':', as Muninn publishes the Sparkplug device id."""
 nodes={n['equipmentInstanceId']:n for n in h['nodes']};out=[];cursor=equipment
 while cursor is not None:
  require(cursor in nodes and len(out)<=64,'command-binding.unresolved')
  out.insert(0,cursor);cursor=nodes[cursor]['parentEquipmentInstanceId']
 return ':'.join(out)

def reconcile(b,docs,h):
 """Every field Tyr can derive must agree with its own documents: the rules Vor applies when it reads."""
 s=find(docs,'mapping-set',b['mappingSetRef']);require(s is not None,'command-binding.unresolved')
 m=next((x for x in s['mappings'] if x['mappingId']==b['mappingId']),None);require(m is not None,'command-binding.unresolved')
 require(s['equipmentInstanceId']==b['equipmentInstanceId'] and b['device']==path(h,b['equipmentInstanceId']),'command-binding.device-path')
 steps=m['memberPath'];require(len(steps)==1 and steps[0]['kind']=='member','read-binding.member-path')
 t=find(docs,'target-instance',s['targetInstanceRef'] or {});require(t is not None and t['equipmentInstanceId']==b['equipmentInstanceId'],'read-binding.target-equipment')
 model=find(docs,'semantic-definition',t['semanticDefinitionRef']) or {}
 member=next((x for x in model.get('members',[]) if x['memberId']==steps[0]['memberId']),None);require(member is not None,'read-binding.member-path')
 require(member['semanticId']==b['semanticId'],'read-binding.semantic-id')
 require(member['name']==b['metric'],'read-binding.metric')
 v=m['valueRef'];src=find(docs,'source-definition',v.get('sourceRef') or {}) if v['kind']=='source' else None
 a=(src or {}).get('access') or {}
 # Muninn names a metric by the member's browse name, the last segment of the OPC UA node identifier.
 require(a.get('kind')=='opcua-node' and str(a.get('identifier','')).endswith('.'+b['metric']),'read-binding.source-node')
 require(m['outputUnit']==member['unit'],'read-binding.output-unit')

def endpoint(c,docs,read):
 """Bifrost's publish check for endpointRef: each certificate resolves, parses, and yields the listed values, once."""
 e=c['endpointRef'];seen=set()
 for x in e['certificates']:
  a=find(docs,'evidence-artifact',x['certificateRef'])
  require(a is not None and a['schemaVersion']=='1.1.0' and a['id'].startswith(sc.PREFIX) and a['file']['mediaType']==sc.MEDIA,'command-binding.endpoint')
  try:t,u=sc.parse(read(a['file']['path']))
  except ValueError as err:raise ValueError('command-binding.endpoint') from err
  require(t==x['thumbprintSha1'] and u==e['applicationUri'] and t not in seen,'command-binding.endpoint');seen.add(t)

def validate(docs,read):
 """docs: every document in one package; read(path) returns a data file's bytes. Returns the profiles by artifact id."""
 docs=list(docs);hs=[d for d in docs if d.get('kind')=='equipment-hierarchy'];links=[d for d in docs if d.get('kind')==KIND]
 # A link names its read binding by id@version, and only an imported read binding (the prefixed artifact) can be one.
 for c in links:require(c['readBindingRef']['id'].startswith(PREFIX),'command-binding.unresolved')
 arts={(d['id'],d['version']):d for d in docs if d.get('kind')=='evidence-artifact' and d['id'].startswith(PREFIX)}
 if not links and not arts:return {}
 profiles={}
 for i,a in arts.items():
  b=profile(read(a['file']['path']));require(len(hs)==1,'command-binding.unresolved')
  reconcile(b,docs,hs[0]);profiles[i]=b
 keys=set()
 for c in links:
  eq=c['equipmentRef'];h=find(docs,'equipment-hierarchy',eq);a=find(docs,'evidence-artifact',c['readBindingRef'])
  require(h is not None and a is not None and a['schemaVersion']=='1.1.0','command-binding.unresolved')
  require(any(n['equipmentInstanceId']==eq['equipmentInstanceId'] for n in h['nodes']),'command-binding.unresolved')
  b=profiles[(a['id'],a['version'])]
  require(b['equipmentInstanceId']==eq['equipmentInstanceId'] and b['device']==path(h,eq['equipmentInstanceId']),'command-binding.device-path')
  ins=c['method']['inputs']
  require(len(ins)==1 and ins[0]['name']!='' and ins[0]['type']=='Double' and ins[0]['unit'] in ucum(c['schemaVersion']),'command-binding.inputs')
  if c['schemaVersion']==VERSION:endpoint(c,docs,read)
  key=(b['device'],c['method']['methodNodeId']);require(key not in keys,'command-binding.duplicate');keys.add(key)
 return profiles
