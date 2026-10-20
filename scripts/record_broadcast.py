"""2.22 bounded row fan-out definitions; common sources are immutable pinned inputs."""
import copy
import mapping_templates as mt,record_mappings as rm
from semantic_lifecycle import require
VERSION='2.22.0'
def basic(r,t):
 require(r['output']['mode']=='array','broadcast.array-required')
 sources={(s.get('id'),s.get('version')):s for s in r['commonSources']};require(len(sources)==len(r['commonSources']),'broadcast.source-duplicate')
 slots={s['slotId']:s for s in t['slots']};used=set()
 import p3a_contracts as p3
 for b in r['commonBindings']:
  ref=b['sourceRef'];key=(ref['id'],ref['version']);s=sources.get(key);require(s is not None and mt.pin(s)==ref,'broadcast.source-pin');used.add(key)
  require(not p3.schema_errors('source-definition',s),'broadcast.source-schema')
  require(s.get('viewOf') is None and s.get('fixedArray') is None and s.get('recordField') is None,'broadcast.direct-scalar-required')
  require(s['status']=='ready' and s['equipmentInstanceId']==r['equipmentInstanceId'] and s.get('accessMode','read')=='read','broadcast.source-context')
  require(mt.signature(s)==slots[b['slotId']]['signature'],'broadcast.slot-signature')
 require(used==set(sources),'broadcast.source-closure')
 require(all(b.get('temporalPolicy') is None for b in t['mapping']['mappings']),'broadcast.frame-policy-required')
 return r

def source_pins(r,docs):
 by={(d['id'],d['version']):d for d in docs if d.get('kind')=='source-definition'}
 for s in r['commonSources']:require(by.get((s['id'],s['version']))==s,'broadcast.source-pin-mismatch')

def policy(r):
 p=r['commonPolicy'];return dict(assembly='latest',timestampBasis='source',maxAgeMs=p['maxAgeMs'],maxSkewMs=p['maxSkewMs'],uncertainInput=p['uncertainInput'],missingInput='reject',badInput='propagate')
