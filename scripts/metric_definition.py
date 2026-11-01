"""2.24 derived metric definition: one Apache Ossie metric over one approved record-mapping result.

The Ossie metric object is carried as written (spec 0.2.0.dev0, `expression.sql` only). Tyr checks what it can
without a SQL engine: the dataset is in the package, every input is a field of it and is read by the expression or
the grain, grain keys are non-null String fields, and the result unit is confirmed. Whether an executed query equals
this expression is decided downstream against the pinned engine, not here.
"""
import re
from semantic_lifecycle import require
KIND='metric-definition'
VERSION='2.24.0'
OSSIE_SPEC='0.2.0.dev0'
LITERAL=re.compile(r"'(?:[^']|'')*'")
IDENTIFIER=re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

def identifiers(sql):
 return {t.lower() for t in IDENTIFIER.findall(LITERAL.sub("''",sql))}

def check(m,records):
 ref=m['dataset']['recordMappingRef'];r=records.get((ref['id'],ref['version']))
 require(r is not None,'metric.dataset-missing')
 fields={f['fieldId']:f for f in r['resultSchema']['fields']}
 require(all(i in fields for i in m['inputs']),'metric.input-missing')
 group=m['grain']['groupBy']
 require(set(group)<=set(m['inputs']),'metric.grain-input')
 require(all(fields[g]['valueType']=='String' and not fields[g]['nullable'] for g in group),'metric.grain-key')
 read=identifiers(m['ossie']['metric']['expression']['sql'])
 require(all(i in read or i in group for i in m['inputs']),'metric.input-unreferenced')
 require(m['result']['unit']['status']=='known','metric.unit-unconfirmed')

def validate(docs):
 """docs: every document in one package or workspace."""
 docs=list(docs);ms=[d for d in docs if d.get('kind')==KIND]
 if not ms:return []
 records={(d['id'],d['version']):d for d in docs if d.get('kind')=='record-mapping'}
 names=set()
 for m in ms:
  check(m,records)
  name=m['ossie']['metric']['name'];require(name not in names,'metric.duplicate-name');names.add(name)
 return ms
