"""Bounded recursive-descent authoring compiler. Never evaluates user code or values."""
import copy,re,json
from decimal import Decimal
import bounded_arithmetic as arithmetic
import source_views,mixed_sources
import sample_quality as sq
VERSION='1.0.0'
ID=re.compile(r'[a-z][a-z0-9._-]{0,127}')
NUMBER=re.compile(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?')
NUMERIC=mixed_sources.NUMERIC
class ExpressionError(ValueError):
 def __init__(self,code,position):self.code=code;self.position=position;super().__init__(code+' @'+str(position))
class Parser:
 def __init__(self,text):
  if not isinstance(text,str) or not 1<=len(text)<=4096:raise ExpressionError('expression.length',0)
  self.text=text;self.tokens=[];p=0
  while p<len(text):
   if text[p].isspace():p+=1;continue
   start=p;c=text[p]
   if c=='[':
    end=text.find(']',p+1)
    if end<0 or not ID.fullmatch(text[p+1:end]):raise ExpressionError('expression.source-syntax',p)
    self.tokens.append(('source',text[p+1:end],p,end+1));p=end+1
   elif c=='"' and getattr(self,'allow_literals',False):
    end=text.find('"',p+1)
    if end<0:raise ExpressionError('expression.unit-string',p)
    self.tokens.append(('unit',text[p+1:end],p,end+1));p=end+1
   elif c in '+-*/(),':self.tokens.append((c,c,p,p+1));p+=1
   elif c.isascii() and c.isdigit():
    m=NUMBER.match(text,p);self.tokens.append(('number',m.group(),p,m.end()));p=m.end()
   elif c.isascii() and c.isalpha():
    m=re.match('[a-z]+',text[p:])
    if not m:raise ExpressionError('expression.token',p)
    word=m.group();self.tokens.append(('function',word,p,p+len(word)));p+=len(word)
   else:raise ExpressionError('expression.token',p)
   if len(self.tokens)>512:raise ExpressionError('expression.token-limit',start)
  self.tokens.append(('end','',len(text),len(text)));self.i=0;self.operations=0
 def peek(self):return self.tokens[self.i]
 def take(self,kind):
  t=self.peek()
  if t[0]!=kind:raise ExpressionError('expression.expected-'+kind,t[2])
  self.i+=1;return t
 def operation(self,op,args,start,end,**extra):
  self.operations+=1
  if self.operations>64:raise ExpressionError('expression.node-limit',start)
  return dict(op=op,args=args,start=start,end=end,**extra)
 def expression(self,depth=0):
  left=self.term(depth)
  while self.peek()[0] in ('+','-'):
   op=self.peek()[0];self.i+=1;right=self.term(depth);left=self.operation('add' if op=='+' else 'subtract',[left,right],left['start'],right['end'])
  return left
 def term(self,depth):
  left=self.primary(depth)
  while self.peek()[0] in ('*','/'):
   op=self.peek()[0];self.i+=1;right=self.primary(depth);left=self.operation('multiply' if op=='*' else 'divide',[left,right],left['start'],right['end'])
  return left
 def decimal(self):
  sign=''
  if self.peek()[0]=='-':self.take('-');sign='-'
  t=self.take('number');value=sign+t[1]
  if len(value)>64:raise ExpressionError('expression.decimal-limit',t[2])
  return value
 def primary(self,depth):
  if depth>32:raise ExpressionError('expression.depth',self.peek()[2])
  t=self.peek()
  if t[0]=='source':self.i+=1;return dict(op='source',id=t[1],start=t[2],end=t[3])
  if t[0]=='(':
   self.i+=1;n=self.expression(depth+1);end=self.take(')')[3];return dict(n,start=t[2],end=end)
  if t[0]=='function':
   self.i+=1;name=t[1]
   if name not in ('sqrt','clamp','linear'):raise ExpressionError('expression.function',t[2])
   self.take('(');arg=self.expression(depth+1);extra={}
   if name in ('clamp','linear'):
    self.take(',');one=self.decimal();self.take(',');two=self.decimal();extra=dict(zip(('low','high') if name=='clamp' else ('factor','offset'),(one,two)))
   end=self.take(')')[3];return self.operation(name,[arg],t[2],end,**extra)
  raise ExpressionError('expression.value',t[2])
 def parse(self):
  node=self.expression();self.take('end');return node

def context(workspace,source_ids,equipment):
 definitions=[s['definition'] for s in workspace['sources']];by_id={}
 for s in definitions:by_id.setdefault(s['id'],[]).append(s)
 selected={};pending=list(source_ids)
 while pending:
  id=pending.pop()
  if id in selected:continue
  found=by_id.get(id,[])
  if len(found)!=1:raise ExpressionError('expression.source-missing-or-ambiguous',0)
  s=found[0];selected[id]=s
  if s.get('viewOf'):
   parent=s['viewOf'];matches=[d for d in definitions if d['id']==parent['id'] and d['version']==parent['version']]
   if len(matches)!=1:raise ExpressionError('expression.source-parent',0)
   pending.append(parent['id'])
  if len(selected)>128:raise ExpressionError('expression.source-limit',0)
 equipment_rows=[e for e in workspace['equipment'] if e['id']==equipment]
 if len(equipment_rows)!=1:raise ExpressionError('expression.equipment',0)
 connections={s.get('connectionProfileRef') for s in selected.values()}
 return {'sources':[copy.deepcopy(s) for k,s in sorted(selected.items())],'equipment':copy.deepcopy(equipment_rows[0]),'connections':[copy.deepcopy(c) for c in sorted(workspace['connections'],key=lambda x:x['id']) if c['id'] in connections]}

def compile_graph(workspace,text,graph_id,equipment,_ast=None):
 if workspace.get('workspaceVersion')!='2.0.0':raise ExpressionError('expression.workspace-version',0)
 if not isinstance(graph_id,str) or not ID.fullmatch(graph_id):raise ExpressionError('expression.graph-id',0)
 ast=Parser(text).parse() if _ast is None else _ast;nodes=[];origins=[];source_ids=set();definitions=[s['definition'] for s in workspace['sources']];index=source_views.index(definitions)
 def fail(code,n):raise ExpressionError(code,n['start'])
 def emit(n):
  op=n['op']
  if op=='source':
   found=[s for s in definitions if s['id']==n['id']]
   if len(found)!=1:fail('expression.source-missing-or-ambiguous',n)
   s=found[0];source_ids.add(s['id'])
   if s['equipmentInstanceId']!=equipment:fail('value.equipment',n)
   if s['status']!='ready' or mixed_sources.mode(s)=='write':fail('expression.source-not-readable',n)
   typ=source_views.value_type(s,index)
   if typ not in NUMERIC or 'fixedArray' in s:fail('graph.input-type',n)
   if s['unit']['status']!='known':fail('graph.input-unit',n)
   closure=context(workspace,[s['id']],equipment)
   if any(d['status']!='ready' or mixed_sources.mode(d)=='write' or d['equipmentInstanceId']!=equipment for d in closure['sources']):fail('expression.source-not-readable',n)
   for d in closure['sources']:
    problems=source_views.rules(d,index)
    if problems:fail(problems[0],n)
   refs=unique([e for d in closure['sources'] for e in d['evidenceRefs']])
   if not refs:fail('expression.evidence',n)
   return {'kind':'source','sourceRef':{'id':s['id'],'version':s['version']}},typ,s['unit'],refs,s['inputStage']
  args=[emit(a) for a in n['args']];unit=args[0][2];refs=unique([ref for a in args for ref in a[3]])
  if op in arithmetic.OPS:
   try:unit=arithmetic.unit_for(op,args[0][2],args[1][2])
   except ValueError as e:fail(str(e),n)
  elif op=='subtract':
   if args[1][2]!=unit or unit.get('code') not in ('Pa','kPa','bar','1'):fail('graph.input-unit',n)
  elif op=='sqrt' and unit!={'status':'known','code':'1'}:fail('graph.input-unit',n)
  elif op=='clamp' and Decimal(n['low'])>Decimal(n['high']):fail('graph.clamp-range',n)
  elif op=='linear' and args[0][4]=='already-engineered' and (Decimal(n['factor'])!=1 or Decimal(n['offset'])!=0):fail('mapping.double-transform',n)
  inputs=dict(zip(('left','right') if len(args)==2 else ('value',),(a[0] for a in args)))
  node={'nodeId':'expr-'+str(len(nodes)+1).zfill(3),'op':op,'inputs':inputs,'valueType':'Decimal','unit':copy.deepcopy(unit),'evidenceRefs':refs}
  if op in ('sqrt','divide'):node.update(precision=34,rounding='half-even')
  for k in ('low','high','factor','offset'):
   if k in n:node[k]=n[k]
  nodes.append(node);origins.append({'nodeId':node['nodeId'],'op':op,'start':n['start'],'end':n['end']})
  return {'kind':'node','nodeId':node['nodeId']},'Decimal',unit,refs,'derived'
 endpoint,typ,unit,refs,stage=emit(ast)
 if not nodes:
  nodes.append({'nodeId':'expr-result','op':'identity','inputs':{'value':endpoint},'valueType':typ,'unit':copy.deepcopy(unit),'evidenceRefs':refs});origins.append({'nodeId':'expr-result','op':'identity','start':ast['start'],'end':ast['end']})
 else:nodes[-1]['nodeId']='expr-result';origins[-1]['nodeId']='expr-result'
 graph={'kind':'value-graph','schemaVersion':'2.15.0','id':graph_id,'version':'1.0.0','equipmentInstanceId':equipment,'nodes':nodes}
 if len(json.dumps(graph,ensure_ascii=False,separators=(',',':')).encode())>262144:raise ExpressionError('expression.graph-size',0)
 source_context=context(workspace,source_ids,equipment)
 return {'compilerVersion':VERSION,'expression':text,'graph':graph,'graphSha256':sq.digest(graph),'sourceContextSha256':sq.digest(source_context),'sourceIds':sorted(source_ids),'origins':origins,'output':{'nodeId':'expr-result','valueType':typ,'unit':copy.deepcopy(unit)}}

def unique(refs):
 out={sq.digest(e):copy.deepcopy(e) for e in refs}
 if len(out)>256:raise ExpressionError('expression.evidence-limit',0)
 return [out[k] for k in sorted(out)]
