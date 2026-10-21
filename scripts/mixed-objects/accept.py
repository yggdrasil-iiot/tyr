"""Network-none operator browser + Python + independent Java acceptance."""
import copy,hashlib,json,os,sqlite3,subprocess,sys,tarfile,tempfile,threading,traceback
from pathlib import Path
E=Path('/work/evidence');E.mkdir(parents=True,exist_ok=True);R=Path('/work/tyr');report={'passed':False,'checks':[],'fieldPoV':'not-performed','deviceCommunication':'excluded','externalSQL':'excluded','writeExecution':'excluded'}
def save():(E/'mixed-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def check(id,ok,**details):
 print(id,bool(ok),flush=True);report['checks'].append(dict(id=id,passed=bool(ok),**details));save();assert ok,(id,details)
def java(*args):
 p=subprocess.run(['java','-jar',str(JAR),*map(str,args)],capture_output=True,text=True,timeout=120);assert p.returncode in (0,1),p.stderr
 v=json.loads(p.stdout);(E/('java-%02d.json'%len(list(E.glob('java-*.json'))))).write_text(json.dumps(v,indent=2));return v
SUITES=[('test_mixed_objects.py',[],'mixed'),('test_record_mappings.py',[],'records'),('test_mapping_templates.py',[],'templates'),('test_semantic_lifecycle.py',[],'lifecycle'),('test_cross_graph.py',[],'reuse'),('test_expression_literals.py',[],'literals'),('test_expression.py',[],'expression'),('test_semantic_catalog.py',[],'catalog'),('test_p3cc.py',[],'arithmetic'),('test_p7_evaluation.py',[],'evaluation'),('test_p6_recovery.py',[],'recovery'),('test_p4ab.py',[],'import'),('test_p3fb.py',[],'graph'),('test_p3eb.py',[],'structure'),('test_p3cb.py',[],'math'),('test_a07.py',['--report',str(E/'a07.json')],'a07'),('test_p7.py',['--report',str(E/'regression.json')],'baseline')]


def main():
 with tarfile.open('/input/package.tar') as t:t.extractall('/work',filter='data')
 os.chdir(R);sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
 global JAR;JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar';report['jarSha256']=hashlib.sha256(JAR.read_bytes()).hexdigest();save()
 check('input.driver-matches-archive',Path('/input/accept.py').read_bytes()==(R/'scripts/mixed-objects/accept.py').read_bytes())
 if os.environ.get('TYR_CROSS_PYTHON_ONLY')=='1':
  report['scope']='python-full'
  for file,args,name in SUITES:
   p=subprocess.run([sys.executable,'-B',str(R/'scripts'/file),*args],capture_output=True,text=True,timeout=1200);(E/(name+'.log')).write_text(p.stdout+p.stderr);check('tests.'+name,p.returncode==0)
  report['passed']=True;save();return
 import server,record_fields as rf,mapping_templates as mt
 from playwright.sync_api import sync_playwright,expect
 registry=E/'registry';st=server.Store(E/'editor.sqlite3');st.migrate(0,{});st.save(1,server.contracts.load(R/'fixtures/mixed-objects/before.json'))
 with sqlite3.connect('file:/input/seed.sqlite3?mode=ro',uri=True) as src,sqlite3.connect(E/'legacy.sqlite3') as dst:src.backup(dst)
 old=server.Store(E/'legacy.sqlite3')
 with old.connect() as c:dump=list(c.iterdump())
 old.read()
 with old.connect() as c:check('sqlite.legacy-read-no-migration',dump==list(c.iterdump()))
 http=server.make_server(st,0,JAR,registry);th=threading.Thread(target=http.serve_forever,daemon=True);th.start();origin='http://127.0.0.1:'+str(http.server_port);errors=[];requests=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(60000);page.on('pageerror',lambda e:(errors.append(str(e)),print('JS_ERROR',str(e),flush=True)));page.on('request',lambda r:requests.append(r.url));page.on('dialog',lambda d:d.accept() if d.type in ('beforeunload','confirm') else d.dismiss());page.goto(origin);page.locator('#counts strong').first.wait_for();page.locator('[data-tab="mixedObjects"]').click();page.locator('[data-mixed-revision="2"]').wait_for();page.locator('#mo-equipment').select_option('record-line-b');page.locator('#mo-model').select_option('combined-model@1.0.0')
  check('browser.model-properties-and-four-source-families',page.locator('#mo-input-0 option').count()>5 and 'DB 필드' in page.locator('#mo-bindings').inner_text())
  for id,v in [('mo-app','operator-mixed'),('mo-template','operator-mixed-kit'),('mo-label','Operator mixed pump'),('mo-author','operator'),('mo-reason','Synthetic mixed object review'),('mo-note','Offline PLC/record/constant/external declarations')]:page.locator('#'+id).fill(v)
  def choose(i,predicate):
   opts=page.locator('#mo-input-'+str(i)).evaluate('(e)=>Array.from(e.options).map(o=>({value:o.value,text:o.text}))');key=next(x['value'] for x in opts if x['value'] and predicate(json.loads(x['value'])));page.locator('#mo-input-'+str(i)).select_option(key)
  for i,id in [(0,'mixed-plc-pressure'),(2,'mixed-baseline'),(3,'mixed-external-reference'),(4,'mixed-line-code')]:choose(i,lambda v,id=id:isinstance(v,list) and v[0]=='source' and v[1]==id)
  choose(1,lambda v:isinstance(v,dict) and v['recordMappingRef']['id']=='pressure-object' and v['fieldId']=='target');choose(2,lambda v:isinstance(v,dict) and v['recordMappingRef']['id']=='pressure-object' and v['fieldId']=='pressure');page.locator('#mo-unit-2').check();page.locator('#mo-factor-0').fill('0.1');page.locator('#mo-factor-1').fill('0.1');page.locator('#mo-temporal').check();before=st.read()
  with page.expect_response(lambda r:r.url.endswith('/api/mixed-object-compose')) as rr:page.locator('#mo-authoring button[type="submit"]').click()
  plan=rr.value.json();check('browser.compose-readonly-and-pinned-record-field',rr.value.status==200 and plan['valid'] and len(plan['draft']['sources'])==2 and st.read()==before)
  page.locator('#mo-label').fill('Reviewed operator mixed pump');check('browser.changed-form-invalidates-plan',page.locator('#mo-save').is_disabled())
  with page.expect_response(lambda r:r.url.endswith('/api/mixed-object-compose')) as rr:page.locator('#mo-authoring button[type="submit"]').click()
  plan=rr.value.json();headers={'Content-Type':'application/json','X-Tyr-Editor':'1'};bad=page.request.post(origin+'/api/mixed-object-apply',data=json.dumps(dict(revision=2,draft=plan['draft'],planSha256='0'*64)),headers=headers);check('http.plan-tamper-no-mutation',bad.status==422 and st.read()==before)
  with page.expect_response(lambda r:r.url.endswith('/api/mixed-object-apply')) as rr:page.locator('#mo-save').click()
  check('browser.atomic-object-source-template-application-save',rr.value.status==200 and rr.value.json()['saved']['revision']==3);page.locator('[data-mixed-revision="3"]').wait_for();page.locator('#mo-target').select_option(json.dumps(dict(id='reuse-operator-mixed-target',version='1.0.0'),separators=(',',':')));page.locator('#mo-evaluation').fill('2026-10-18T00:00:00.500Z');page.locator('#mo-example').click()
  field=next(x['definition'] for x in st.read()['workspace']['sources'] if x['definition'].get('recordField',{}).get('fieldId')=='target');ids=page.evaluate('moRequired()');snap=server.contracts.load(R/'fixtures/record-mappings/snapshot.json')
  for i,id in enumerate(ids):
   src=next(x['definition'] for x in st.read()['workspace']['sources'] if x['definition']['id']==id)
   if src.get('recordField') and page.evaluate('(i)=>moInputIndex(moRequired(),i)',i)!=i:continue
   if src.get('recordField'):page.locator('#mo-sample-'+str(i)).fill(json.dumps(snap))
   elif id=='mixed-plc-pressure':page.locator('#mo-sample-'+str(i)).fill('b004');page.locator('#mo-time-'+str(i)).fill(snap['capturedAt'])
   else:page.locator('#mo-sample-'+str(i)).fill('101');page.locator('#mo-time-'+str(i)).fill(snap['capturedAt'])
  def preview():
   with page.expect_response(lambda r:r.url.endswith('/api/logical-preview')) as rr:page.locator('#mo-preview').click()
   assert rr.value.status==200,rr.value.text();return rr.value.json()
  expected=dict(server.contracts.load(R/'fixtures/mixed-objects/oracle.json'),baseline='123.4500000000000028421709430404007434844970703125');before=st.read();p=preview();check('browser.combined-object-scale-cast-and-provenance',p['quality']=='uncertain' and p['result']==expected and st.read()==before);check('browser.source-origins-visible-without-trace-expansion',all(k in page.locator('.mixed-origin').all_text_contents().__str__() for k in ['PLC','DB 필드','상수','외부 값']));check('browser.same-record-fields-share-one-editor',len([r for r in st.read()['workspace']['sources'] if r['definition'].get('recordField')])==2 and page.locator('#mo-samples textarea').count()==1);check('browser.record-key-trace-visible','record-field-select' in page.locator('#mo-preview-result').text_content() and 'A-002' in page.locator('#mo-preview-result').text_content());page.locator('#mo-preview-result').screenshot(path=str(E/'mixed-object-preview.png'))
  page.locator('#mo-scene-id').fill('mixed-scene')
  with page.expect_response(lambda r:r.url.endswith('/api/scenarios') and r.request.method=='POST') as rr:page.locator('#mo-scene-save').click()
  scene=rr.value.json();check('browser.virtual-scene-separate-SQLite-save',rr.value.status==200 and st.read()==before and scene['scenario']['kind']=='object-preview-scenario');bad=page.request.post(origin+'/api/scenarios',data=json.dumps(dict(workspaceRevision=3,scenarioRevision=0,scenario=scene['scenario'])),headers=headers);check('http.scenario-CAS-protected',bad.status==409)
  fi=ids.index(field['id']);changed=copy.deepcopy(snap);changed['rows'].append(copy.deepcopy(changed['rows'][1]));page.locator('#mo-sample-'+str(fi)).fill(json.dumps(changed));p=preview();check('browser.duplicate-record-key-blocks-whole-object',p['result'] is None and any(i['code']=='record-field.duplicate-key' for i in p['issues']))
  changed=copy.deepcopy(snap);changed['rows']=[];page.locator('#mo-sample-'+str(fi)).fill(json.dumps(changed));p=preview();check('browser.zero-record-blocks-whole-object',p['result'] is None)
  changed=copy.deepcopy(snap);changed['quality']='bad';page.locator('#mo-sample-'+str(fi)).fill(json.dumps(changed));p=preview();check('browser.bad-DB-quality-propagation',p['result'] is None and any(i['code']=='quality.bad-input' for i in p['issues']))
  page.locator('#mo-sample-'+str(fi)).fill(json.dumps(snap));pi=ids.index('mixed-plc-pressure');page.locator('#mo-quality-'+str(pi)).select_option('bad');p=preview();check('browser.bad-PLC-quality-propagation',p['result'] is None);page.locator('#mo-quality-'+str(pi)).select_option('good');page.locator('#mo-evaluation').fill('2026-10-18T00:00:02Z');p=preview();check('browser.freshness-blocks-stale-object',p['result'] is None and any(i['code']=='time.stale-input' for i in p['issues']))
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="mixedObjects"]').click();page.locator('[data-mixed-revision="3"]').wait_for();page.locator('#mo-scene-picker').select_option('mixed-scene');page.locator('#mo-scene-load').click();p=preview();check('browser.SQLite-reopen-and-scene-replay',p['result']==expected);page.screenshot(path=str(E/'mixed-workbench.png'))
  page.locator('[data-tab="templates"]').click();page.locator('[data-template-revision="3"]').wait_for();page.locator('#tpl-version').select_option('operator-mixed-kit@1.0.0');page.locator('#tpl-equipment').select_option('record-line-b');page.locator('#tpl-app').fill('operator-mixed-copy');page.locator('#tpl-target').fill('Second mixed object');page.locator('#tpl-apply-author').fill('operator');page.locator('#tpl-load').click();page.locator('#tpl-slot-0').wait_for();t=next(t for t in st.read()['workspace']['mappingTemplates'] if t['id']=='operator-mixed-kit')
  for i,slot in enumerate(t['slots']):page.locator('#tpl-slot-'+str(i)).select_option(json.dumps(slot['sourceRef'],separators=(',',':')))
  with page.expect_response(lambda r:r.url.endswith('/api/template-plan')) as rr:page.locator('#tpl-compare').click()
  check('browser.existing-template-record-source-reuse-plan',rr.value.status==200 and rr.value.json()['valid'])
  with page.expect_response(lambda r:r.url.endswith('/api/template-apply')) as rr:page.locator('#tpl-apply').click()
  check('browser.reuse-second-object-atomic-save',rr.value.status==200 and rr.value.json()['saved']['revision']==4);page.locator('[data-template-revision="4"]').wait_for();state=st.read()['workspace'];check('model.record-source-pin-preserved-across-reuse',len([r for r in state['sources'] if r['definition'].get('recordField')])==2 and len(state['templateApplications'])==2)
  page.locator('[data-tab="mixedObjects"]').click();page.locator('[data-mixed-revision="4"]').wait_for();page.locator('#mo-scene-picker').select_option('mixed-scene');page.locator('#mo-scene-load').click();expect(page.locator('#message')).to_contain_text('이전 정의');check('browser.old-scene-marked-stale-after-definition-change',st.read()['revision']==4)
  page.locator('[data-tab="records"]').click();page.locator('[data-record-revision="4"]').wait_for();check('browser.existing-record-workbench-compatible',page.locator('[data-rec-edit]').count()==2)
  page.locator('[data-tab="publication"]').click();page.locator('#submission-id').fill('mixed-offline');page.locator('#submission-stream').fill('combined-line');page.locator('#submission-by').fill('proposer');page.locator('#submission-mapping').select_option(['reuse-operator-mixed-mapping','reuse-operator-mixed-copy-mapping'])
  with page.expect_response(lambda r:r.url.endswith('/api/submissions') and r.request.method=='POST') as rr:page.locator('#submission-form button[type="submit"]').click()
  sub=rr.value.json();check('browser.publication-record-template-source-proof-closure',rr.value.status==200 and sub['preflightFindings']==[]);bundle=Path(sub['path']);check('java.independent-mixed-object-validation',java('mapping','validate',bundle)['accepted']);proposal=server.contracts.load(bundle/'proposal.json');check('wire.virtual-inputs-not-published',proposal['schemaVersion']=='2.21.0' and all(e['kind'] not in ('virtual-result-set','object-preview-scenario','write-definition') for e in proposal['files']))
  with tempfile.TemporaryDirectory(prefix='mixed-private-') as kd:
   keys=Path(kd);identity=registry/'identity';identity.mkdir(parents=True,exist_ok=True);public=[java('identity','keygen',who,'--out',keys) for who in ['proposer','approver']];(identity/'authorized-keys.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in public));(identity/'activation-policy.json').write_text(json.dumps({'version':'1.0.0','default':'deny','rules':[{'id':action,'principal':who,'action':action,'target':'mapping-publication','kind':'mapping-release','ref':'combined-line'} for action,who in [('publish','proposer'),('approve','approver')]]}));check('java.real-two-key-signed-approval',java('mapping','approve',registry,bundle,'mixed-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key').get('kind')=='mapping-approval');rel=java('mapping','publish',registry,bundle,'mixed-release','1.0.0','--approval','mixed-approval');check('java.immutable-release-without-activation',rel.get('kind')=='mapping-release' and rel['activation']=='not-performed')
  with page.expect_response(lambda r:r.url.endswith('/api/submission-refresh')) as rr:page.locator('[data-submission-refresh="mixed-offline"]').click()
  check('browser.release-status-refresh',rr.value.json()['publicationState']=='published');page.screenshot(path=str(E/'mixed-publication.png'));check('security.private-keys-excluded',not list(E.rglob('*.key')));check('browser.no-js-errors',not errors,errors=errors);check('browser.localhost-only',all(u.startswith(origin) for u in requests),requestCount=len(requests));browser.close()
 http.shutdown();http.server_close();th.join();report['passed']=True;report['scope']='ui-python-sqlite-java-integration';save()
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();save();raise
 finally:
  with tarfile.open('/evidence/runtime-evidence.tar','w') as t:t.add(E,arcname='.')
