"""Network-none operator browser + Python + independent Java acceptance."""
import copy,hashlib,json,os,sqlite3,subprocess,sys,tarfile,tempfile,threading,traceback
from pathlib import Path
E=Path('/work/evidence');E.mkdir(parents=True,exist_ok=True);R=Path('/work/tyr');report={'passed':False,'checks':[],'fieldPoV':'not-performed','deviceCommunication':'excluded','externalSQL':'excluded','writeExecution':'excluded'}
def save():(E/'broadcast-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def check(id,ok,**details):
 print(id,bool(ok),flush=True);report['checks'].append(dict(id=id,passed=bool(ok),**details));save();assert ok,(id,details)
def java(*args):
 p=subprocess.run(['java','-jar',str(JAR),*map(str,args)],capture_output=True,text=True,timeout=120);assert p.returncode in (0,1),p.stderr
 v=json.loads(p.stdout);(E/('java-%02d.json'%len(list(E.glob('java-*.json'))))).write_text(json.dumps(v,indent=2));return v
SUITES=[('test_broadcast.py',[],'broadcast'),('test_mixed_objects.py',[],'mixed'),('test_record_mappings.py',[],'records'),('test_mapping_templates.py',[],'templates'),('test_semantic_lifecycle.py',[],'lifecycle'),('test_cross_graph.py',[],'reuse'),('test_expression_literals.py',[],'literals'),('test_expression.py',[],'expression'),('test_semantic_catalog.py',[],'catalog'),('test_p3cc.py',[],'arithmetic'),('test_p7_evaluation.py',[],'evaluation'),('test_p6_recovery.py',[],'recovery'),('test_p4ab.py',[],'import'),('test_p3fb.py',[],'graph'),('test_p3eb.py',[],'structure'),('test_p3cb.py',[],'math'),('test_a07.py',['--report',str(E/'a07.json')],'a07'),('test_p7.py',['--report',str(E/'regression.json')],'baseline')]


def main():
 with tarfile.open('/input/package.tar') as t:t.extractall('/work',filter='data')
 os.chdir(R);sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
 global JAR;JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar';report['jarSha256']=hashlib.sha256(JAR.read_bytes()).hexdigest();save()
 check('input.driver-matches-archive',Path('/input/accept.py').read_bytes()==(R/'scripts/broadcast/accept.py').read_bytes())
 if os.environ.get('TYR_CROSS_PYTHON_ONLY')=='1':
  report['scope']='python-full'
  for file,args,name in (SUITES[:1] if os.environ.get('TYR_BROADCAST_FOCUS_ONLY')=='1' else SUITES):
   p=subprocess.run([sys.executable,'-B',str(R/'scripts'/file),*args],capture_output=True,text=True,timeout=1200);(E/(name+'.log')).write_text(p.stdout+p.stderr);check('tests.'+name,p.returncode==0)
  report['passed']=True;save();return
 import server,record_mappings as rm,mapping_templates as mt
 from playwright.sync_api import sync_playwright,expect
 registry=E/'registry';st=server.Store(E/'editor.sqlite3');st.migrate(0,{});st.save(1,server.contracts.load(R/'fixtures/broadcast/before.json'))
 with sqlite3.connect('file:/input/seed.sqlite3?mode=ro',uri=True) as src,sqlite3.connect(E/'legacy.sqlite3') as dst:src.backup(dst)
 old=server.Store(E/'legacy.sqlite3')
 with old.connect() as c:dump=list(c.iterdump())
 old.read()
 with old.connect() as c:check('sqlite.legacy-read-no-migration',dump==list(c.iterdump()))
 http=server.make_server(st,0,JAR,registry);th=threading.Thread(target=http.serve_forever,daemon=True);th.start();origin='http://127.0.0.1:'+str(http.server_port);errors=[];requests=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(60000);page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url));page.on('dialog',lambda d:d.accept() if d.type in ('beforeunload','confirm') else d.dismiss());page.goto(origin);page.locator('#counts strong').first.wait_for();page.locator('[data-tab="broadcast"]').click();page.locator('[data-broadcast-revision="2"]').wait_for()
  check('browser.source-families-and-explicit-policies','공통 PLC' in page.locator('#bc-members').inner_text() and page.locator('#bc-row-policy').input_value()=='reject-all')
  page.locator('#bc-schema').select_option('pressure-records@1.0.0');page.locator('#bc-model').select_option('combined-model@1.0.0');page.locator('#bc-equipment').select_option('record-line-b')
  for i,v in enumerate(['common:mixed-plc-pressure@1.0.0','field:target','common:mixed-baseline@1.0.0','common:mixed-external-reference@1.0.0','common:mixed-line-code@1.0.0']):page.locator('#bc-input-'+str(i)).select_option(v)
  for i in [0,1]:page.locator('#bc-factor-'+str(i)).fill('0.1')
  page.locator('#bc-author').fill('operator');page.locator('#bc-reason').fill('Synthetic broadcast review');page.locator('#bc-note').fill('Common virtual values applied once to every row');before=st.read()
  def compare():
   with page.expect_response(lambda r:r.url.endswith('/api/broadcast-compose')) as rr:page.locator('#bc-compare').click()
   assert rr.value.status==200,rr.value.text();return rr.value.json()
  p=compare();check('browser.plan-readonly-pins-and-template',p['valid'] and len(p['draft']['record']['commonSources'])==4 and st.read()==before)
  page.locator('#bc-label').fill('Reviewed virtual object array');check('browser.changed-input-invalidates-plan',page.locator('#bc-save').is_disabled());p=compare();headers={'Content-Type':'application/json','X-Tyr-Editor':'1'};bad=page.request.post(origin+'/api/record-apply',data=json.dumps(dict(revision=2,draft=p['draft'],planSha256='0'*64)),headers=headers);check('http.plan-tamper-no-save',bad.status==422 and st.read()==before)
  with page.expect_response(lambda r:r.url.endswith('/api/record-apply')) as rr:page.locator('#bc-save').click()
  check('browser.atomic-definition-template-save',rr.value.status==200 and rr.value.json()['saved']['revision']==3);page.locator('[data-broadcast-revision="3"]').wait_for();check('browser.one-editor-per-common-input',page.locator('#bc-common textarea').count()==2)
  def inputs():
   snap=server.contracts.load(R/'fixtures/broadcast/snapshot.json');page.locator('#bc-snapshot').fill(json.dumps(snap));src=page.evaluate('bcInputs().map(s=>s.id)')
   for i,id in enumerate(src):page.locator('#bc-value-'+str(i)).fill(json.dumps({'bytesHex':'b004'} if id=='mixed-plc-pressure' else {'typedValue':'101'}))
   return snap,src
  snap,src=inputs()
  def preview():
   with page.expect_response(lambda r:r.url.endswith('/api/broadcast-preview')) as rr:page.locator('#bc-preview').click()
   assert rr.value.status==200,rr.value.text();return rr.value.json()
  before=st.read();p=preview();expected=[dict(actual='120',target='90',baseline='100',external='101',line_code='LINE-A'),dict(actual='120',target='95',baseline='100',external='101',line_code='LINE-A')];check('browser.row-specific-and-shared-value-oracle',p['result']==expected and p['quality']=='good' and st.read()==before);check('browser.trace-provenance-and-identity',all(row['members'] for row in p['records']) and p['records'][0]['identity']['key']==['A-001']);page.locator('#bc-result').screenshot(path=str(E/'broadcast-preview.png'))
  page.locator('#bc-missing-0').check();p=preview();check('browser.common-missing-blocks-array',p['result'] is None and any(i['code']=='sample.missing' for i in p['issues']));page.locator('#bc-missing-0').uncheck()
  page.locator('#bc-row-table').click();check('browser.record-table-preserves-unmapped-column',page.locator('[data-bc-cell]').count()==len(snap['rows'])*len(st.read()['workspace']['recordMappings'][-1]['resultSchema']['fields']));page.locator('[data-bc-cell="0,2"]').fill('951');p=preview();check('browser.table-edit-cast-loss-visible',p['quality']=='uncertain' and any(m['preview']['losses'] for row in p['records'] for m in row['members']));snap,src=inputs()
  for i,id in enumerate(src):page.locator('#bc-value-'+str(i)).fill('b004' if id=='mixed-plc-pressure' else '101')
  p=preview();check('browser.plain-HEX-and-numeric-input',p['result']==expected)
  with page.expect_response(lambda r:r.url.endswith('/api/broadcast-scenarios')) as rr:page.locator('#bc-scene-save').click()
  check('browser.scenario-SQLite-save-without-workspace-change',rr.value.status==200 and st.read()==before);scene=rr.value.json();request=dict(revision=3,id=scene['id'],scenarioRevision=0,mappingRef=scene['mappingRef'],snapshot=scene['snapshot'],commonSamples=scene['commonSamples'],evaluatedAt=scene['evaluatedAt']);bad=page.request.post(origin+'/api/broadcast-scenarios',data=json.dumps(request),headers=headers);check('http.scenario-CAS',bad.status==409)
  broken=copy.deepcopy(snap);broken['rows'][0]['target']='oops';page.locator('#bc-snapshot').fill(json.dumps(broken));p=preview();check('browser.reject-all-retains-row-diagnostics',p['result'] is None and len(p['omittedRecords'])==1 and len(p['partialResults'])==1)
  broken=copy.deepcopy(snap);broken['rows'].append(copy.deepcopy(snap['rows'][0]));page.locator('#bc-snapshot').fill(json.dumps(broken));p=preview();check('browser.duplicate-key-global-error',p['result'] is None and any(i['code']=='record.duplicate-key' for i in p['issues']))
  page.locator('#bc-snapshot').fill(json.dumps(snap));pi=src.index('mixed-plc-pressure');page.locator('#bc-quality-'+str(pi)).select_option('bad');p=preview();check('browser.common-bad-quality-blocks-array',p['result'] is None);page.locator('#bc-quality-'+str(pi)).select_option('good');page.locator('#bc-evaluated').fill('2026-10-18T00:00:02Z');p=preview();check('browser.stale-common-frame-blocks-array',p['result'] is None and any(i['code']=='time.stale-input' for i in p['issues']))
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="broadcast"]').click();page.locator('[data-broadcast-revision="3"]').wait_for();page.locator('#bc-scene').select_option('broadcast-scene');p=preview();check('browser.reopen-and-scene-replay',p['result']==expected)
  page.locator('[data-bc-edit="0"]').click();page.locator('#bc-row-policy').select_option('omit-invalid');page.locator('#bc-reason').fill('Explicit row omission policy');p=compare();check('browser.explicit-version-update-reuses-pinned-template',p['draft']['template'] is None and p['draft']['record']['previousMappingRef']['id']=='operator-broadcast')
  with page.expect_response(lambda r:r.url.endswith('/api/record-apply')) as rr:page.locator('#bc-save').click()
  check('browser.new-array-version-atomic-save',rr.value.status==200);page.locator('[data-broadcast-revision="4"]').wait_for();page.locator('#bc-preview-map').select_option('operator-broadcast@1.0.1');snap,src=inputs();broken=copy.deepcopy(snap);broken['rows'][0]['target']='oops';page.locator('#bc-snapshot').fill(json.dumps(broken));p=preview();check('browser.omit-invalid-explicit-and-uncertain',p['valid'] and len(p['result'])==1 and p['quality']=='uncertain' and p['omittedRecords'][0]['key']==['A-002'])
  page.locator('#bc-preview-map').select_option('operator-broadcast@1.0.0');page.locator('#bc-scene').select_option('broadcast-scene');expect(page.locator('#message')).to_contain_text(' 이전 정의'.strip());check('browser.stale-scene-not-silently-replayed',st.read()['revision']==4)
  page.locator('[data-tab="records"]').click();page.locator('[data-record-revision="4"]').wait_for();check('browser.old-record-editor-unchanged',page.locator('[data-rec-edit]').count()==2)
  page.locator('[data-tab="templates"]').click();page.locator('[data-template-revision="4"]').wait_for();check('browser.template-impact-includes-array-users','operator-broadcast' in page.locator('#view').inner_text())
  if os.environ.get('TYR_BROADCAST_BROWSER_ONLY')=='1':
   check('browser.no-js-errors',not errors,errors=errors);check('browser.localhost-only',all(u.startswith(origin) for u in requests));page.screenshot(path=str(E/'broadcast-draft.png'));browser.close();http.shutdown();http.server_close();th.join();report['passed']=True;report['scope']='browser-draft-only-no-Java';save();return
  page.locator('[data-tab="publication"]').click();page.locator('#submission-id').fill('broadcast-offline');page.locator('#submission-stream').fill('broadcast-line');page.locator('#submission-by').fill('proposer');page.locator('#submission-mapping').select_option(['record:operator-broadcast@1.0.1'])
  with page.expect_response(lambda r:r.url.endswith('/api/submissions') and r.request.method=='POST') as rr:page.locator('#submission-form button[type="submit"]').click()
  assert rr.value.status==200,rr.value.text();sub=rr.value.json();check('browser.Bifrost-submission-closure',sub['preflightFindings']==[]);bundle=Path(sub['path']);check('java.independent-broadcast-validation',java('mapping','validate',bundle)['accepted']);proposal=server.contracts.load(bundle/'proposal.json');check('wire.no-virtual-values-or-writes',proposal['schemaVersion']=='2.22.0' and not any(e['kind'] in ('virtual-result-set','broadcast-scenario','write-definition') for e in proposal['files']))
  with tempfile.TemporaryDirectory(prefix='broadcast-private-') as kd:
   keys=Path(kd);identity=registry/'identity';identity.mkdir(parents=True,exist_ok=True);public=[java('identity','keygen',who,'--out',keys) for who in ['proposer','approver']];(identity/'authorized-keys.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in public));(identity/'activation-policy.json').write_text(json.dumps({'version':'1.0.0','default':'deny','rules':[{'id':action,'principal':who,'action':action,'target':'mapping-publication','kind':'mapping-release','ref':'broadcast-line'} for action,who in [('publish','proposer'),('approve','approver')]]}));check('java.real-two-key-approval',java('mapping','approve',registry,bundle,'broadcast-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key').get('kind')=='mapping-approval');rel=java('mapping','publish',registry,bundle,'broadcast-release','1.0.0','--approval','broadcast-approval');check('java.immutable-release-no-activation',rel.get('kind')=='mapping-release' and rel['activation']=='not-performed')
  with page.expect_response(lambda r:r.url.endswith('/api/submission-refresh')) as rr:page.locator('[data-submission-refresh="broadcast-offline"]').click()
  check('browser.release-status',rr.value.json()['publicationState']=='published');page.screenshot(path=str(E/'broadcast-publication.png'));check('security.private-keys-excluded',not list(E.rglob('*.key')));check('browser.no-js-errors',not errors,errors=errors);check('browser.localhost-only',all(u.startswith(origin) for u in requests),requestCount=len(requests));browser.close()
 http.shutdown();http.server_close();th.join();report['passed']=True;report['scope']='ui-python-sqlite-java-integration';save()
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();save();raise
 finally:
  with tarfile.open('/evidence/runtime-evidence.tar','w') as t:t.add(E,arcname='.')
