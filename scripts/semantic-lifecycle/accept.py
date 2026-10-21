"""Network-none browser, SQLite, CLI and Python lifecycle acceptance."""
import copy,hashlib,json,os,shutil,sqlite3,subprocess,sys,tarfile,tempfile,threading,traceback
from pathlib import Path
E=Path('/work/evidence');E.mkdir(parents=True,exist_ok=True);R=Path('/work/tyr');report={'passed':False,'checks':[],'fieldPoV':'not-performed','deviceCommunication':'excluded','externalSQL':'excluded','writeExecution':'excluded'}
def save():(E/'lifecycle-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def check(id,ok,**details):
 print(id,bool(ok),flush=True);report['checks'].append(dict(id=id,passed=bool(ok),**details));save();assert ok,(id,details)
def java(*args):
 p=subprocess.run(['java','-jar',str(JAR),*map(str,args)],capture_output=True,text=True,timeout=120);assert p.returncode in (0,1),p.stderr
 v=json.loads(p.stdout);(E/('java-%02d.json'%len(list(E.glob('java-*.json'))))).write_text(json.dumps(v,indent=2));return v
SUITES=[('test_semantic_lifecycle.py',[],'lifecycle-tests'),('test_cross_graph.py',[],'reuse-tests'),('test_expression_literals.py',[],'literal-tests'),('test_expression.py',[],'expression-tests'),('test_semantic_catalog.py',[],'catalog-tests'),('test_p3cc.py',[],'arithmetic-tests'),('test_p7_evaluation.py',[],'evaluation-regression'),('test_p6_recovery.py',[],'recovery-regression'),('test_p4ab.py',[],'import-regression'),('test_p3fb.py',[],'graph-regression'),('test_p3eb.py',[],'structure-regression'),('test_p3cb.py',[],'math-regression'),('test_a07.py',['--report',str(E/'a07.json')],'a07'),('test_p7.py',['--report',str(E/'regression.json')],'baseline')]

def main():
 with tarfile.open('/input/package.tar') as t:t.extractall('/work',filter='data')
 os.chdir(R);sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
 report['inputSha256']={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for n in ['scripts','backend','frontend','contracts','evaluation-contracts','editor-contracts','fixtures'] for p in (R/n).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 global JAR;JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar';report['jarSha256']=hashlib.sha256(JAR.read_bytes()).hexdigest();save()
 report['driverSha256']=hashlib.sha256(Path('/input/accept.py').read_bytes()).hexdigest();check('input.driver-matches-archive',report['driverSha256']==report['inputSha256']['scripts/semantic-lifecycle/accept.py'])
 import server,lifecycle_authoring,semantic_lifecycle as lc
 if os.environ.get('TYR_CROSS_PYTHON_ONLY')=='1' or os.environ.get('TYR_LIFECYCLE_BASELINE_ONLY')=='1':
  report['scope']='python-baseline-and-lifecycle' if os.environ.get('TYR_LIFECYCLE_BASELINE_ONLY')=='1' else 'python-full'
  for file,args,name in (SUITES if os.environ.get('TYR_LIFECYCLE_BASELINE_ONLY')!='1' else [s for s in SUITES if s[2] in ('lifecycle-tests','baseline')]):
   proc=subprocess.run([sys.executable,'-B',str(R/'scripts'/file),*args],capture_output=True,text=True,timeout=1200);(E/(name+'.log')).write_text(proc.stdout+proc.stderr);check('tests.'+name,proc.returncode==0)
  report['passed']=True;save();return
 from playwright.sync_api import sync_playwright,expect
 registry=E/'registry';store=server.Store(E/'editor.sqlite3');store.migrate(0,{});w=server.contracts.load(R/'fixtures/semantic-lifecycle/workspace.json');store.save(1,w);uri=w['semanticLifecycles'][0]['semanticId']
 with sqlite3.connect('file:/input/seed.sqlite3?mode=ro',uri=True) as src,sqlite3.connect(E/'legacy.sqlite3') as dst:src.backup(dst)
 legacy=server.Store(E/'legacy.sqlite3')
 with legacy.connect() as db:oldrows=list(db.iterdump())
 legacy.read()
 with legacy.connect() as db:check('sqlite.old-rows-and-schema-preserved',oldrows==list(db.iterdump()))
 http=server.make_server(store,0,JAR,registry);th=threading.Thread(target=http.serve_forever,daemon=True);th.start();origin='http://127.0.0.1:'+str(http.server_port);errors=[];requests=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1400,'height':1050});page.set_default_timeout(90000);page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url));page.on('dialog',lambda d:d.accept() if d.type=='beforeunload' else d.dismiss())
  page.goto(origin);page.locator('#counts strong').first.wait_for();page.locator('[data-tab="lifecycle"]').click();page.locator('#lifecycle-uri').wait_for();page.locator('#lifecycle-uri').select_option(uri);expect(page.locator('#lifecycle-details')).to_contain_text('deprecated');check('browser.local-history-and-impacts-visible',True)
  page.locator('#lifecycle-author').fill('offline-author');page.locator('#lifecycle-label').fill('압력 의미 개정 · offline');page.locator('#lifecycle-description').fill('Synthetic URI metadata revision');page.locator('#lifecycle-reason').fill('오프라인 URI 개정 검토')
  with page.expect_response(lambda r:r.url.endswith('/api/semantic-lifecycle-apply')) as response:page.locator('#lifecycle-form button[type="submit"]').click()
  check('browser.revision-atomic-save',response.value.status==200 and response.value.json()['saved']['revision']==3);page.locator('#lifecycle-uri').wait_for();check('sqlite.append-and-reopen',len(server.Store(store.path).read()['workspace']['semanticLifecycles'])==3)
  page.reload();page.locator('#counts strong').first.wait_for();page.locator('[data-tab="lifecycle"]').click();expect(page.locator('#lifecycle-details')).to_contain_text('압력 의미 개정 · offline');check('browser.history-roundtrip',True)
  before=store.read();r=page.request.post(origin+'/api/semantic-lifecycle-apply',data=json.dumps(dict(revision=2,semanticId=uri,action='revise',replacementSemanticId=None,label='Stale',description='',reason='Stale',authoredBy='offline-author')),headers={'Content-Type':'application/json','X-Tyr-Editor':'1'});check('http.stale-CAS-no-mutation',r.status==409 and store.read()==before)
  page.locator('[data-tab="publication"]').click();page.locator('#submission-id').fill('lifecycle-offline');page.locator('#submission-stream').fill('mixed-line');page.locator('#submission-by').fill('proposer');page.locator('#submission-mapping').select_option([w['mappings'][0]['id']])
  with page.expect_response(lambda r:r.url.endswith('/api/submissions') and r.request.method=='POST') as response:page.locator('#submission-form button[type="submit"]').click()
  record=response.value.json();check('browser.submission-closure',response.value.status==200 and record['preflightFindings']==[]);bundle=Path(record['path']);p=server.contracts.load(bundle/'proposal.json');check('wire.full-chain-and-new-version',p['schemaVersion']=='2.18.0' and sum(e['kind']=='semantic-lifecycle' for e in p['files'])==3);check('java.independent-wire-validation',java('mapping','validate',bundle)['accepted'])
  old_receiver=subprocess.run(['java','-jar','/work/old-bifrost-gates.jar','mapping','validate',str(bundle)],capture_output=True,text=True,timeout=120);old_result=json.loads(old_receiver.stdout);check('java.old-receiver-fails-closed',old_receiver.returncode==1 and not old_result.get('accepted',True))
  with tempfile.TemporaryDirectory(prefix='lifecycle-private-') as kd:
   keys=Path(kd);identity=registry/'identity';identity.mkdir(parents=True,exist_ok=True);public=[java('identity','keygen',who,'--out',keys) for who in ['proposer','approver']];(identity/'authorized-keys.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in public));policy={'version':'1.0.0','default':'deny','rules':[{'id':action,'principal':who,'action':action,'target':'mapping-publication','kind':'mapping-release','ref':'mixed-line'} for action,who in [('publish','proposer'),('approve','approver')]]};(identity/'activation-policy.json').write_text(json.dumps(policy))
   approved=java('mapping','approve',registry,bundle,'lifecycle-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key');check('java.signed-approval',approved.get('kind')=='mapping-approval' and 'semantic-lifecycle' in json.dumps(approved['changeAssessment']))
   released=java('mapping','publish',registry,bundle,'lifecycle-release','1.0.0','--approval','lifecycle-approval');check('java.file-release-without-activation',released.get('kind')=='mapping-release' and released['activation']=='not-performed')
   with page.expect_response(lambda r:r.url.endswith('/api/submission-refresh')) as refreshed:page.locator('[data-submission-refresh="lifecycle-offline"]').click()
   check('browser.published-status',refreshed.value.json()['publicationState']=='published')
   page.locator('[data-tab="lifecycle"]').click();expect(page.locator('#lifecycle-details')).to_contain_text('발행본 deprecated / r3');check('browser.verified-history-current-head-impacts',True)
   page.locator('#lifecycle-uri').select_option(uri);page.locator('#lifecycle-action').select_option('retire');page.locator('#lifecycle-author').fill('offline-author');page.locator('#lifecycle-reason').fill('Retirement simulation')
   with page.expect_response(lambda r:r.url.endswith('/api/semantic-lifecycle-apply')) as ret:page.locator('#lifecycle-form button[type="submit"]').click()
   check('browser.retirement-draft-keeps-affected-bindings',ret.value.status==200 and any(f['ruleCode']=='lifecycle.retired-binding' for f in ret.value.json()['saved']['findings']))
   page.locator('#revision').filter(has_text='저장 revision '+str(ret.value.json()['saved']['revision'])).wait_for()
   page.locator('#lifecycle-uri').wait_for() # Wait for the async verified-history redraw before navigating.
   # Governance-only release does not require unrelated mapping sets; historical mapping evidence remains.
   page.locator('[data-tab="publication"]').click();page.locator('#submission-id').fill('retirement-offline');page.locator('#submission-stream').fill('mixed-line');page.locator('#submission-by').fill('proposer')
   with page.expect_response(lambda r:r.url.endswith('/api/submissions') and r.request.method=='POST') as ret:page.locator('#submission-form button[type="submit"]').click()
   retirement=ret.value.json();check('browser.governance-only-submission',ret.value.status==200 and retirement['preflightFindings']==[]);rb=Path(retirement['path']);check('java.retirement-only-validation',java('mapping','validate',rb)['accepted'])
   approved=java('mapping','approve',registry,rb,'retire-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key');check('java.retirement-approval',approved.get('kind')=='mapping-approval');released=java('mapping','publish',registry,rb,'retirement-release','1.0.0','--approval','retire-approval');check('java.retirement-release',released.get('kind')=='mapping-release')
   page.locator('[data-tab="lifecycle"]').click();expect(page.locator('#lifecycle-details')).to_contain_text('발행본 retired / r4');page.locator('#lifecycle-details article').filter(has=page.get_by_role('heading',name=uri,exact=True)).evaluate('(e)=>e.scrollIntoView({block:"start"})');page.screenshot(path=str(E/'lifecycle-history.png'));check('browser.retirement-history-and-historical-impact',True)
   # A valid old bundle must be refused using registry lifecycle even if it omits all lifecycle records.
   legacy_bundle=E/'legacy-republication';old=copy.deepcopy(w);old.pop('semanticLifecycles');server.publication.build(old,legacy_bundle,'legacy-submission','legacy-line','proposer',None,[m['id'] for m in old['mappings']],False,server.build_package)
   policy['rules'] += [dict(id=action+'-legacy',principal=who,action=action,target='mapping-publication',kind='mapping-release',ref='legacy-line') for action,who in [('publish','proposer'),('approve','approver')]];(identity/'activation-policy.json').write_text(json.dumps(policy));refused=java('mapping','approve',registry,legacy_bundle,'legacy-approval','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key');check('java.legacy-omission-cannot-bypass-retirement','retired-binding' in refused.get('error',''))
  check('identity.private-keys-not-in-evidence',not list(E.rglob('*.key')))
  catalog_a=java('mapping','lifecycle',registry);catalog_b=java('mapping','lifecycle',registry);check('report.stable-cross-process-digest',catalog_a==catalog_b)
  before=store.read();r=page.request.get(origin+'/api/semantic-lifecycle');check('report.readonly',r.status==200 and store.read()==before and len(r.json()['published']['eventReleases'])==7);check('browser.no-javascript-errors',not errors,errors=errors);check('browser.localhost-only',all(u.startswith(origin) for u in requests),requests=requests)
  browser.close()
 http.shutdown();http.server_close();th.join();report['scope']='ui-and-focused'
 proc=subprocess.run([sys.executable,'-B',str(R/'scripts/test_semantic_lifecycle.py')],capture_output=True,text=True,timeout=1200);(E/'lifecycle-tests.log').write_text(proc.stdout+proc.stderr);check('tests.lifecycle',proc.returncode==0)
 report['passed']=True;save()
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();save();raise
 finally:
  with tarfile.open('/evidence/runtime-evidence.tar','w') as t:t.add(E,arcname='.')
