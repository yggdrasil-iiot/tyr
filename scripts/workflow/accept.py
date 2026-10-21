"""Network-none operator browser + Python + independent Java acceptance."""
import copy,hashlib,json,os,sqlite3,subprocess,sys,tarfile,tempfile,threading,traceback
from pathlib import Path
E=Path('/work/evidence');E.mkdir(parents=True,exist_ok=True);R=Path('/work/tyr');report={'passed':False,'checks':[],'fieldPoV':'not-performed','deviceCommunication':'excluded','externalSQL':'excluded','writeExecution':'excluded'}
def save():(E/'workflow-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def check(id,ok,**details):
 print(id,bool(ok),flush=True);report['checks'].append(dict(id=id,passed=bool(ok),**details));save();assert ok,(id,details)
def java(*args):
 p=subprocess.run(['java','-jar',str(JAR),*map(str,args)],capture_output=True,text=True,timeout=120);assert p.returncode in (0,1),p.stderr
 v=json.loads(p.stdout);(E/('java-%02d.json'%len(list(E.glob('java-*.json'))))).write_text(json.dumps(v,indent=2));return v
SUITES=[('test_workflow.py',[],'workflow'),('test_broadcast.py',[],'broadcast'),('test_mixed_objects.py',[],'mixed'),('test_record_mappings.py',[],'records'),('test_mapping_templates.py',[],'templates'),('test_semantic_lifecycle.py',[],'lifecycle'),('test_cross_graph.py',[],'reuse'),('test_expression_literals.py',[],'literals'),('test_expression.py',[],'expression'),('test_semantic_catalog.py',[],'catalog'),('test_p3cc.py',[],'arithmetic'),('test_p7_evaluation.py',[],'evaluation'),('test_p6_recovery.py',[],'recovery'),('test_p4ab.py',[],'import'),('test_p3fb.py',[],'graph'),('test_p3eb.py',[],'structure'),('test_p3cb.py',[],'math'),('test_a07.py',['--report',str(E/'a07.json')],'a07'),('test_p7.py',['--report',str(E/'regression.json')],'baseline')]


def main():
 with tarfile.open('/input/package.tar') as t:t.extractall('/work',filter='data')
 os.chdir(R);sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
 global JAR;JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar';report['jarSha256']=hashlib.sha256(JAR.read_bytes()).hexdigest();save()
 check('input.driver-matches-archive',Path('/input/accept.py').read_bytes()==(R/'scripts/workflow/accept.py').read_bytes())
 if os.environ.get('TYR_CROSS_PYTHON_ONLY')=='1':
  report['scope']='python-full'
  for file,args,name in (SUITES[:1] if os.environ.get('TYR_BROADCAST_FOCUS_ONLY')=='1' else SUITES):
   p=subprocess.run([sys.executable,'-B',str(R/'scripts'/file),*args],capture_output=True,text=True,timeout=1200);(E/(name+'.log')).write_text(p.stdout+p.stderr);check('tests.'+name,p.returncode==0)
  report['passed']=True;save();return
 import server,result_schemas as rs,record_mappings as rm,mapping_templates as mt
 from playwright.sync_api import sync_playwright,expect
 registry=E/'registry';st=server.Store(E/'editor.sqlite3');st.migrate(0,{});st.save(1,server.contracts.load(R/'fixtures/workflow/before.json'))
 with sqlite3.connect('file:/input/seed.sqlite3?mode=ro',uri=True) as src,sqlite3.connect(E/'legacy.sqlite3') as dst:src.backup(dst)
 old=server.Store(E/'legacy.sqlite3')
 with old.connect() as c:dump=list(c.iterdump())
 old.read()
 with old.connect() as c:check('sqlite.legacy-read-no-migration',dump==list(c.iterdump()))
 http=server.make_server(st,0,JAR,registry);th=threading.Thread(target=http.serve_forever,daemon=True);th.start();origin='http://127.0.0.1:'+str(http.server_port);errors=[];requests=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1550,'height':1100});page.set_default_timeout(60000);page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url));page.on('dialog',lambda d:d.accept() if d.type in ('beforeunload','confirm') else d.dismiss());page.goto(origin);page.locator('#counts strong').first.wait_for();expect(page.locator('#view h2')).to_have_text('자료 준비');check('browser.five-stages-and-all-existing-tools',page.locator('aside [data-workflow-stage]').count()==5 and page.locator('aside [data-tab]').count()==23);page.screenshot(path=str(E/'workflow-prepare.png'))
  page.locator('[data-tab="resultSchemas"]').click();page.locator('#rs-fields').wait_for();definition=server.contracts.load(R/'fixtures/workflow/definition.json');schema=definition['resultSchema']
  for id,value in [('rs-id',schema['id']),('rs-label','독립 압력 결과 스키마'),('rs-provider',schema['providerRef']),('rs-value-key',schema['valueKey']),('rs-author-name','operator'),('rs-reason','Independent schema preparation'),('rs-note','Virtual declarations only')]:page.locator('#'+id).fill(value)
  for i,f in enumerate(schema['fields']):
   if i:page.locator('#rs-add').click()
   page.locator('#rs-f-id-'+str(i)).fill(f['fieldId']);page.locator('#rs-f-name-'+str(i)).fill(f['name']);page.locator('#rs-f-type-'+str(i)).select_option(f['valueType']);page.locator('#rs-f-unit-'+str(i)).select_option(f['unit'].get('code',f['unit']['status']));page.locator('#rs-f-stage-'+str(i)).select_option(f['inputStage']);page.locator('#rs-f-key-'+str(i)).set_checked(f['fieldId'] in schema['keyFields']);page.locator('#rs-f-null-'+str(i)).set_checked(f['nullable'])
  page.locator('#rs-extra').select_option(schema['unknownFields']);page.locator('#rs-author > details > summary').click();page.locator('#rs-query-language').select_option(schema['query']['language']);page.locator('#rs-query').fill(schema['query']['text'] or '')
  def schema_plan():
   with page.expect_response(lambda r:r.url.endswith('/api/result-schema-plan')) as rr:page.locator('#rs-author button[type="submit"]').click()
   assert rr.value.status==200,rr.value.text();return rr.value.json()
  before=st.read();p=schema_plan();check('browser.independent-schema-plan-readonly',p['valid'] and st.read()==before);page.locator('#rs-label').fill('검토한 독립 압력 스키마');check('browser.schema-plan-invalidated-on-edit',page.locator('#rs-save').is_disabled());p=schema_plan();headers={'Content-Type':'application/json','X-Tyr-Editor':'1'};bad=page.request.post(origin+'/api/result-schema-apply',data=json.dumps(dict(revision=2,definition=p['definition'],planSha256='0'*64)),headers=headers);check('http.schema-plan-tamper-blocked',bad.status==422 and st.read()==before)
  with page.expect_response(lambda r:r.url.endswith('/api/result-schema-apply')) as rr:page.locator('#rs-save').click()
  assert rr.value.status==200,rr.value.text();w=st.read()['workspace'];check('browser.schema-saved-without-any-record-or-template',len(w['resultSchemas'])==1 and not w.get('recordMappings') and not w.get('mappingTemplates'));page.locator('[data-rs-edit="0"]').wait_for();page.screenshot(path=str(E/'workflow-schema.png'))
  page.reload();page.locator('#counts strong').first.wait_for();check('browser.schema-reopen',len(st.read()['workspace']['resultSchemas'])==1);page.locator('aside [data-workflow-stage="object"]').click();page.locator('#wf-equipment').select_option('record-line-b');page.locator('#wf-model').select_option('combined-model@1.0.0');page.locator('#view [data-workflow-stage="connect"]').click();expect(page.locator('#view h2')).to_have_text('연결');page.locator('#view [data-workflow-go="broadcast"]').click();page.locator('[data-broadcast-revision="3"]').wait_for();check('browser.context-carried-and-independent-schema-selected',page.locator('#bc-equipment').input_value()=='record-line-b' and page.locator('#bc-model').input_value()=='combined-model@1.0.0' and page.locator('#bc-schema').input_value()=='schema:'+schema['id']+'@'+schema['version'])
  for i,v in enumerate(['common:mixed-plc-pressure@1.0.0','field:target','common:mixed-baseline@1.0.0','common:mixed-external-reference@1.0.0','common:mixed-line-code@1.0.0']):page.locator('#bc-input-'+str(i)).select_option(v)
  for i in [0,1]:page.locator('#bc-factor-'+str(i)).fill('0.1')
  for id,v in [('bc-id','workflow-array'),('bc-template-id','workflow-kit'),('bc-author','operator'),('bc-reason','Offline operator workflow'),('bc-note','Independent result schema; shared PLC values')]:page.locator('#'+id).fill(v)
  page.locator('#workflow-toolbar [data-workflow-stage="verify"]').last.click();expect(page.locator('#message')).to_contain_text('입력은 그대로 보존');check('browser.forward-step-preserves-unsaved-connection',page.locator('#bc-factor-0').input_value()=='0.1')
  with page.expect_response(lambda r:r.url.endswith('/api/broadcast-compose')) as rr:page.locator('#bc-compare').click()
  assert rr.value.status==200,rr.value.text();check('browser.array-plan-no-record-preparation',rr.value.json()['valid'] and not st.read()['workspace'].get('recordMappings'))
  with page.expect_response(lambda r:r.url.endswith('/api/record-apply')) as rr:page.locator('#bc-save').click()
  assert rr.value.status==200,rr.value.text();page.locator('[data-broadcast-revision="4"]').wait_for();check('browser.array-and-template-atomic-save',len(st.read()['workspace']['recordMappings'])==1 and st.read()['workspace']['recordMappings'][0]['schemaVersion']=='2.22.0')
  page.locator('aside [data-workflow-stage="verify"]').click();page.locator('#view [data-workflow-go="broadcast"]').click();page.locator('[data-broadcast-revision="4"]').wait_for();expect(page.locator('#workflow-toolbar [aria-current="step"]')).to_contain_text('검증');r=st.read()['workspace']['recordMappings'][0];snap=server.contracts.load(R/'fixtures/broadcast/snapshot.json');snap['resultSetRef']=rm.pin(r['resultSchema']);page.locator('#bc-snapshot').fill(json.dumps(snap));sources=page.evaluate('bcInputs().map(s=>s.id)')
  for i,id in enumerate(sources):page.locator('#bc-value-'+str(i)).fill('b004' if id=='mixed-plc-pressure' else '101')
  with page.expect_response(lambda r:r.url.endswith('/api/broadcast-preview')) as rr:page.locator('#bc-preview').click()
  p=rr.value.json();expected=[dict(actual='120',target='90',baseline='100',external='101',line_code='LINE-A'),dict(actual='120',target='95',baseline='100',external='101',line_code='LINE-A')];check('browser.verify-stage-and-canonical-array',rr.value.status==200 and p['result']==expected and p['quality']=='good');check('browser.source-and-loss-visible',page.locator('#bc-result .mixed-origin').count()==10);page.locator('#bc-result').screenshot(path=str(E/'workflow-preview.png'))
  page.locator('#bc-scene-id').fill('workflow-scene')
  with page.expect_response(lambda r:r.url.endswith('/api/broadcast-scenarios')) as rr:page.locator('#bc-scene-save').click()
  check('browser.scenario-save',rr.value.status==200 and st.read()['revision']==4)
  page.locator('[data-tab="resultSchemas"]').click();page.locator('[data-rs-edit="0"]').click();expect(page.locator('#rs-version')).to_have_value('1.0.1');page.locator('#rs-f-name-2').fill('개정 목표값 표시');page.locator('#rs-reason').fill('Explicit schema revision');p=schema_plan();check('browser.schema-version-pin-history',p['definition']['previousSchemaRef']['id']==schema['id'])
  with page.expect_response(lambda r:r.url.endswith('/api/result-schema-apply')) as rr:page.locator('#rs-save').click()
  assert rr.value.status==200,rr.value.text();page.locator('[data-rs-edit="1"]').wait_for();w=st.read()['workspace'];check('browser.schema-update-does-not-retarget-existing-mapping',len(w['resultSchemas'])==2 and w['recordMappings'][0]['resultSchema']==schema and w['recordMappings'][0]['version']=='1.0.0');check('browser.schema-usage-visible','workflow-array' in page.locator('#view').inner_text());old=copy.deepcopy(w);old['resultSchemas'][0]['label']='rewrite';bad=page.request.post(origin+'/api/workspace',data=json.dumps(dict(revision=5,workspace=old)),headers=headers);check('http.immutable-schema-rewrite-blocked',bad.status==422 and st.read()['revision']==5)
  page.locator('aside [data-workflow-stage="review"]').click();expect(page.locator('#view h2')).to_have_text('검토·제출');page.locator('#view [data-workflow-go="templates"]').click();page.locator('[data-template-revision="5"]').wait_for();check('browser.template-impact-retains-review-stage','검토·제출' in page.locator('#workflow-toolbar [aria-current="step"]').inner_text());page.locator('aside [data-workflow-stage="review"]').click();page.locator('#view [data-workflow-go="review"]').click();page.locator('#view').wait_for();check('browser.review-stage-reachable',page.locator('#workflow-toolbar [aria-current="step"]').inner_text().endswith('검토·제출'));page.locator('[data-tab="publication"]').click();page.locator('#submission-id').fill('workflow-offline');page.locator('#submission-stream').fill('workflow-line');page.locator('#submission-by').fill('proposer');page.locator('#submission-mapping').select_option(['record:workflow-array@1.0.0'])
  with page.expect_response(lambda r:r.url.endswith('/api/submissions') and r.request.method=='POST') as rr:page.locator('#submission-form button[type="submit"]').click()
  assert rr.value.status==200,rr.value.text();sub=rr.value.json();check('browser.review-submit-compatible-closure',sub['preflightFindings']==[]);bundle=Path(sub['path']);proposal=server.contracts.load(bundle/'proposal.json');check('wire.same-2.22-contract-no-editor-catalog-or-values',proposal['schemaVersion']=='2.22.0' and not any(e['kind'] in ('result-schema-definition','virtual-result-set','broadcast-scenario','write-definition') for e in proposal['files']));check('java.unchanged-receiver-accepts-independent-schema',java('mapping','validate',bundle)['accepted'])
  with tempfile.TemporaryDirectory(prefix='workflow-private-') as kd:
   keys=Path(kd);identity=registry/'identity';identity.mkdir(parents=True,exist_ok=True);public=[java('identity','keygen',who,'--out',keys) for who in ['proposer','approver']];(identity/'authorized-keys.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in public));(identity/'activation-policy.json').write_text(json.dumps({'version':'1.0.0','default':'deny','rules':[{'id':action,'principal':who,'action':action,'target':'mapping-publication','kind':'mapping-release','ref':'workflow-line'} for action,who in [('publish','proposer'),('approve','approver')]]}));check('java.real-two-key-approval',java('mapping','approve',registry,bundle,'workflow-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key').get('kind')=='mapping-approval');rel=java('mapping','publish',registry,bundle,'workflow-release','1.0.0','--approval','workflow-approval');check('java.release-without-activation',rel.get('kind')=='mapping-release' and rel['activation']=='not-performed')
  with page.expect_response(lambda r:r.url.endswith('/api/submission-refresh')) as rr:page.locator('[data-submission-refresh="workflow-offline"]').click()
  check('browser.published-status',rr.value.json()['publicationState']=='published');page.screenshot(path=str(E/'workflow-publication.png'));check('security.no-private-keys',not list(E.rglob('*.key')));check('browser.no-js-errors',not errors,errors=errors);check('browser.localhost-only',all(u.startswith(origin) for u in requests));check('workflow.never-entered-record-only-authoring',not any('/api/record-compose' in u for u in requests));browser.close()
 http.shutdown();http.server_close();th.join();report['passed']=True;report['scope']='operator-workflow-browser-python-sqlite-unchanged-java';save()
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();save();raise
 finally:
  with tarfile.open('/evidence/runtime-evidence.tar','w') as t:t.add(E,arcname='.')
