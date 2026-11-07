"""2.27 attribution rule: the forseti stage-1 rule that joins governed process members with MES occupancy per station and tool.

Tyr authors the rule and the occupancy binding profile it names and checks both before export with the codes Bifrost's
AttributionRules and OccupancyBindingProfile use (spec "Attribution rule (mapping contract 2.27.0)" and "Binding profiles").
Everything resolves inside the package: the ISA-95 hierarchy, the stations (paths that do not nest), the members (one mapping
each, named by the metric Muninn publishes and the semantic id of the leaf it maps), one Boolean activity member per equipment,
the profile carried by an evidence-artifact 1.1.0, the plc-stamped identity members and the temporal order. The first failure
stops the rule. Approval stays with Bifrost; whether format.schemaSha256 equals forseti's built-in schema is forseti's start-up
check (binding.schema-mismatch), not Tyr's or Bifrost's. No Bifrost or forseti code is read.
"""
import json,re,warnings
from semantic_lifecycle import require
import validate_contracts as vc
import logical_structures as ls
import equipment_hierarchy as eh
KIND='attribution-rule'
VERSION='2.27.0'
PROFILE='0.1.0'
PREFIX='occupancy-binding-'
MEDIA='application/vnd.forseti.occupancy-binding+json'
SCHEMA_ID='urn:forseti:schema:occupancy:1.0.0'
REASONS={'urn:epcglobal:cbv:er:did_not_occur','urn:epcglobal:cbv:er:incorrect_data'}
FIELDS={'profileVersion','topic','format','identity','enter','leave','correction','timestampBasis','sources'}
MAX_DEPTH=32
MAX_REPEAT=2147483647   # Java Pattern: a repetition bound above Integer.MAX_VALUE is "Illegal repetition range"; Python's re would accept up to 4294967295
DIGEST=re.compile('[0-9a-f]{64}')

def text(d,k):return isinstance(d,dict) and isinstance(d.get(k),str) and d[k]!=''
def names(d):return set(d) if isinstance(d,dict) else None
def strings(a,code):
 """A non-empty list of distinct non-empty strings."""
 require(isinstance(a,list) and len(a)>0,code);out=[]
 for x in a:require(isinstance(x,str) and x!='' and x not in out,code);out.append(x)
 return out
def digest_form(v):return isinstance(v,str) and DIGEST.fullmatch(v) is not None

def occupancy_profile(raw,code='attribution.binding-profile'):
 """Profile 0.1.0 from its bytes: exactly the nine fields, the constants, non-empty values, the reasons subset, the pattern subset.
 Read from the bytes as Bifrost's MappingJson reader reads them: a UTF-8 BOM is skipped (json.loads detects utf-8-sig on bytes),
 duplicate JSON keys are refused (vc.pairs), and any decoder failure, nesting past Python's recursion limit included, is the code."""
 try:b=json.loads(raw,object_pairs_hook=vc.pairs)
 except (UnicodeDecodeError,ValueError,RecursionError) as e:raise ValueError(code) from e
 require(names(b)==FIELDS and b['profileVersion']==PROFILE and text(b,'topic') and b['timestampBasis']=='eventTime',code)
 f,i,enter,leave,c=b['format'],b['identity'],b['enter'],b['leave'],b['correction']
 require(names(f)=={'schemaId','schemaSha256'} and f['schemaId']==SCHEMA_ID and digest_form(f['schemaSha256']),code)
 require(names(i)=={'scheme','pattern'} and i['scheme']=='mes-unit-id' and text(i,'pattern'),code)
 require(names(enter)=={'bizStep'} and text(enter,'bizStep') and names(leave)=={'bizStep'} and text(leave,'bizStep'),code)
 require(names(c)=={'errorDeclaration','reasons'} and c['errorDeclaration']=='reissue-same-event-id',code)
 reasons=strings(c['reasons'],code);strings(b['sources'],code)
 require(set(reasons)<=REASONS,code)
 require(pattern_accepted(i['pattern']),code)
 return b

