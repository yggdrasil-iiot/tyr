"""Network-none operator browser + Python + independent Java acceptance."""
import copy,hashlib,json,os,sqlite3,subprocess,sys,tarfile,tempfile,threading,traceback
from pathlib import Path
E=Path('/work/evidence');E.mkdir(parents=True,exist_ok=True);R=Path('/work/tyr');report={'passed':False,'checks':[],'fieldPoV':'not-performed','deviceCommunication':'excluded','externalSQL':'excluded','writeExecution':'excluded'}
def save():(E/'record-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def check(id,ok,**details):
 print(id,bool(ok),flush=True);report['checks'].append(dict(id=id,passed=bool(ok),**details));save();assert ok,(id,details)
def java(*args):
 p=subprocess.run(['java','-jar',str(JAR),*map(str,args)],capture_output=True,text=True,timeout=120);assert p.returncode in (0,1),p.stderr
 v=json.loads(p.stdout);(E/('java-%02d.json'%len(list(E.glob('java-*.json'))))).write_text(json.dumps(v,indent=2));return v
SUITES=[('test_record_mappings.py',[],'records'),('test_mapping_templates.py',[],'templates'),('test_semantic_lifecycle.py',[],'lifecycle'),('test_cross_graph.py',[],'reuse'),('test_expression_literals.py',[],'literals'),('test_expression.py',[],'expression'),('test_semantic_catalog.py',[],'catalog'),('test_p3cc.py',[],'arithmetic'),('test_p7_evaluation.py',[],'evaluation'),('test_p6_recovery.py',[],'recovery'),('test_p4ab.py',[],'import'),('test_p3fb.py',[],'graph'),('test_p3eb.py',[],'structure'),('test_p3cb.py',[],'math'),('test_a07.py',['--report',str(E/'a07.json')],'a07'),('test_p7.py',['--report',str(E/'regression.json')],'baseline')]

def main():
 with tarfile.open('/input/package.tar') as t:t.extractall('/work',filter='data')
 os.chdir(R);sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
 global JAR,page;JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar';report['jarSha256']=hashlib.sha256(JAR.read_bytes()).hexdigest();save()
 check('input.driver-matches-archive',Path('/input/accept.py').read_bytes()==(R/'scripts/record-mappings/accept.py').read_bytes())
 if os.environ.get('TYR_CROSS_PYTHON_ONLY')=='1':
  report['scope']='python-full'
  for file,args,name in SUITES:
   p=subprocess.run([sys.executable,'-B',str(R/'scripts'/file),*args],capture_output=True,text=True,timeout=1200);(E/(name+'.log')).write_text(p.stdout+p.stderr);check('tests.'+name,p.returncode==0)
  report['passed']=True;save();return
 import server,record_mappings as rm,record_authoring as ra
 from playwright.sync_api import sync_playwright,expect
 registry=E/'registry';store=server.Store(E/'editor.sqlite3');store.migrate(0,{});store.save(1,server.contracts.load(R/'fixtures/record-mappings/workspace.json'))
 with sqlite3.connect('file:/input/seed.sqlite3?mode=ro',uri=True) as src,sqlite3.connect(E/'legacy.sqlite3') as dst:src.backup(dst)
 legacy=server.Store(E/'legacy.sqlite3')
 with legacy.connect() as db:old=list(db.iterdump())
 legacy.read();ra.listing(legacy)
 with legacy.connect() as db:check('sqlite.legacy-read-no-DDL-or-mutation',old==list(db.iterdump()))
 http=server.make_server(store,0,JAR,registry);th=threading.Thread(target=http.serve_forever,daemon=True);th.start();origin='http://127.0.0.1:'+str(http.server_port);errors=[];requests=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(60000);page.on('pageerror',lambda e:(errors.append(str(e)),print('JS_ERROR',str(e),flush=True)));page.on('request',lambda r:requests.append(r.url));page.on('dialog',lambda d:d.accept() if d.type in ('beforeunload','confirm') else d.dismiss());page.goto(origin);page.locator('#counts strong').first.wait_for();page.locator('[data-tab="records"]').click();page.wait_for_timeout(1000);print('RECORDS_MESSAGE',page.locator('#message').inner_text(),flush=True);page.locator('[data-record-revision="2"]').wait_for()
  check('browser.record-template-pins-and-two-equipment-visible',page.locator('[data-rec-edit]').count()==2 and 'record-line-b' in page.locator('#rec-saved').inner_text())
  # Restore existing recipe into a new explicit immutable version through operator controls.
  page.locator('[data-rec-edit="0"]').click();page.locator('#rec-reason').fill('Offline operator revision');page.locator('#rec-version').fill('1.0.1')
  before=store.read()
  with page.expect_response(lambda r:r.url.endswith('/api/record-compose')) as rr:page.locator('#record-author button[type="submit"]').click()
  plan=rr.value.json();check('browser.compose-pinned-recipe-readonly',rr.value.status==200 and plan['valid'] and store.read()==before and plan['draft']['record']['templateRef']==before['workspace']['recordMappings'][0]['templateRef'])
  page.locator('#rec-label').fill('Reviewed pressure records');check('browser.changed-form-invalidates-plan',page.locator('#rec-save').is_disabled())
  with page.expect_response(lambda r:r.url.endswith('/api/record-compose')) as rr:page.locator('#record-author button[type="submit"]').click()
  plan=rr.value.json()
  headers={'Content-Type':'application/json','X-Tyr-Editor':'1'}
  bad=page.request.post(origin+'/api/record-apply',data=json.dumps(dict(revision=2,draft=plan['draft'],planSha256='0'*64)),headers=headers);check('http.tampered-plan-no-mutation',bad.status==422 and store.read()==before)
  with page.expect_response(lambda r:r.url.endswith('/api/record-apply')) as rr:page.locator('#rec-save').click()
  check('browser.atomic-record-save',rr.value.status==200 and rr.value.json()['saved']['revision']==3);page.locator('[data-record-revision="3"]').wait_for()
  bad=page.request.post(origin+'/api/record-apply',data=json.dumps(dict(revision=2,draft=plan['draft'],planSha256=plan['planSha256'])),headers=headers);check('http.stale-revision-no-mutation',bad.status==409 and store.read()['revision']==3)
  snap=server.contracts.load(R/'fixtures/record-mappings/snapshot.json')
  def rows(v):page.locator('#rec-json').locator('..').evaluate('(e)=>e.open=true');page.locator('#rec-json').fill(json.dumps(v));page.locator('#rec-json-load').click()
  def preview():
   with page.expect_response(lambda r:r.url.endswith('/api/record-preview')) as rr:page.locator('#rec-preview-run').click()
   assert rr.value.status==200,rr.value.text();return rr.value.json()
  page.locator('#rec-captured').fill(snap['capturedAt']);page.locator('#rec-evaluated').fill('2026-10-18T00:00:01Z');rows(snap['rows']);before=store.read();v=preview()
  check('browser.array-key-order-unit-scale-cast-and-loss',v['valid'] and [x['asset'] for x in v['result']]==['A-001','A-002'] and v['result'][1]['target']=='95' and v['quality']=='uncertain' and store.read()==before)
  check('browser.precise-trace-and-summary-visible','cast' in page.locator('#rec-preview-result').inner_text() and '≈' in page.locator('#rec-preview-result').inner_text());page.locator('#rec-preview-result').screenshot(path=str(E/'record-array-preview.png'))
  page.locator('#rec-scenario-id').fill('pressure-two-rows')
  with page.expect_response(lambda r:r.url.endswith('/api/record-scenarios')) as rr:page.locator('#rec-scenario-save').click()
  check('browser.scenario-save-without-workspace-change',rr.value.status==200 and store.read()==before and len(ra.listing(server.Store(store.path))['scenarios'])==1)
  rows([]);v=preview();check('browser.zero-array-empty',v['valid'] and v['result']==[] and v['empty'])
  page.locator('#rec-scenario').select_option('pressure-two-rows');v=preview();check('browser.scenario-reload',v['valid'] and len(v['records'])==2)
  rows([snap['rows'][0],snap['rows'][0]]);v=preview();check('browser.duplicate-key-blocks-whole-result',not v['valid'] and v['result'] is None and any('duplicate' in i['code'] for i in v['issues']))
  nullable=copy.deepcopy(snap['rows']);nullable[0]['pressure']=None;rows(nullable);v=preview();check('browser.explicit-null-default',v['valid'] and v['result'][1]['pressure']=='0' and any('default' in i['code'] for i in v['issues']))
  page.locator('#rec-quality').select_option('bad');v=preview();check('browser.bad-quality-propagation',not v['valid'] and v['quality']=='bad');page.locator('#rec-quality').select_option('good')
  page.locator('#rec-preview-map').select_option('pressure-object@1.0.0');rows(snap['rows']);v=preview();check('browser.object-selected-composite-key',v['valid'] and v['result']['asset']=='A-002')
  rows([]);v=preview();check('browser.zero-object-null',v['valid'] and v['result'] is None and v['empty'])
  # Fresh model-based authoring: typed fields, explicit unit conversion and scaling controls.
  page.locator('#rec-template').select_option('__new__');page.locator('#rec-model').select_option('record-pressure-model@1.0.0');page.locator('#rec-fields-from-model').click();check('browser.model-to-field-draft',page.locator('[data-rec-field-delete]').count()==5)
  page.locator('#rec-equipment').select_option('record-line-a');page.locator('#rec-id').fill('operator-record');page.locator('#rec-version').fill('1.0.0');page.locator('#rec-schema-id').fill('operator-result');page.locator('#rec-schema-version').fill('1.0.0');page.locator('#rec-template-id').fill('operator-record-template');page.locator('#rec-template-version').fill('1.0.0');page.locator('#rec-output').select_option('array');page.locator('#rec-author').fill('operator');page.locator('#rec-note').fill('Synthetic result schema and declared field policies');page.locator('#rec-reason').fill('Model-based synthetic records');page.locator('#rf-unit-2').select_option('Pa');page.locator('#rm-convert-1').check();page.locator('#rm-factor-2').fill('0.1');check('browser.new-form-required-fields-ready',page.evaluate("document.getElementById('record-author').checkValidity()"),invalid=page.evaluate("Array.from(document.querySelectorAll('#record-author :invalid')).map(e=>e.id)"))
  with page.expect_response(lambda r:r.url.endswith('/api/record-compose')) as rr:page.locator('#record-author button[type="submit"]').click()
  check('browser.model-fields-conversion-new-template-plan',rr.value.status==200 and rr.value.json()['valid'])
  with page.expect_response(lambda r:r.url.endswith('/api/record-apply')) as rr:page.locator('#rec-save').click()
  check('browser.new-template-and-record-atomic-save',rr.value.status==200 and rr.value.json()['saved']['revision']==4);page.locator('[data-record-revision="4"]').wait_for();page.screenshot(path=str(E/'record-workbench.png'))
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="records"]').click();page.locator('[data-record-revision="4"]').wait_for();check('browser.sqlite-reopen-immutable-history',page.locator('[data-rec-edit]').count()==4 and len(ra.listing(server.Store(store.path))['scenarios'])==1)
  page.locator('[data-tab="publication"]').click();page.locator('#submission-id').fill('records-offline');page.locator('#submission-stream').fill('record-line');page.locator('#submission-by').fill('proposer');page.locator('#submission-mapping').select_option(['record:pressure-records@1.0.1','record:operator-record@1.0.0'])
  with page.expect_response(lambda r:r.url.endswith('/api/submissions') and r.request.method=='POST') as rr:page.locator('#submission-form button[type="submit"]').click()
  record=rr.value.json();check('browser.record-only-publication-history-closure',rr.value.status==200 and record['preflightFindings']==[]);bundle=Path(record['path']);check('java.independent-definition-validation',java('mapping','validate',bundle)['accepted'])
  proposal=server.contracts.load(bundle/'proposal.json');check('wire.no-virtual-rows-or-executable-SQL-sources',all(e['kind'] not in ('virtual-result-set','source-definition') for e in proposal['files']))
  with tempfile.TemporaryDirectory(prefix='records-private-') as kd:
   keys=Path(kd);identity=registry/'identity';identity.mkdir(parents=True,exist_ok=True);public=[java('identity','keygen',who,'--out',keys) for who in ['proposer','approver']];(identity/'authorized-keys.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in public));(identity/'activation-policy.json').write_text(json.dumps({'version':'1.0.0','default':'deny','rules':[{'id':action,'principal':who,'action':action,'target':'mapping-publication','kind':'mapping-release','ref':'record-line'} for action,who in [('publish','proposer'),('approve','approver')]]}))
   check('java.real-two-key-signed-approval',java('mapping','approve',registry,bundle,'record-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key').get('kind')=='mapping-approval')
   rel=java('mapping','publish',registry,bundle,'record-release','1.0.0','--approval','record-approval');check('java.immutable-release-without-activation',rel.get('kind')=='mapping-release' and rel['activation']=='not-performed')
  with page.expect_response(lambda r:r.url.endswith('/api/submission-refresh')) as rr:page.locator('[data-submission-refresh="records-offline"]').click()
  check('browser.publication-status-refresh',rr.value.json()['publicationState']=='published');page.screenshot(path=str(E/'record-publication.png'))
  page.locator('[data-tab="templates"]').click();page.locator('[data-template-revision="4"]').wait_for();expect(page.locator('#view')).to_contain_text('레코드 매핑의 템플릿 사용처와 변경 영향');check('browser.template-record-usage-visible','operator-record' in page.locator('#view').inner_text());page.screenshot(path=str(E/'record-template-impact.png'))
  check('security.no-private-keys-in-evidence',not list(E.rglob('*.key')));check('browser.no-js-errors',not errors,errors=errors);check('browser.localhost-only',all(u.startswith(origin) for u in requests),requestCount=len(requests));browser.close()
 http.shutdown();http.server_close();th.join();report['scope']='ui-python-sqlite-java-integration';report['passed']=True;save()
if __name__=='__main__':
 try:main()
 except Exception:
  report['error']=traceback.format_exc()
  if 'page' in globals():
   try:(E/'failed-page.html').write_text(page.content());report['browserMessage']=page.locator('#message').inner_text();page.screenshot(path=str(E/'failed-page.png'))
   except Exception:pass
  save();raise
 finally:
  with tarfile.open('/evidence/runtime-evidence.tar','w') as t:t.add(E,arcname='.')
