"""Read-only evaluation acceptance under an isolated localhost-only browser/Python runtime."""
import hashlib,json,os,shutil,sqlite3,subprocess,sys,tarfile,threading,traceback
from pathlib import Path
E=Path('/work/evidence');E.mkdir(parents=True,exist_ok=True);R=Path('/work/tyr')
report={'passed':False,'checks':[],'fieldPoV':'not-performed','deviceCommunication':'excluded','externalSQL':'excluded','writeExecution':'excluded'}
def save():(E/'p7eval-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def check(id,ok,**details):
 print(id,bool(ok),flush=True);report['checks'].append(dict(id=id,passed=bool(ok),**details));save();assert ok,(id,details)
def main():
 with tarfile.open('/input/package.tar') as t:t.extractall('/work',filter='data')
 os.chdir(R);sys.path[:0]=[str(R/'scripts'),str(R/'backend')]
 report['inputSha256']={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for n in ['scripts','backend','frontend','contracts','evaluation-contracts','fixtures'] for p in (R/n).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 report['jarSha256']=hashlib.sha256((R.parent/'bifrost/gates/target/bifrost-gates.jar').read_bytes()).hexdigest();save()
 import server,pov_evaluation as pe
 from playwright.sync_api import sync_playwright,expect
 store=server.Store(E/'editor.sqlite3');store.migrate(0,{});w=server.contracts.load(R/'fixtures/p3eb/workspace.json');store.save(1,w)
 before=store.read()
 def dump():
  with store.connect() as c:return list(c.iterdump())
 before_rows=dump();http=server.make_server(store,0);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();origin='http://127.0.0.1:'+str(http.server_port)
 pack=server.contracts.load(R/'fixtures/p7-evaluation/oracle.json');errors=[];requests=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1400,'height':1050});page.set_default_timeout(90000)
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda req:requests.append(req.url));page.on('dialog',lambda d:d.accept() if d.type=='beforeunload' else d.dismiss())
  page.goto(origin);page.locator('#counts strong').first.wait_for();page.locator('[data-tab="pov"]').click();check('browser.evaluation-view',page.locator('#pov-pack').is_visible())
  page.locator('#pov-scope').select_option(pack['mappingSetIds'])
  with page.expect_response(lambda r:r.url.endswith('/api/pov-template')) as tr:page.locator('#pov-template').click()
  t=tr.value.json();check('browser.blank-oracle-template',tr.value.status==200 and all(c['expected'] is None for c in t['pack']['cases']) and not t['expectedValuesGenerated'])
  expect(page.locator('#pov-pack')).to_have_value(__import__('re').compile('.*review-required.*',__import__('re').DOTALL))
  with page.expect_response(lambda r:r.url.endswith('/api/pov-evaluate')) as rr:page.locator('#pov-evaluate').click()
  blank=rr.value.json();check('browser.unreviewed-not-pass',blank['metrics']['evaluation']['counts']['unreviewed']==40 and blank['metrics']['evaluation']['verifiedPercent']=='0.00')
  page.locator('#pov-file').set_input_files(str(R/'fixtures/p7-evaluation/oracle.json'));expect(page.locator('#pov-pack')).to_have_value((R/'fixtures/p7-evaluation/oracle.json').read_text(encoding='utf-8'))
  with page.expect_response(lambda r:r.url.endswith('/api/pov-evaluate')) as rr:page.locator('#pov-evaluate').click()
  result=rr.value.json();check('browser.independent-fixture-evaluation',rr.value.status==200 and [result['metrics'][s]['counts']['verified-fixture'] for s in pe.SPLITS]==[10,20,10])
  expect(page.locator('#pov-summary')).to_contain_text('synthetic-only');check('browser.synthetic-scope-visible','현장 PoV 미인증' in page.locator('#pov-summary').inner_text())
  check('browser.full-path-identity-visible',page.locator('#pov-cases tbody tr').count()==40 and 'modules[1].pressure.actual' in page.locator('#pov-cases').inner_text())
  check('browser.full-time-denominator',result['metrics']['evaluation']['time']['manualSeconds']==1000 and result['metrics']['evaluation']['time']['toolSeconds']==800 and result['metrics']['evaluation']['time']['savingPercent']=='20.00')
  check('browser.unmeasured-heldout-time',result['metrics']['heldout']['time']['savingPercent'] is None)
  with page.expect_download() as dl:page.locator('#pov-download').click()
  path=E/'downloaded-report.json';dl.value.save_as(path);downloaded=json.loads(path.read_text());pin=downloaded.pop('reportSha256');check('browser.report-download-pin',pe.sq.digest(downloaded)==pin)
  check('sqlite.all-existing-tables-unchanged',dump()==before_rows and store.read()==before and server.Store(store.path).read()==before)
  page.locator('#pov-summary').scroll_into_view_if_needed();page.screenshot(path=str(E/'p7eval-summary.png'))
  pack['cases'][10]['samples'][0]['expected']['result']['value']='999';page.locator('#pov-pack').fill(json.dumps(pack));check('browser.edit-invalidates-report',page.locator('#pov-download').is_disabled())
  with page.expect_response(lambda r:r.url.endswith('/api/pov-evaluate')) as rr:page.locator('#pov-evaluate').click()
  check('browser.wrong-value-detected',rr.value.json()['cases'][10]['status']=='sample-mismatch')
  page.locator('#pov-pack').fill('{}')
  with page.expect_response(lambda r:r.url.endswith('/api/pov-evaluate')) as rr:page.locator('#pov-evaluate').click()
  check('browser.invalid-pack-refused',rr.value.status==422)
  stale=page.request.post(origin+'/api/pov-evaluate',data=json.dumps({'revision':1,'pack':pack}),headers={'Content-Type':'application/json','X-Tyr-Editor':'1'});check('http.stale-revision-refused',stale.status==409)
  check('browser.no-errors-or-outbound',not errors and all(u.startswith(origin) or u.startswith('blob:'+origin) for u in requests),errors=errors)
  browser.close()
 http.shutdown();http.server_close();thread.join()
 # Existing seed DB copied from the previous acceptance; inspect/additive initialization cannot rewrite rows.
 shutil.copyfile('/input/seed.sqlite3',E/'legacy.sqlite3')
 with sqlite3.connect(E/'legacy.sqlite3') as c:old=list(c.iterdump())
 server.Store(E/'legacy.sqlite3')
 with sqlite3.connect(E/'legacy.sqlite3') as c:check('sqlite.existing-db-open-preserves-rows',old==list(c.iterdump()))
 for mode,args in [('template',['--template']),('evaluate',['--pack',str(R/'fixtures/p7-evaluation/oracle.json')])]:
  out=E/('cli-'+mode+'.json');proc=subprocess.run([sys.executable,'-B',str(R/'scripts/pov_evaluation.py'),str(R/'fixtures/p3eb/workspace.json'),*args,'--out',str(out)],capture_output=True,text=True,timeout=120);(E/('cli-'+mode+'.log')).write_text(proc.stdout+proc.stderr);v=json.loads(out.read_text()) if out.exists() else {};check('cli.'+mode,proc.returncode==0 and (all(c['expected'] is None for c in v['cases']) if mode=='template' else v['metrics']['evaluation']['counts']['verified-fixture']==20))
 suites=[('test_p7_evaluation.py',[],'evaluation-tests'),('test_p6_recovery.py',[],'recovery-regression'),('test_p4ab.py',[],'import-regression'),('test_p3fb.py',[],'graph-regression'),('test_p3eb.py',[],'structure-regression'),('test_p3cb.py',[],'math-regression'),('test_a07.py',['--report',str(E/'a07.json')],'a07'),('test_p7.py',['--report',str(E/'regression.json')],'baseline')]
 if os.environ.get('TYR_P7EVAL_UI_ONLY')=='1':suites=[]
 report['regressionScope']='full' if suites else 'separate-full-run'
 for file,args,name in suites:
  proc=subprocess.run([sys.executable,'-B',str(R/'scripts'/file),*args],capture_output=True,text=True,timeout=1200);(E/(name+'.log')).write_text(proc.stdout+proc.stderr);check('tests.'+name,proc.returncode==0)
 report['passed']=True;save()
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();save();raise
 finally:
  with tarfile.open('/evidence/runtime-evidence.tar','w') as t:t.add(E,arcname='.')