class _Pattern:
 """Spec 225: literals, '.', bracket classes with ranges and negation, a backslash before a non-alphanumeric ASCII character, the
 quantifiers * + ? {m} {m,} {m,n}, alternation and non-capturing groups. Anchors, lookaround, backreferences, flags, named or
 capturing groups, shorthand, property or POSIX classes, lazy or possessive quantifiers, Java's '&&', a bare '{', nesting deeper
 than MAX_DEPTH, a repetition bound above MAX_REPEAT and any surrogate or supplementary character (one code point in Java, two
 code units in ECMA-262) are refused, as Bifrost's BindingPattern refuses them."""
 def __init__(s,p):s.s=p;s.i=0;s.depth=0;s.mark=0;s.out=[]
 def at(s,c):return s.i<len(s.s) and s.s[s.i]==c
 def alternation(s):
  s.sequence()
  while s.at('|'):s.i+=1;s.sequence()
 def sequence(s):
  while s.i<len(s.s) and not s.at('|') and not s.at(')'):s.atom();s.quantifier()
 def atom(s):
  c=s.s[s.i]
  if c=='(':
   require(s.s.startswith('(?:',s.i) and s.depth<MAX_DEPTH,'group');s.i+=3;s.depth+=1;s.alternation();s.depth-=1;require(s.at(')'),'group');s.i+=1
  elif c=='[':s.char_class()
  elif c=='\\':s.escape()
  elif c=='.':s.i+=1
  elif c in '^$)*+?{}|]':raise ValueError('meta')
  else:s.i+=1
 def escape(s):
  require(s.i+1<len(s.s),'escape');n=s.s[s.i+1];require(ord(n)<128 and not n.isalnum(),'escape');s.i+=2
 def char_class(s):
  s.i+=1
  if s.at('^'):s.i+=1
  require(not s.at(']'),'class')
  while not s.at(']'):
   require(s.i<len(s.s),'class');s.class_char()
   if s.at('-') and s.i+1<len(s.s) and s.s[s.i+1]!=']':s.i+=1;s.class_char()
  s.i+=1
 def class_char(s):
  c=s.s[s.i]
  if c=='\\':s.escape()
  else:require(c!='[' and c!=']' and not (c=='&' and s.i+1<len(s.s) and s.s[s.i+1]=='&'),'class');s.i+=1
 def quantifier(s):
  if s.i>=len(s.s):return
  c=s.s[s.i]
  if c in '*+?':s.i+=1
  elif c=='{':
   close=s.s.find('}',s.i);require(close>s.i,'quantifier');q=s.s[s.i+1:close]
   require(re.fullmatch('[0-9]+|[0-9]+,|[0-9]+,[0-9]+',q) is not None,'quantifier')
   # Java accumulates leading zeros ({000...01} is 1) and Python's int() refuses more than 4,300 digits: strip them first, then
   # bound as Pattern.compile does (above Integer.MAX_VALUE: Illegal repetition range) and compile the normalised text later
   parts=[(x.lstrip('0') or '0') if x else '' for x in q.split(',')];bounds=[int(x) for x in parts if x]
   require(all(b<=MAX_REPEAT for b in bounds) and bounds[0]<=bounds[-1],'quantifier')
   s.out.append(s.s[s.mark:s.i]+'{'+','.join(parts)+'}');s.i=close+1;s.mark=s.i
  else:return
  require(not (s.at('?') or s.at('+') or s.at('*') or s.at('{')),'quantifier')
 def normalised(s):
  """The pattern with every quantifier's leading zeros stripped: what Python's re is asked to compile (same syntax, Java's values)."""
  return ''.join(s.out)+s.s[s.mark:]

def pattern_accepted(p):
 """True when p is inside the subset and compiles; Python's re is a syntax check here, the job's engine is Java's."""
 if not isinstance(p,str) or p=='':return False
 if any(0xD800<=ord(c)<=0xDFFF or ord(c)>0xFFFF for c in p):return False
 b=_Pattern(p)
 try:
  b.alternation()
  if b.i!=len(p):return False
  # Java reads '--', '~~' and '||' inside a class as literals; Python's re agrees but warns (FutureWarning, set operations)
  with warnings.catch_warnings():warnings.simplefilter('ignore',FutureWarning);re.compile(b.normalised())
  return True
 except (ValueError,re.error,OverflowError):return False
def find(docs,kind,ref):
 return next((d for d in docs if d.get('kind')==kind and d.get('id')==ref.get('id') and d.get('version')==ref.get('version')),None)
def key(ref):return ref['id']+'@'+ref['version']
def paths(h):
 """Each node's hierarchy path, root first, joined with ':': the string Muninn publishes as the Sparkplug device id and the
 occupancy readPoint carries (the rule of command_binding.path). equipment_hierarchy.check runs first, so a duplicate node, a
 missing parent, a cycle or an over-deep chain raises the hierarchy's own code (spec 130) instead of looping or failing on a key."""
 by=eh.check(h);out={}
 for i in by:
  p=[];c=i
  while c is not None:p.insert(0,c);c=by[c]['parentEquipmentInstanceId']
  out[i]=':'.join(p)
 return out
