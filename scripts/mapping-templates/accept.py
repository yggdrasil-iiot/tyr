"""Network-none operator browser + Python + independent Java acceptance."""
import copy,hashlib,json,os,sqlite3,subprocess,sys,tarfile,tempfile,threading,traceback
from pathlib import Path
E=Path('/work/evidence');E.mkdir(parents=True,exist_ok=True);R=Path('/work/tyr');report={'passed':False,'checks':[],'fieldPoV':'not-performed','deviceCommunication':'excluded','externalSQL':'excluded','writeExecution':'excluded'}
def save():(E/'template-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def check(id,ok,**details):
 print(id,bool(ok),flush=True);report['checks'].append(dict(id=id,passed=bool(ok),**details));save();assert ok,(id,details)
def java(*args):
 p=subprocess.run(['java','-jar',str(JAR),*map(str,args)],capture_output=True,text=True,timeout=120);assert p.returncode in (0,1),p.stderr
 v=json.loads(p.stdout);(E/('java-%02d.json'%len(list(E.glob('java-*.json'))))).write_text(json.dumps(v,indent=2));return v
SUITES=[('test_mapping_templates.py',[],'templates'),('test_semantic_lifecycle.py',[],'lifecycle'),('test_cross_graph.py',[],'reuse'),('test_expression_literals.py',[],'literals'),('test_expression.py',[],'expression'),('test_semantic_catalog.py',[],'catalog'),('test_p3cc.py',[],'arithmetic'),('test_p7_evaluation.py',[],'evaluation'),('test_p6_recovery.py',[],'recovery'),('test_p4ab.py',[],'import'),('test_p3fb.py',[],'graph'),('test_p3eb.py',[],'structure'),('test_p3cb.py',[],'math'),('test_a07.py',['--report',str(E/'a07.json')],'a07'),('test_p7.py',['--report',str(E/'regression.json')],'baseline')]
def main():
 with tarfile.open('/input/package.tar') as t:t.extractall('/work',filter='data')
 os.chdir(R);sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
 global JAR;JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar';report['jarSha256']=hashlib.sha256(JAR.read_bytes()).hexdigest();report['inputSha256']={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for n in ['scripts','backend','frontend','contracts','evaluation-contracts','editor-contracts','fixtures'] for p in (R/n).rglob('*') if p.is_file() and '__pycache__' not in p.parts};save()
 check('input.driver-matches-archive',hashlib.sha256(Path('/input/accept.py').read_bytes()).hexdigest()==report['inputSha256']['scripts/mapping-templates/accept.py'])
 if os.environ.get('TYR_CROSS_PYTHON_ONLY')=='1':
  report['scope']='python-full'
  for file,args,name in SUITES:
   p=subprocess.run([sys.executable,'-B',str(R/'scripts'/file),*args],capture_output=True,text=True,timeout=1200);(E/(name+'.log')).write_text(p.stdout+p.stderr);check('tests.'+name,p.returncode==0)
  report['passed']=True;save();return
 import server,mapping_templates as mt,template_authoring as ta
 from playwright.sync_api import sync_playwright,expect
 registry=E/'registry';store=server.Store(E/'editor.sqlite3');store.migrate(0,{});w=server.contracts.load(R/'fixtures/mapping-templates/before-update.json');store.save(1,w)
 with sqlite3.connect('file:/input/seed.sqlite3?mode=ro',uri=True) as src,sqlite3.connect(E/'legacy.sqlite3') as dst:src.backup(dst)
 legacy=server.Store(E/'legacy.sqlite3')
 with legacy.connect() as db:old=list(db.iterdump())
 legacy.read()
 with legacy.connect() as db:check('sqlite.legacy-read-preserves-schema-and-rows',old==list(db.iterdump()))
 http=server.make_server(store,0,JAR,registry);th=threading.Thread(target=http.serve_forever,daemon=True);th.start();origin='http://127.0.0.1:'+str(http.server_port);errors=[];requests=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1450,'height':1050});page.set_default_timeout(90000);page.on('pageerror',lambda e:(errors.append(str(e)),print('JS_ERROR',str(e),flush=True)));page.on('request',lambda r:requests.append(r.url));page.on('dialog',lambda d:d.accept() if d.type=='beforeunload' or d.type=='confirm' else d.dismiss());page.goto(origin);page.locator('#counts strong').first.wait_for();page.locator('[data-tab="templates"]').click();page.locator('#tpl-map').wait_for()
  check('browser.templates-pins-and-impact-visible',page.locator('[data-tpl-update]').count()==4 and '1.1.0' in page.locator('#view').inner_text())
  page.locator('#tpl-map').select_option('arithmetic-mapping-ab');page.locator('#tpl-name').fill('Operator pressure recipe');page.locator('#tpl-id').fill('operator-pressure');page.locator('#tpl-author').fill('operator');page.locator('#tpl-reason').fill('Synthetic operator capture')
  with page.expect_response(lambda r:r.url.endswith('/api/template-capture')) as rr:page.locator('#tpl-capture button').click()
  check('browser.capture-transitive-graph-and-slots',rr.value.status==200 and rr.value.json()['graphCount']==3 and rr.value.json()['slotCount']==3)
  page.locator('#tpl-label-0').fill('Gain factor')
  with page.expect_response(lambda r:r.url.endswith('/api/template-save')) as rr:page.locator('#tpl-save').click()
  check('browser.template-save',rr.value.status==200 and rr.value.json()['saved']['revision']==3);page.locator('[data-template-revision="3"]').wait_for()
  page.locator('[data-tpl-update="1"]').click();page.locator('#tpl-slot-0').wait_for();check('browser.update-prefills-pinned-bindings',all(page.locator('#tpl-slot-'+str(i)).input_value() for i in range(3)))
  for i,value in enumerate(['2','150','50']):page.locator('#tpl-sample-'+str(i)).fill(value)
  before=store.read();check('browser.form-request-ready',page.evaluate('templateForm().applicationId')=='pump-ua')
  def changing_sample(route):
   response=route.fetch();page.locator('#tpl-sample-1').fill('151');route.fulfill(response=response)
  page.route('**/api/template-plan',changing_sample)
  with page.expect_response(lambda r:r.url.endswith('/api/template-plan')):page.locator('#tpl-compare').click()
  expect(page.locator('#message')).to_contain_text('다시 비교');check('browser.inflight-virtual-input-invalidates-plan',page.locator('#tpl-apply').is_disabled() and store.read()==before);page.unroute('**/api/template-plan',changing_sample);page.locator('#tpl-sample-1').fill('150')
  with page.expect_response(lambda r:r.url.endswith('/api/template-plan')) as rr:page.locator('#tpl-compare').click()
  plan=rr.value.json();check('browser.plan-readonly-and-numeric-preview',rr.value.status==200 and plan['valid'] and store.read()==before and any(p['preview']['result']['value']=='100' for p in plan['previews']))
  page.locator('#tpl-slots').evaluate('(e)=>e.scrollIntoView({block:"start"})');page.screenshot(path=str(E/'templates-slots.png'))
  request=dict(revision=3,templateRef=plan['application']['templateRef'],applicationId='pump-ua',equipmentInstanceId=plan['application']['equipmentInstanceId'],targetLabel=plan['application']['targetLabel'],bindings=plan['application']['bindings'],authoredBy=plan['application']['authoredBy'],planSha256=plan['planSha256'])
  headers={'Content-Type':'application/json','X-Tyr-Editor':'1'}
  bad=page.request.post(origin+'/api/template-apply',data=json.dumps(dict(request,planSha256='0'*64)),headers=headers);check('http.plan-token-tamper-no-mutation',bad.status==422 and store.read()==before)
  with page.expect_response(lambda r:r.url.endswith('/api/template-apply')) as rr:page.locator('#tpl-apply').click()
  check('browser.explicit-update-atomic-save',rr.value.status==200 and rr.value.json()['saved']['revision']==4);page.locator('[data-template-revision="4"]').wait_for()
  apps=mt.histories(store.read()['workspace']['mappingTemplates']+store.read()['workspace']['templateApplications'])[1];check('model.only-chosen-application-updated',apps['pump-ua'][-1]['templateRef']['version']=='1.1.0' and apps['pump-ab'][-1]['templateRef']['version']=='1.0.0')
  bad=page.request.post(origin+'/api/template-apply',data=json.dumps(request),headers=headers);check('http.stale-CAS-no-mutation',bad.status==409 and store.read()['revision']==4)
  page.locator('#tpl-version').select_option('pressure-kit@1.0.0');page.locator('#tpl-equipment').select_option('line-a-motor-ab');page.locator('#tpl-app').fill('pump-extra');page.locator('#tpl-target').fill('Additional pressure object');page.locator('#tpl-apply-author').fill('operator');page.locator('#tpl-load').click();page.locator('#tpl-slot-0').wait_for();page.locator('#tpl-recommend').click()
  check('browser.one-click-recommendations',all(page.locator('#tpl-slot-'+str(i)).input_value() for i in range(3)))
  for i,value in enumerate(['2','150','50']):page.locator('#tpl-sample-'+str(i)).fill(value)
  with page.expect_response(lambda r:r.url.endswith('/api/template-plan')) as rr:page.locator('#tpl-compare').click()
  check('browser.new-application-plan',rr.value.status==200 and rr.value.json()['valid'])
  page.locator('#tpl-target').fill('Extra pressure object reviewed');check('browser.changed-input-invalidates-plan',page.locator('#tpl-apply').is_disabled())
  with page.expect_response(lambda r:r.url.endswith('/api/template-plan')):page.locator('#tpl-compare').click()
  with page.expect_response(lambda r:r.url.endswith('/api/template-apply')) as rr:page.locator('#tpl-apply').click()
  check('browser.new-application-save',rr.value.status==200 and rr.value.json()['saved']['revision']==5);page.locator('[data-template-revision="5"]').wait_for()
  page.locator('#tpl-version').select_option('pressure-kit@1.0.0');page.locator('#tpl-equipment').select_option('line-a-motor-db');page.locator('#tpl-load').click();page.locator('#tpl-slot-0').wait_for();page.locator('#tpl-slots details summary').first.click();check('browser.decoded-slot-cross-vendor-and-unit-mismatch-explained',page.locator('#tpl-slot-0 option').count()==2 and 'unit' in page.locator('#tpl-slots').text_content())
  page.locator('#tpl-author').fill('operator');page.locator('#tpl-reason').fill('Explicit shared graph revision');page.locator('[data-tpl-revise="1"]').click();page.locator('#tpl-new-version').fill('1.1.1');page.locator('select[id^="tpl-op-"]').last.select_option('subtract')
  with page.expect_response(lambda r:r.url.endswith('/api/template-save')) as rr:page.locator('#tpl-save').click()
  check('browser.shared-policy-new-version',rr.value.status==200 and rr.value.json()['saved']['revision']==6);page.locator('[data-template-revision="6"]').wait_for();check('browser.version-change-impact-no-auto-update','1.1.1' in page.locator('#view').inner_text() and [a for a in store.read()['workspace']['templateApplications'] if a['applicationId']=='pump-ua'][-1]['templateRef']['version']=='1.1.0')
  page.screenshot(path=str(E/'templates-workbench.png'));page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="templates"]').click();page.locator('#tpl-map').wait_for();check('browser.sqlite-reopen-history',len(ta.listing(server.Store(store.path))['applications'])==5 and page.locator('[data-tpl-update]').count()==5)
  page.locator('[data-tab="publication"]').click();page.locator('#submission-id').fill('templates-offline');page.locator('#submission-stream').fill('template-fixture');page.locator('#submission-by').fill('proposer');page.locator('#submission-mapping').select_option(['reuse-pump-ua-mapping'])
  with page.expect_response(lambda r:r.url.endswith('/api/submissions') and r.request.method=='POST') as rr:page.locator('#submission-form button[type="submit"]').click()
  record=rr.value.json();check('browser.submission-proof-closure',rr.value.status==200 and record['preflightFindings']==[]);bundle=Path(record['path']);check('java.independent-recompile-and-validation',java('mapping','validate',bundle)['accepted'])
  old=subprocess.run(['java','-jar','/work/old-bifrost-gates.jar','mapping','validate',str(bundle)],capture_output=True,text=True,timeout=120);check('java.old-receiver-fails-closed',old.returncode==1 and not json.loads(old.stdout)['accepted'])
  with tempfile.TemporaryDirectory(prefix='templates-private-') as kd:
   keys=Path(kd);identity=registry/'identity';identity.mkdir(parents=True,exist_ok=True);public=[java('identity','keygen',who,'--out',keys) for who in ['proposer','approver']];(identity/'authorized-keys.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in public));(identity/'activation-policy.json').write_text(json.dumps({'version':'1.0.0','default':'deny','rules':[{'id':action,'principal':who,'action':action,'target':'mapping-publication','kind':'mapping-release','ref':'template-fixture'} for action,who in [('publish','proposer'),('approve','approver')]]}))
   a=java('mapping','approve',registry,bundle,'template-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key');check('java.real-two-key-signed-approval',a.get('kind')=='mapping-approval')
   rel=java('mapping','publish',registry,bundle,'template-release','1.0.0','--approval','template-approval');check('java.immutable-release-without-activation',rel.get('kind')=='mapping-release' and rel['activation']=='not-performed')
  with page.expect_response(lambda r:r.url.endswith('/api/submission-refresh')) as rr:page.locator('[data-submission-refresh="templates-offline"]').click()
  check('browser.publication-status-refresh',rr.value.json()['publicationState']=='published');page.screenshot(path=str(E/'templates-publication.png'))
  check('security.no-private-keys-in-evidence',not list(E.rglob('*.key')));check('browser.no-js-errors',not errors,errors=errors);check('browser.localhost-only',all(u.startswith(origin) for u in requests),requestCount=len(requests))
  viewstore=server.Store(E/'views.sqlite3');viewstore.migrate(0,{});viewstore.save(1,server.contracts.load(R/'fixtures/mapping-templates/views-workspace.json'));viewhttp=server.make_server(viewstore,0,JAR,registry);vt=threading.Thread(target=viewhttp.serve_forever,daemon=True);vt.start();vo='http://127.0.0.1:'+str(viewhttp.server_port);vp=browser.new_page(viewport={'width':1450,'height':1050});vp.set_default_timeout(90000);ve=[];vr=[];vp.on('pageerror',lambda e:ve.append(str(e)));vp.on('request',lambda r:vr.append(r.url));vp.on('dialog',lambda d:d.accept() if d.type in ('beforeunload','confirm') else d.dismiss());vp.goto(vo);vp.locator('#counts strong').first.wait_for();vp.locator('[data-tab="templates"]').click();vp.locator('[data-template-revision="2"]').wait_for();vp.locator('[data-tpl-update="0"]').click();vp.locator('#tpl-slot-0').wait_for();check('browser.view-slot-shows-interpreted-type-and-parent-word','Boolean' in vp.locator('#tpl-slots').inner_text() and 'a07-melsec-word' in vp.locator('#tpl-sample-0').locator('..').inner_text());vp.locator('#tpl-sample-0').fill('0080');vbefore=viewstore.read()
  with vp.expect_response(lambda r:r.url.endswith('/api/template-plan')) as rr:vp.locator('#tpl-compare').click()
  check('browser.view-parent-raw-preview',rr.value.status==200 and rr.value.json()['valid'] and rr.value.json()['previews'][0]['preview']['result']['value'] is True and viewstore.read()==vbefore)
  vp.locator('#tpl-slots').evaluate('(e)=>e.scrollIntoView({block:"start"})');vp.screenshot(path=str(E/'templates-view-parent.png'))
  with vp.expect_response(lambda r:r.url.endswith('/api/template-apply')) as rr:vp.locator('#tpl-apply').click()
  check('browser.view-parent-atomic-save',rr.value.status==200 and len(rr.value.json()['application']['sourceSnapshots'])==3);vp.locator('[data-template-revision="3"]').wait_for();check('browser.view-localhost-and-no-js-errors',not ve and all(u.startswith(vo) for u in vr),errors=ve);vp.close();viewhttp.shutdown();viewhttp.server_close();vt.join();browser.close()
 http.shutdown();http.server_close();th.join();report['scope']='ui-python-sqlite-java-integration';report['passed']=True;save()
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();save();raise
 finally:
  with tarfile.open('/evidence/runtime-evidence.tar','w') as t:t.add(E,arcname='.')
