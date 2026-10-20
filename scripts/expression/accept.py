"""Arithmetic authoring/SQLite/virtual preview/independent signed file publication, offline."""
import copy,hashlib,json,os,shutil,sqlite3,subprocess,sys,tarfile,tempfile,threading,traceback,base64,io,zipfile
from pathlib import Path
E=Path('/work/evidence');E.mkdir(parents=True,exist_ok=True);R=Path('/work/tyr');report={'passed':False,'checks':[],'fieldPoV':'not-performed','deviceCommunication':'excluded','externalSQL':'excluded','writeExecution':'excluded'}
def save():(E/'expression-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def check(id,ok,**details):
 print(id,bool(ok),flush=True);report['checks'].append(dict(id=id,passed=bool(ok),**details));save();assert ok,(id,details)
def java(*args):
 p=subprocess.run(['java','-jar',str(JAR),*map(str,args)],capture_output=True,text=True,timeout=120);assert p.returncode in (0,1),p.stderr
 v=json.loads(p.stdout);(E/('java-%02d.json'%len(list(E.glob('java-*.json'))))).write_text(json.dumps(v,indent=2));return v

def main():
 with tarfile.open('/input/package.tar') as t:t.extractall('/work',filter='data')
 os.chdir(R);sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
 report['inputSha256']={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for n in ['scripts','backend','frontend','contracts','evaluation-contracts','editor-contracts','fixtures'] for p in (R/n).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 global JAR;JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar';report['jarSha256']=hashlib.sha256(JAR.read_bytes()).hexdigest();save()
 import server
 from playwright.sync_api import sync_playwright,expect
 registry=E/'registry';store=server.Store(E/'editor.sqlite3');store.migrate(0,{});w=server.contracts.load(R/'fixtures/p3cc/workspace.json');store.save(1,w)
 http=server.make_server(store,0,JAR,registry);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();origin='http://127.0.0.1:'+str(http.server_port);errors=[];requests=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1400,'height':1050});page.set_default_timeout(90000)
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda req:requests.append(req.url));page.on('dialog',lambda d:d.accept() if d.type=='beforeunload' else d.dismiss())
  page.goto(origin);page.locator('#counts strong').first.wait_for();check('browser.localhost-loaded',True)
  page.locator('[data-tab="expressions"]').click();page.locator('#expression-id').fill('formula-ui');page.locator('#expression-equipment').select_option('line-a-motor-ab');page.locator('#expression-text').fill('[structure-ab-actual] * [structure-ab-target]')
  snapshot=store.read()
  with page.expect_response(lambda r:r.url.endswith('/api/expression-compile')) as bad:page.locator('#expression-form button[type="submit"]').click()
  check('expression.dimension-product-refused',bad.value.status==422 and store.read()==snapshot and page.locator('#expression-apply').is_disabled())
  formula='([structure-ab-actual] - [structure-ab-target]) / [arithmetic-ab-gain]';page.locator('#expression-text').fill(formula)
  store.save(snapshot['revision'],snapshot['workspace'])
  with page.expect_response(lambda r:r.url.endswith('/api/expression-compile')) as stale_formula:page.locator('#expression-form button[type="submit"]').click()
  check('expression.stale-authoring-requires-reload',stale_formula.value.status==409 and page.locator('#expression-apply').is_disabled())
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="expressions"]').click();page.locator('#expression-id').fill('formula-ui');page.locator('#expression-equipment').select_option('line-a-motor-ab');page.locator('#expression-text').fill(formula);snapshot=store.read()
  with page.expect_response(lambda r:r.url.endswith('/api/expression-compile')) as co:page.locator('#expression-form button[type="submit"]').click()
  c=co.value.json()['compilation'];check('expression.compile-to-existing-wire-readonly',co.value.status==200 and c['graph']['schemaVersion']=='2.15.0' and [n['op'] for n in c['graph']['nodes']]==['subtract','divide'] and store.read()==snapshot and c['expression'][c['origins'][-1]['start']:c['origins'][-1]['end']]==formula)
  with page.expect_response(lambda r:r.url.endswith('/api/expression-apply')) as applied:page.locator('#expression-apply').click()
  check('expression.browser-atomic-save',applied.value.json()['persisted'] and server.Store(store.path).read()==store.read())
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="expressions"]').click();expect(page.locator('#expression-records')).to_contain_text(formula);check('expression.browser-reopen-raw-text',True)
  snap=store.read();next_state=copy.deepcopy(snap['workspace']);next(g for g in next_state['graphs'] if g['id']=='formula-ui')['nodes'][0]['op']='add';store.save(snap['revision'],next_state)
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="expressions"]').click();expect(page.locator('#expression-records')).to_contain_text('stale');check('expression.manual-graph-edit-visible-stale',True)
  page.locator('[data-expression-edit="formula-ui"]').click()
  with page.expect_response(lambda r:r.url.endswith('/api/expression-compile')) as co:page.locator('#expression-form button[type="submit"]').click()
  with page.expect_response(lambda r:r.url.endswith('/api/expression-apply')) as applied:page.locator('#expression-apply').click()
  recipes=server.expression_authoring.listing(store)['recipes'];check('expression.explicit-recompile-preserves-history',recipes[0]['state']=='current' and len(recipes[0]['history'])==2)
  page.locator('#expression-summary').scroll_into_view_if_needed();page.screenshot(path=str(E/'expression-preview.png'))
  arith_base=store.read()['revision']
  page.locator('[data-tab="graphs"]').click();page.locator('[data-edit="graph"][data-id="arithmetic-ab"]').click()
  check('browser.new-operations-visible',all(page.locator('#node-op-0 option[value="'+op+'"]').count()==1 for op in ['add','multiply','divide']))
  before=store.read();page.locator('#node-right-1').select_option('s:structure-ab-target')
  with page.expect_response(lambda r:r.url==origin+'/api/workspace' and r.request.method=='PUT') as bad:page.locator('#graph-form button[type="submit"]').click()
  check('browser.dimension-product-refused',bad.value.status==422 and store.read()==before)
  page.locator('#node-op-1').select_option('divide');page.locator('#node-left-1').select_option('n:sum');page.locator('#node-right-1').select_option('s:arithmetic-ab-gain');page.locator('#node-unit-1').select_option('kPa')
  with page.expect_response(lambda r:r.url==origin+'/api/workspace' and r.request.method=='PUT') as saved:page.locator('#graph-form button[type="submit"]').click()
  check('browser.division-author-save',saved.value.status==200)
  page.locator('#revision').filter(has_text='저장 revision '+str(arith_base+1)).wait_for();g=next(g for g in store.read()['workspace']['graphs'] if g['id']=='arithmetic-ab')
  check('sqlite.contract-policy-roundtrip',g['schemaVersion']=='2.15.0' and g['nodes'][1]['precision']==34 and g['nodes'][1]['rounding']=='half-even' and server.Store(store.path).read()==store.read())
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="graphs"]').click();page.locator('[data-edit="graph"][data-id="arithmetic-ab"]').click();check('browser.reload-node-ports',page.locator('#node-op-1').input_value()=='divide' and page.locator('#node-right-1').input_value()=='s:arithmetic-ab-gain')
  page.locator('[data-tab="preview"]').click();page.locator('#preview-binding').select_option(json.dumps(['arithmetic-mapping-ab','ab-quotient'],separators=(',',':')))
  def fill(id,value):page.locator('.sample-input[data-source="'+id+'"] input[id^="virtual-"]').fill(value)
  for id,value in [('structure-ab-actual','150'),('structure-ab-target','50'),('arithmetic-ab-gain','2')]:fill(id,value)
  snapshot=store.read()
  with page.expect_response(lambda r:r.url.endswith('/api/preview')) as pr:page.locator('#preview-form button[type="submit"]').click()
  v=pr.value.json();stages=[t['stage'] for t in v['trace']];check('browser.multi-input-arithmetic-trace',v['result']['value']=='50' and stages.count('graph:divide')==2 and stages.index('graph:add')<stages.index('graph:divide')<stages.index('transform:cast'),preview=v)
  check('sqlite.preview-readonly',store.read()==snapshot)
  fill('arithmetic-ab-gain','0')
  with page.expect_response(lambda r:r.url.endswith('/api/preview')) as pr:page.locator('#preview-form button[type="submit"]').click()
  v=pr.value.json();check('browser.zero-denominator-visible',v['result'] is None and v['quality']=='bad' and 'value.divide-zero' in {i['code'] for i in v['issues']})
  page.locator('#preview-binding').select_option(json.dumps(['arithmetic-mapping-ab','ab-ratio'],separators=(',',':')));fill('structure-ab-actual','1');fill('structure-ab-target','3')
  with page.expect_response(lambda r:r.url.endswith('/api/preview')) as pr:page.locator('#preview-form button[type="submit"]').click()
  v=pr.value.json();check('browser.division-and-final-cast-loss',len(v['losses'])==2 and v['quality']=='uncertain' and next(t for t in v['trace'] if t['stage']=='graph:divide')['value']=='0.3333333333333333333333333333333333',preview=v)
  expect(page.locator('#preview-result')).to_contain_text('loss.precision');check('browser.loss-detail-readable','[object Object]' not in page.locator('#preview-result').inner_text())
  page.locator('#preview-result').scroll_into_view_if_needed();page.screenshot(path=str(E/'arithmetic-regression.png'))
  stale=page.request.post(origin+'/api/preview',data=json.dumps({'revision':2,'mappingSetId':'arithmetic-mapping-ab','mappingId':'ab-ratio','samples':{}}),headers={'Content-Type':'application/json','X-Tyr-Editor':'1'});check('http.stale-revision-refused',stale.status==409)
  # Compile the remaining equipment profiles through HTTP; no fixture bypass or Java/Python shared code.
  cases=server.contracts.load(R/'fixtures/expression/cases.json')['profiles']
  for profile in ['ua','db','melsec']:
   case=cases[profile];q={'revision':store.read()['revision'],'graphId':case['graphId'],'equipmentInstanceId':case['equipmentInstanceId'],'expression':case['expression']}
   response=page.request.post(origin+'/api/expression-apply',data=json.dumps(q),headers={'Content-Type':'application/json','X-Tyr-Editor':'1'});assert response.status==200,response.text()
  snap=store.read();next_state=copy.deepcopy(snap['workspace'])
  for profile in ['ab','ua','db','melsec']:
   b=next(b for m in next_state['mappings'] if m['id']=='arithmetic-mapping-'+profile for b in m['mappings'] if b['mappingId']==profile+'-quotient');b['valueRef']={'kind':'graph','graphRef':{'id':'formula-ui' if profile=='ab' else 'formula-'+profile,'version':'1.0.0'},'nodeId':'expr-result'}
  store.save(snap['revision'],next_state);check('expression.four-profile-graphs-mapped',len(server.expression_authoring.listing(store)['recipes'])==4)
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="preview"]').click();page.locator('#preview-binding').select_option(json.dumps(['arithmetic-mapping-ab','ab-quotient'],separators=(',',':')))
  for id,value in [('structure-ab-actual','150'),('structure-ab-target','50'),('arithmetic-ab-gain','2')]:fill(id,value)
  with page.expect_response(lambda r:r.url.endswith('/api/preview')) as pr:page.locator('#preview-form button[type="submit"]').click()
  pv=pr.value.json();check('expression.existing-step-preview-and-cast',pv['result']['value']=='50' and 'graph:subtract' in [t['stage'] for t in pv['trace']] and 'graph:divide' in [t['stage'] for t in pv['trace']],preview=pv)
  page.locator('[data-tab="publication"]').click();page.locator('#submission-id').fill('p3cc-ui');page.locator('#submission-stream').fill('p3cc-offline');page.locator('#submission-by').fill('proposer');page.locator('#submission-mapping').select_option([m['id'] for m in w['mappings']])
  with page.expect_response(lambda r:r.url.endswith('/api/submissions') and r.request.method=='POST') as ex:page.locator('#submission-form button[type="submit"]').click()
  record=ex.value.json();check('browser.export-all-four-profile-closure',ex.value.status==200 and record['preflightFindings']==[],record=record);bundle=Path(record['path']);check('java.independent-validation',java('mapping','validate',bundle)['accepted'])
  forged=E/'forged-expression-bundle';shutil.copytree(bundle,forged);proposal=json.loads((forged/'proposal.json').read_text());entry=next(x for x in proposal['files'] if x['kind']=='value-graph' and x['id']=='formula-ui');target=forged/entry['path'];g=json.loads(target.read_text());g['nodes'][-1]['unit']['code']='bar';target.write_text(json.dumps(g));entry['sha256']=hashlib.sha256(target.read_bytes()).hexdigest();(forged/'proposal.json').write_text(json.dumps(proposal));submission=json.loads((forged/'submission.json').read_text());submission['proposalSha256']=hashlib.sha256((forged/'proposal.json').read_bytes()).hexdigest();(forged/'submission.json').write_text(json.dumps(submission));refusal=java('mapping','validate',forged)
  check('expression.independent-receiver-refuses-forged-output-unit',not refusal['accepted'] and 'graph.output-unit' in json.dumps(refusal['findings']))
  with tempfile.TemporaryDirectory(prefix='p3cc-keys-') as kd:
   keys=Path(kd);identity=registry/'identity';identity.mkdir(parents=True,exist_ok=True);public=[java('identity','keygen',who,'--out',keys) for who in ['proposer','approver']];(identity/'authorized-keys.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in public))
   policy={'version':'1.0.0','default':'deny','rules':[{'id':'p3cc-'+action,'principal':who,'action':action,'target':'mapping-publication','kind':'mapping-release','ref':'p3cc-offline'} for action,who in [('publish','proposer'),('approve','approver')]]};(identity/'activation-policy.json').write_text(json.dumps(policy))
   approved=java('mapping','approve',registry,bundle,'p3cc-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key');check('java.two-key-approval',approved.get('kind')=='mapping-approval')
   release=java('mapping','publish',registry,bundle,'p3cc-release','1.0.0','--approval','p3cc-approval');check('java.publish-without-activation',release.get('kind')=='mapping-release' and release['activation']=='not-performed')
  with page.expect_response(lambda r:r.url.endswith('/api/submission-refresh')) as rr:page.locator('[data-submission-refresh="p3cc-ui"]').click()
  check('browser.published-status',rr.value.json()['publicationState']=='published')
  before_catalog=store.read()
  with page.expect_response(lambda r:r.url.endswith('/api/semantic-catalog')) as ca:page.locator('#catalog-preview').click()
  cat=ca.value.json();check('catalog.browser-registered-meaning',ca.value.status==200 and {e['status'] for e in cat['entries']}=={'compatible'},catalog=cat)
  check('catalog.readonly-sqlite',store.read()==before_catalog)
  expect(page.locator('#catalog-summary')).to_contain_text('계약 일치')
  page.locator('#catalog-preview').scroll_into_view_if_needed();page.screenshot(path=str(E/'catalog-preview.png'))
  second_state=copy.deepcopy(store.read()['workspace']);second_state['semantics'][0]['members'][0]['role']='setpoint'
  second_bundle=E/'conflicting-bundle'
  server.publication.build(second_state,second_bundle,'conflict-submission','second-line','proposer',None,[m['id'] for m in second_state['mappings']],False,server.build_package)
  check('catalog.bundle-individually-valid',java('mapping','validate',second_bundle)['accepted'])
  # Compare conflicting authoring state without modifying immutable submissions.
  store.save(before_catalog['revision'],second_state);page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="publication"]').click()
  with page.expect_response(lambda r:r.url.endswith('/api/semantic-catalog')) as cc:page.locator('#catalog-preview').click()
  conflict=cc.value.json();check('catalog.browser-cross-stream-conflict-visible',any(e['status']=='registry-conflict' for e in conflict['entries']),catalog=conflict)
  expect(page.locator('#catalog-summary')).to_contain_text('보존 릴리스와 충돌')
  # Registered historical signatures and payload pins must be verified, not silently skipped.
  history=registry/'mappings/releases/p3cc-release/1.0.0/payload/semantics/0.json';raw=history.read_bytes();history.write_bytes(b'{}')
  with page.expect_response(lambda r:r.url.endswith('/api/semantic-catalog')) as fail:page.locator('#catalog-preview').click()
  check('catalog.corrupt-history-refused',fail.value.status==422 and 'error' in fail.value.json())
  expect(page.locator('#catalog-summary')).to_contain_text('조회 실패');history.write_bytes(raw)
  check('catalog.restored-history-reverified',java('mapping','catalog',registry).get('compatible') is True)
  store.save(store.read()['revision'],before_catalog['workspace']);page.reload();page.locator('#counts strong').first.wait_for()
  downloaded=page.request.post(origin+'/api/submission-download',data=json.dumps({'id':'p3cc-ui'}),headers={'Content-Type':'application/json','X-Tyr-Editor':'1'}).json();pins=server.publication.file_pins(bundle)
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(downloaded['bytesBase64']))) as z:check('http.download-all-file-pins',set(z.namelist())==set(pins) and all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in pins.items()))
  page.locator('[data-tab="pov"]').click();page.locator('#pov-scope').select_option([m['id'] for m in w['mappings']])
  with page.expect_response(lambda r:r.url.endswith('/api/pov-template')) as po:page.locator('#pov-template').click()
  check('browser.p7-evaluation-new-graph-compatible',len(po.value.json()['pack']['cases'])==16 and all(c['expected'] is None for c in po.value.json()['pack']['cases']))
  check('browser.no-errors-or-outbound',not errors and all(u.startswith(origin) for u in requests),errors=errors);browser.close()
 http.shutdown();http.server_close();thread.join()
 shutil.copyfile('/input/seed.sqlite3',E/'legacy.sqlite3')
 with sqlite3.connect(E/'legacy.sqlite3') as c:old=list(c.iterdump())
 server.Store(E/'legacy.sqlite3')
 with sqlite3.connect(E/'legacy.sqlite3') as c:check('sqlite.existing-db-open-preserves-rows',old==list(c.iterdump()))
 suites=[('test_expression.py',[],'expression-tests'),('test_semantic_catalog.py',[],'catalog-tests'),('test_p3cc.py',[],'arithmetic-tests'),('test_p7_evaluation.py',[],'evaluation-regression'),('test_p6_recovery.py',[],'recovery-regression'),('test_p4ab.py',[],'import-regression'),('test_p3fb.py',[],'graph-regression'),('test_p3eb.py',[],'structure-regression'),('test_p3cb.py',[],'math-regression'),('test_a07.py',['--report',str(E/'a07.json')],'a07'),('test_p7.py',['--report',str(E/'regression.json')],'baseline')]
 if os.environ.get('TYR_EXPRESSION_UI_ONLY')=='1':suites=[]
 report['regressionScope']='full' if suites else 'separate-full-run'
 for file,args,name in suites:
  proc=subprocess.run([sys.executable,'-B',str(R/'scripts'/file),*args],capture_output=True,text=True,timeout=1200);(E/(name+'.log')).write_text(proc.stdout+proc.stderr);check('tests.'+name,proc.returncode==0)
 report['passed']=True;save()
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();save();raise
 finally:
  with tarfile.open('/evidence/runtime-evidence.tar','w') as t:t.add(E,arcname='.')