def within(stations,path):
 """A path is a station of the rule or a descendant of one (a tool). Ids carry no ':', so the prefix test is exact."""
 return any(path==s or path.startswith(s+':') for s in stations)
def distinct_names(sem):
 """Spec 132: within one semantic definition no two leaf members share a name (a station and a tool may, across definitions)."""
 try:nodes=ls.layout(sem)['definitions']
 except ls.StructureError:return False
 seen=set()
 for m in nodes:
  if m['valueType'] in ls.CONTAINERS:continue
  if m['name'] in seen:return False
  seen.add(m['name'])
 return True
def members(docs,paths_):
 """Every mapping of the package by mappingId: its set key, its equipment's hierarchy path, the semantic leaf it maps, whether
 its memberPath is one step, whether its definition's leaf names are distinct, and its OPC UA node identifier (None unless
 the source is an opcua-node). A mapping whose target, definition, equipment or member path does not resolve is left out and
 is then attribution.member-unresolved; p3a_contracts reports its own code for it as well."""
 out={};distinct={}
 for s in docs:
  if s.get('kind')!='mapping-set':continue
  t=find(docs,'target-instance',s['targetInstanceRef'] or {});sem=find(docs,'semantic-definition',t['semanticDefinitionRef']) if t else None;path=paths_.get(s['equipmentInstanceId'])
  if sem is None or path is None:continue
  names_ok=distinct.setdefault(key(sem),distinct_names(sem))
  for m in s['mappings']:
   try:leaf=ls.resolve(sem,m['memberPath'])
   except ls.StructureError:continue
   v=m['valueRef'];src=find(docs,'source-definition',v.get('sourceRef') or {}) if v['kind']=='source' else None
   a=(src or {}).get('access') or {};ident=a.get('identifier') if a.get('kind')=='opcua-node' else None
   require(m['mappingId'] not in out,'mapping.duplicate-id')
   out[m['mappingId']]={'set':key(s),'path':path,'leaf':leaf,'one':len(m['memberPath'])==1,'distinct':names_ok,'identifier':None if ident is None else str(ident)}
 return out
def typed(rule,ref,path,value_type):
 x=rule.get(ref);return x is not None and x['path']==path and x['leaf']['valueType']==value_type
def check(r,docs,read):
 """One rule, the spec's attribution.* codes in Bifrost's order; the first failure stops it."""
 h=find(docs,'equipment-hierarchy',r['equipmentRef']);require(h is not None,'attribution.hierarchy-missing')
 paths_=paths(h);known=set(paths_.values());stations=list(r['stations'])
 for s in stations:require(s in known,'attribution.station-unresolved')
 for a in stations:
  for b in stations:require(not b.startswith(a+':'),'attribution.station-nested')
 bundle=members(docs,paths_);rule={};slots=set()
 require(len(r['members'])>0,'attribution.member-unresolved')
 for m in r['members']:
  x=bundle.get(m['mappingId']);metric=m['metric']
  require(x is not None and x['set']==key(m['mappingSetRef']) and x['one'] and x['distinct'] and x['leaf']['name']==metric and x['leaf']['semanticId']==m['semanticId']
          and (x['identifier'] is None or x['identifier'].endswith('.'+metric)) and m['mappingId'] not in rule and (x['path'],metric) not in slots,'attribution.member-unresolved')
  rule[m['mappingId']]=x;slots.add((x['path'],metric))
  require(within(stations,x['path']),'attribution.member-equipment')
 active=set()
 for a in r['activity']:
  x=rule.get(a['memberRef']);p=a['equipmentPath']
  require(x is not None and x['path']==p and within(stations,p) and x['leaf']['valueType']=='Boolean' and p not in active,'attribution.activity-member');active.add(p)
 e=find(docs,'evidence-artifact',r['occupancyBindingRef'])
 require(e is not None and e['schemaVersion']=='1.1.0','attribution.binding-unresolved')
 require(e['id'].startswith(PREFIX) and e['file']['mediaType']==MEDIA,'attribution.binding-profile')
 occupancy_profile(read(e['file']['path']),'attribution.binding-profile')
 # Task 11 inserts the plc-stamped identity checks here (spec 132 roles, 135 coverage and member types).
 t=r['temporal'];require(t['outOfOrdernessMs']<=t['allowedLatenessMs']<=t['horizonMs'],'attribution.temporal-order')
def validate(docs,read):
 """docs: every document in one package; read(path) returns a data file's bytes."""
 docs=list(docs)
 for r in docs:
  if r.get('kind')==KIND:check(r,docs,read)
