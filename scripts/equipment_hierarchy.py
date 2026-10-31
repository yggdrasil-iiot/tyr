"""2.23 ISA-95 equipment hierarchy: reviewer-stated levels and parents, governed metadata only.

Levels are the OPC 10030 v1.00 ISA95EquipmentElementLevelEnum names exactly as Table 36 prints them
(including PRODUCTIONUINT_7). Nothing here infers a level, and nothing here reaches authorization or topics.
"""
from semantic_lifecycle import require
KIND='equipment-hierarchy'
VERSION='2.23.0'
MAX_DEPTH=64

def check(h):
 by={}
 for n in h['nodes']:
  require(n['equipmentInstanceId'] not in by,'hierarchy.duplicate-node');by[n['equipmentInstanceId']]=n
 for n in h['nodes']:
  p=n['parentEquipmentInstanceId']
  require(p is None or p in by,'hierarchy.parent-missing')
 for n in h['nodes']:
  seen={n['equipmentInstanceId']};p=n['parentEquipmentInstanceId'];depth=1
  while p is not None:
   require(p not in seen,'hierarchy.cycle');seen.add(p);depth+=1
   require(depth<=MAX_DEPTH,'hierarchy.depth');p=by[p]['parentEquipmentInstanceId']
 return by

def validate(docs,equipment=None):
 """docs: every document in one package or workspace. equipment: workspace equipment ids, when known."""
 docs=list(docs);hs=[d for d in docs if d.get('kind')==KIND]
 if not hs:return None
 require(len(hs)==1,'hierarchy.multiple')
 by=check(hs[0])
 if equipment is not None:require(set(by)<=set(equipment),'hierarchy.context-equipment')
 for d in docs:
  if d.get('kind')!=KIND and 'equipmentInstanceId' in d:require(d['equipmentInstanceId'] in by,'hierarchy.unresolved-instance')
 return hs[0]
