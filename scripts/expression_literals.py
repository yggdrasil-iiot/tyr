"""Opt-in 1.1 authoring literals lowered to unchanged constant/graph wire contracts."""
import copy
from datetime import datetime,timezone
from decimal import Decimal
import bounded_expression as old
import sample_quality as sq
VERSION='1.1.0'
UNITS={'1','Pa','kPa','bar','rpm','1/s','N.m','mN.m','Cel','K'}
class Parser(old.Parser):
 allow_literals=True
 def primary(self,depth):
  t=self.peek()
  if depth>32:raise old.ExpressionError('expression.depth',t[2])
  if t[0] in ('number','-','+'):
   start=t[2];sign=''
   if t[0] in ('-','+'):sign=t[1];self.i+=1
   n=self.take('number');value=sign+n[1]
   if len(value)>64:raise old.ExpressionError('expression.decimal-limit',start)
   return dict(op='literal',value=value,unit='1',start=start,end=n[3])
  if t[0]=='function' and t[1]=='quantity':
   self.i+=1;self.take('(');n=self.primary(depth+1)
   if n['op']!='literal' or n['unit']!='1':raise old.ExpressionError('expression.quantity-number',t[2])
   self.take(',');u=self.take('unit');end=self.take(')')[3]
   if u[1] not in UNITS:raise old.ExpressionError('expression.quantity-unit',u[2])
   return dict(n,unit=u[1],start=t[2],end=end)
  return super().primary(depth)

def canonical(value):
 # No Decimal.normalize(): ambient precision must not round long literals.
 v=format(Decimal(value),'f')
 if '.' in v:v=v.rstrip('0').rstrip('.')
 return '0' if Decimal(v)==0 else v

def compile_graph(workspace,text,graph_id,equipment):
 ast=Parser(text).parse();state=copy.deepcopy(workspace);generated={};origins=[]
 def lower(n):
  if n['op']!='literal':return dict(n,args=[lower(x) for x in n.get('args',[])]) if 'args' in n else n
  value=canonical(n['value']);unit=n['unit'];identity={'compiler':VERSION,'graphId':graph_id,'equipmentInstanceId':equipment,'value':value,'unit':unit}
  id='exprlit-'+sq.digest(identity)[:40]
  definition={'kind':'source-definition','schemaVersion':'2.7.0','id':id,'version':'1.0.0','sourceKind':'constant','accessMode':'read','equipmentInstanceId':equipment,'connectionProfileRef':None,'accessProfileRef':'constant-v1','status':'ready','rawAddressText':'constant:'+id,'addressRadix':None,'access':{'kind':'constant','value':value},'rawRepresentation':{'mode':'typed','valueType':'Double'},'inputStage':'already-engineered','unit':{'status':'known','code':unit},'evidenceRefs':[{'artifactId':'manual-'+id,'locator':{'kind':'text-line','line':1}}],'viewOf':None}
  row={'definition':definition,'label':'Expression literal '+value+' '+unit,'note':'Authored constant; graph '+str(graph_id)+'; compiler '+VERSION+'; value '+value+'; unit '+unit+'. Synthetic declaration, not a device observation. Decimal preview of the declared string; no native IEEE storage guarantee.','origin':'synthetic'}
  found=[s for s in state['sources'] if s['definition']['id']==id]
  if found:
   if len(found)!=1 or {k:v for k,v in found[0].items() if k!='capturedAt'}!=row:raise old.ExpressionError('expression.literal-collision',n['start'])
   row=copy.deepcopy(found[0])
  else:
   row['capturedAt']=datetime.now(timezone.utc).isoformat().replace('+00:00','Z');state['sources'].append(row)
  generated[id]=row;origins.append({'sourceId':id,'start':n['start'],'end':n['end'],'value':value,'unit':unit})
  if len(origins)>128:raise old.ExpressionError('expression.literal-limit',n['start'])
  return {'op':'source','id':id,'start':n['start'],'end':n['end']}
 lowered=lower(ast);compiled=old.compile_graph(state,text,graph_id,equipment,_ast=lowered)
 compiled.update(compilerVersion=VERSION,generatedSources=[generated[k] for k in sorted(generated)],literalOrigins=origins)
 return compiled
