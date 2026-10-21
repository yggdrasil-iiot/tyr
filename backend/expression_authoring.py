"""Local expression recipes; existing canonical graphs are the only receiver wire data."""
import copy,json
from pathlib import Path
from jsonschema import Draft202012Validator
import bounded_expression as compiler
import expression_literals
import sample_quality as sq
from publication import require
TABLE='expression_recipes'

def rows(connection):
 if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(TABLE,)).fetchone():return []
 return [json.loads(body) for body, in connection.execute('SELECT body FROM expression_recipes ORDER BY revision DESC,graph_id')]

def listing(store):
 with store.connect() as c:
  c.execute('BEGIN')
  revision,body=c.execute('SELECT revision,body FROM workspace WHERE id=1').fetchone();workspace=json.loads(body);history=rows(c)
 graphs={g['id']:g for g in workspace.get('graphs',[])};out=[];seen=set()
 for recipe in history:
  id=recipe['graphId']
  if id in seen:continue
  seen.add(id);g=graphs.get(id);state='missing-graph' if g is None else 'current'
  if g is not None:
   try:
    if sq.digest(g)!=recipe['compilation']['graphSha256'] or sq.digest(compiler.context(workspace,recipe['compilation']['sourceIds'],g['equipmentInstanceId']))!=recipe['compilation']['sourceContextSha256']:state='stale'
   except (KeyError,ValueError):state='stale'
  out.append(dict(recipe,state=state,history=[h for h in history if h['graphId']==id]))
 return {'workspaceRevision':revision,'recipes':out,'execution':'excluded'}

def prepare(snapshot,request):
 require(set(request) in ({'revision','graphId','equipmentInstanceId','expression'},{'revision','graphId','equipmentInstanceId','expression','compilerVersion'}),'Invalid expression request')
 version=request.get('compilerVersion','1.0.0');require(version in ('1.0.0','1.1.0'),'Unsupported expression compiler')
 require(type(request['revision']) is int and request['revision']>=0,'Invalid expression revision')
 compiled=(expression_literals if version=='1.1.0' else compiler).compile_graph(snapshot['workspace'],request['expression'],request['graphId'],request['equipmentInstanceId'])
 existing=[g for g in snapshot['workspace']['graphs'] if g['id']==request['graphId']]
 if existing:
  require(len(existing)==1 and existing[0]['equipmentInstanceId']==request['equipmentInstanceId'],'Expression equipment change requires new graph ID')
  compiled['graph']['version']=existing[0]['version'];compiled['graphSha256']=sq.digest(compiled['graph'])
 state=copy.deepcopy(snapshot['workspace'])
 existing_ids={s['definition']['id'] for s in state['sources']}
 state['sources'].extend(copy.deepcopy(s) for s in compiled.get('generatedSources',[]) if s['definition']['id'] not in existing_ids)
 state['graphs']=[g for g in state['graphs'] if g['id']!=request['graphId']]+[compiled['graph']]
 return state,compiled

def insert(connection,recipe,state,revision):
 # Lazy additive migration, within the same transaction as workspace CAS.
 graph=next(g for g in state['graphs'] if g['id']==recipe['graphId'])
 require(sq.digest(graph)==recipe['compilation']['graphSha256'],'Expression graph digest mismatch')
 connection.execute('CREATE TABLE IF NOT EXISTS expression_recipes (graph_id TEXT NOT NULL,revision INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(graph_id,revision))')
 require(connection.execute('SELECT COUNT(*) FROM expression_recipes').fetchone()[0]<1000,'At most 1000 expression recipe revisions')
 record=dict(recipe,savedRevision=revision)
 version=recipe['compilation']['compilerVersion'];require(version in ('1.0.0','1.1.0'),'Unsupported recipe compiler')
 schema=json.loads((Path(__file__).resolve().parents[1]/('editor-contracts/'+version+'/expression-recipe.schema.json')).read_text(encoding='utf-8'))
 require(not list(Draft202012Validator(schema).iter_errors(record)),'Invalid expression recipe contract')
 body=json.dumps(record,ensure_ascii=False,allow_nan=False)
 size=len(body.encode('utf-8'));require(size<=524288,'Expression recipe exceeds 512 KiB')
 total=connection.execute('SELECT COALESCE(SUM(length(CAST(body AS BLOB))),0) FROM expression_recipes').fetchone()[0]
 require(total+size<=16*1024*1024,'Expression history exceeds 16 MiB; preserve existing history')
 connection.execute('INSERT INTO expression_recipes VALUES (?,?,?)',(recipe['graphId'],revision,body))

def response(store,request,Conflict,check_state,apply=False):
 snap=store.read()
 require(isinstance(request,dict),'Invalid expression request')
 require(type(request.get('revision')) is int,'Invalid expression revision')
 if request['revision']!=snap['revision']:raise Conflict('작성본이 변경됐습니다. 최신 저장본을 다시 연 뒤 수식을 다시 컴파일하세요.')
 existing=next((g for g in snap['workspace'].get('graphs',[]) if g['id']==request.get('graphId')),None)
 if existing:
  with store.connect() as c:known=any(r['graphId']==existing['id'] for r in rows(c))
  require(known,'Manual graph replacement is forbidden; choose a new graph ID')
 state,compiled=prepare(snap,request)
 require(len(json.dumps(state,ensure_ascii=False,allow_nan=False).encode('utf-8'))<=2*1024*1024,'Expression workspace exceeds 2 MiB')
 check_state(state)
 report={'kind':'expression-compilation','version':1,'revision':snap['revision'],'compilation':compiled,'persisted':False,'execution':'excluded'}
 if apply:
  result=store.save(snap['revision'],state,expression_recipe={'graphId':request['graphId'],'compilation':compiled})
  report.update(persisted=True,saved=result)
 return report
