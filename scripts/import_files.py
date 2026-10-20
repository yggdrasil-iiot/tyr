
"""File-only, bounded import. No evaluation, macros, external resources or device clients."""
import base64,copy,hashlib,io,json,posixpath,re,zipfile
from datetime import datetime
from xml.etree import ElementTree as ET
import validate_contracts as vc
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def integer(v):
 if isinstance(v,bool) or not re.fullmatch(r'[0-9]{1,10}',str(v)) or int(v)>2147483647:raise ValueError('parameter.integer-range')
 return int(v)
def xlsx(raw):
 z=zipfile.ZipFile(io.BytesIO(raw));infos=z.infolist()
 if len(infos)>64 or len({i.filename for i in infos})!=len(infos) or sum(i.file_size for i in infos)>4194304:raise ValueError('xlsx.limit')
 def xml(n):
  b=z.read(n)
  if b'<!DOCTYPE' in b.upper() or b'<!ENTITY' in b.upper():raise ValueError('xlsx.entity')
  return ET.fromstring(b)
 for i in infos:
  if i.flag_bits&1 or i.filename.startswith('/') or '..' in i.filename.split('/') or '\\' in i.filename or i.filename.endswith('.bin'):raise ValueError('xlsx.unsafe-part')
  if i.filename.endswith('.rels') and any(r.get('TargetMode')=='External' for r in xml(i.filename)):raise ValueError('xlsx.external')
 shared=[''.join(n.itertext()) for n in xml('xl/sharedStrings.xml').findall('s:si',NS)] if 'xl/sharedStrings.xml' in z.namelist() else []
 rel={r.get('Id'):r.get('Target') for r in xml('xl/_rels/workbook.xml.rels')};rows=[];cells={};sheet_names=set()
 for sh in xml('xl/workbook.xml').findall('s:sheets/s:sheet',NS):
  target=rel[sh.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
  path=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
  if not path.startswith('xl/worksheets/'):raise ValueError('xlsx.sheet-path')
  name=sh.get('name');header=None
  if name in sheet_names:raise ValueError('xlsx.duplicate-sheet')
  sheet_names.add(name)
  for row in xml(path).findall('s:sheetData/s:row',NS):
   values={};formula=False;addresses=[]
   for c in row.findall('s:c',NS):
    addr=c.get('r')
    if not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,5}',addr or ''):raise ValueError('xlsx.cell')
    col=re.match('[A-Z]+',addr)[0];v=c.find('s:v',NS);text=v.text if v is not None else ''
    if c.get('t')=='s':text=shared[integer(text)]
    elif c.get('t')=='inlineStr':text=''.join(c.find('s:is',NS).itertext())
    f=c.find('s:f',NS)
    if (name,addr) in cells:raise ValueError('xlsx.duplicate-cell')
    cells[(name,addr)]={'value':text,'formula':f.text if f is not None else None};values[col]=text;formula|=f is not None;addresses.append(addr)
   if not values:continue
   if header is None:
    if formula:raise ValueError('xlsx.header-formula')
    header=values
    if len(set(header.values()))!=len(header):raise ValueError('xlsx.duplicate-header')
    continue
   r={header.get(k,'column-'+k):v for k,v in values.items()}
   if formula:r['_formula']=True
   rows.append((r,{'kind':'xlsx-cell','sheet':name,'cell':addresses[0]}))
   if len(rows)>256:raise ValueError('import.row-limit')
 return rows,cells
def records(raw,fmt):
 if fmt=='xlsx':return xlsx(raw)[0]
 if fmt!='tyr-config-json-v1':raise ValueError('import.format')
 d=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=vc.pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('json.nonfinite')))
 if not isinstance(d,dict) or d.get('format')!='tyr-config-v1' or not isinstance(d.get('records'),list):raise ValueError('config.format')
 if len(d['records'])>256:raise ValueError('import.row-limit')
 out=[(r,{'kind':'json-pointer','pointer':'/records/'+str(i)}) for i,r in enumerate(d['records'])]
 for k,v in d.items():
  if k not in ('format','records'):out.append(({'kind':'opaque','field':k,'value':v},{'kind':'json-pointer','pointer':'/'+k.replace('~','~0').replace('/','~1')}))
 return out
KEYS=('id','filename','format','bytesBase64','equipmentInstanceId','capturedAt','origin','columnMap')
ALLOWED={'id','kind','profile','address','type','unit','stage','byteOrder','wordOrder','width','namespaceUri','identifierType','base','stride','count','overrides','target','label'}
def parse(q,state):
 if not isinstance(q,dict) or set(q)!=set(KEYS):raise ValueError('import.request-fields')
 if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}',q['id']):raise ValueError('import.id')
 if not isinstance(q['filename'],str) or not 1<=len(q['filename'])<=200 or any(c in q['filename'] for c in '/\\'):raise ValueError('import.filename')
 if q['origin'] not in ('field','synthetic'):raise ValueError('import.origin')
 dt=datetime.fromisoformat(q['capturedAt'].replace('Z','+00:00'))
 if dt.tzinfo is None:raise ValueError('import.timestamp')
 raw=base64.b64decode(q['bytesBase64'],validate=True)
 if not 1<=len(raw)<=524288:raise ValueError('import.file-limit')
 if q['equipmentInstanceId'] not in {e['id'] for e in state['equipment']}:raise ValueError('import.equipment')
 if not isinstance(q['columnMap'],dict) or len(q['columnMap'])>64 or any(not isinstance(k,str) or v not in ALLOWED for k,v in q['columnMap'].items()) or len(set(q['columnMap'].values()))!=len(q['columnMap']):raise ValueError('import.column-map')
 b=copy.deepcopy(q);b['contextConnections']=copy.deepcopy([c for c in state['connections'] if c['equipmentInstanceId']==q['equipmentInstanceId']]);b.update(kind='import-batch',schemaVersion='2.6.0',version='1.0.0',parser={'name':'tyr-bounded-files','version':'1.0.0'},sha256=hashlib.sha256(raw).hexdigest(),observations=[])
 try:rs=records(raw,q['format'])
 except (ValueError,KeyError,IndexError,TypeError,ET.ParseError,zipfile.BadZipFile,UnicodeError,RuntimeError,NotImplementedError,RecursionError,OverflowError) as e:rs=[];b['fileIssue']=str(e)
 original={}
 if q['format']=='xlsx':
  normalized=[]
  for row,loc in rs:
   original[json.dumps(loc,sort_keys=True)]=copy.deepcopy(row)
   mapped={q['columnMap'].get(k,k):v for k,v in row.items()}
   if len(mapped)!=len(row):mapped['_columnConflict']=True
   normalized.append((mapped,loc))
  rs=normalized
 entries={}
 def add(r,loc,issue=None,template=None):
  o={'id':'row-'+str(len(b['observations'])),'raw':copy.deepcopy(r),'locator':loc,'derivation':[loc],'issues':[] if issue is None else [issue],'assumptions':[],'draft':None}
  if q['format']=='xlsx':o['originalColumns']=original.get(json.dumps(loc,sort_keys=True),{})
  if template is not None:o['template']=copy.deepcopy(template)
  b['observations'].append(o)
  if not isinstance(r,dict):o['issues'].append('record.object');return
  id=r.get('id')
  if not isinstance(id,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,47}',id):o['issues'].append('record.id');return
  if id in entries:entries[id]['issues'].append('record.duplicate-id');o['issues'].append('record.duplicate-id');return
  entries[id]=o
 for r,loc in rs:
  if isinstance(r,dict) and r.get('kind')=='template':
   try:
    base,stride,count=map(integer,(r['base'],r['stride'],r['count']))
    if not 1<=count<=64:raise ValueError('template.count')
    ov=r.get('overrides',{})
    if isinstance(ov,str):ov=json.loads(ov or '{}')
    if not isinstance(ov,dict) or any(not re.fullmatch('[0-9]+',k) or int(k)>=count for k in ov):raise ValueError('template.override')
    expanded=[]
    for i in range(count):
     x=copy.deepcopy(r);x.update(kind='source',id=r['id']+'-'+str(i))
     for k in ('base','stride','count','overrides'):x.pop(k,None)
     offset=base+stride*i
     if offset>2147483647:raise ValueError('template.offset')
     x['address']=x['address'].replace('{index}',str(i)).replace('{offset}',str(offset))
     if '{' in x['address'] or '}' in x['address']:raise ValueError('template.parameter')
     change=ov.get(str(i),{})
     if not isinstance(change,dict) or not set(change)<={'address','label','unit','type','stage','byteOrder','wordOrder','width'}:raise ValueError('template.override')
     x.update(change);expanded.append(x)
    for x in expanded:add(x,loc,template=r)
   except (ValueError,KeyError,TypeError) as e:add(r,loc,issue=str(e))
  else:add(r,loc)
  if len(b['observations'])>256:raise ValueError('import.expansion-limit')
 preissues={id:list(o['issues']) for id,o in entries.items()}
 def resolve(id,active):
  o=entries.get(id)
  if o is None:raise ValueError('alias.missing-target')
  if id in active:raise ValueError('alias.cycle')
  if len(active)>=64:raise ValueError('alias.depth')
  if preissues[id]:raise ValueError('record.unresolved')
  r=o['raw']
  if r.get('_formula'):raise ValueError('xlsx.formula')
  if set(r)-ALLOWED:raise ValueError('record.unknown-fields')
  if r.get('kind','source') not in ('source','alias'):raise ValueError('record.unsupported-kind')
  if r.get('kind','source')=='alias':
   t,chain=resolve(r.get('target'),active+[id]);return {**t,'id':id,'label':r.get('label',id)},[o['locator']]+chain
  return r,[o['locator']]
 for id,o in entries.items():
  try:
   r,chain=resolve(id,[]);orig=o['raw']
   if orig.get('_formula'):raise ValueError('xlsx.formula')
   if set(orig)-ALLOWED:raise ValueError('record.unknown-fields')
   if orig.get('kind','source') not in ('source','alias'):raise ValueError('record.unsupported-kind')
   o['derivation']=chain
   con=[c for c in state['connections'] if c['equipmentInstanceId']==q['equipmentInstanceId'] and c['accessProfileRef']==r['profile']]
   if len(con)!=1:raise ValueError('connection.missing-or-ambiguous')
   profile=r['profile'];typ=r.get('type') or None;address=r['address'];kind=vc.PROFILES[profile];width=vc.WIDTH.get(typ)
   if kind=='symbol':
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.\[\]]*',address):raise ValueError('address.symbol')
    a={'kind':kind,'symbolPath':address}
   elif kind=='opcua-node':
    it=r.get('identifierType') or 'string';a={'kind':kind,'namespaceUri':r.get('namespaceUri') or None,'identifierType':it,'identifier':integer(address) if it=='numeric' else address}
   elif kind=='db-offset':
    m=re.fullmatch(r'DB([0-9]+)\.DBB([0-9]+)',address)
    if not m:raise ValueError('address.db')
    a={'kind':kind,'dbNumber':integer(m[1]),'byteOffset':integer(m[2]),'byteLength':integer(r['width']) if r.get('width') else width,'bitOffset':None}
   else:
    m=re.fullmatch(r'([A-Z]+)([0-9]+)',address)
    if not m:raise ValueError('address.register')
    a={'kind':kind,'deviceArea':m[1],'addressIndex':integer(m[2]),'addressUnit':'word16','wordCount':integer(r['width']) if r.get('width') else ((width+1)//2 if width else None),'bitOffset':None}
   rawrep={'mode':'typed','valueType':typ} if kind in ('symbol','opcua-node') else {'mode':'bytes','valueType':typ,'byteOrder':r.get('byteOrder') or None,'wordOrder':r.get('wordOrder') or None}
   d={'kind':'source-definition','schemaVersion':'2.2.0','id':'imp-'+q['id']+'-'+id,'version':'1.0.0','equipmentInstanceId':q['equipmentInstanceId'],'connectionProfileRef':con[0]['id'],'accessProfileRef':profile,'status':'draft','rawAddressText':address,'addressRadix':10 if kind=='device-register' else None,'access':a,'rawRepresentation':rawrep,'inputStage':r.get('stage') or 'raw','unit':{'status':'known','code':r['unit']} if r.get('unit') else {'status':'unknown'},'evidenceRefs':[{'artifactId':'import-'+q['id'],'locator':l} for l in chain],'viewOf':None}
   if vc.validate_schema('source-definition',d):raise ValueError('source.schema')
   proposed=copy.deepcopy(d);proposed['status']='ready'
   o['issues']+=vc.source_rules(proposed)
   if not r.get('stage'):o['issues'].append('source.stage-unconfirmed');o['assumptions'].append('inputStage=raw for draft only')
   if not r.get('unit'):o['issues'].append('source.unit-unconfirmed')
   if kind in ('db-offset','device-register') and not r.get('width'):o['assumptions'].append('storage width derived from declared type')
   o['draft']=d
  except (ValueError,KeyError,TypeError) as e:o['issues'].append(str(e))
 return b
def request_of(b):return {k:b[k] for k in KEYS}
def projection(state):
 s=copy.deepcopy(state);s.pop('imports',None);s.pop('writes',None)
 for r in s['sources']:
  if r.pop('importRef',None):r['definition']['evidenceRefs']=[{'artifactId':'manual-'+r['definition']['id'],'locator':{'kind':'text-line','line':1}}]
 return s
def check(state):
 batches=state.get('imports',[])
 if not isinstance(batches,list) or len(batches)>16:raise ValueError('imports.limit')
 if len(json.dumps(state,ensure_ascii=False).encode())>1900000:raise ValueError('workspace.import-size-limit')
 ids=set();obs={}
 for b in batches:
  if b.get('schemaVersion') not in ('2.6.0','2.14.0') or list(vc.schema_validator('import-batch',b['schemaVersion']).iter_errors(b)):raise ValueError('import.schema')
  if b['id'] in ids:raise ValueError('import.duplicate-id')
  ids.add(b['id'])
  context={'equipment':[{'id':b['equipmentInstanceId']}],'connections':b['contextConnections']}
  original=copy.deepcopy(b)
  if b['schemaVersion']=='2.14.0':
   import import_workflow as workflow
   for field in ('reviews','adoptions','reconciliation'):original.pop(field)
   original['schemaVersion']='2.6.0'
   workflow.check(b,batches)
  replay=parse(request_of(b),context)
  if (workflow.digest(replay)!=workflow.digest(original) if b['schemaVersion']=='2.14.0' else replay!=original):raise ValueError('import.provenance-mismatch')
  for o in b['observations']:
   effective=copy.deepcopy(o)
   if b['schemaVersion']=='2.14.0':
    import import_workflow as workflow
    effective['draft']=workflow.materialize(b,o)
   obs[(b['id'],o['id'])]=effective
 for r in state['sources']:
  if 'importRef' not in r:continue
  ref=r['importRef']
  if not isinstance(ref,dict) or set(ref)!={'batchId','observationId'}:raise ValueError('import.reference')
  o=obs.get((ref['batchId'],ref['observationId']))
  if not o or o['draft'] is None:raise ValueError('import.unresolved-adoption')
  if r['definition']['status']=='ready' and (vc.source_rules(r['definition']) or r['definition']['unit']['status']=='unknown'):raise ValueError('import.unreviewed-issues')
  if r['definition']['id']!=o['draft']['id'] or r['definition']['evidenceRefs']!=[{'artifactId':'manual-'+r['definition']['id'],'locator':{'kind':'text-line','line':1}}]+o['draft']['evidenceRefs']:raise ValueError('import.evidence-mismatch')
def adopt(state,b,selected):
 out=copy.deepcopy(state)
 if any(x['id']==b['id'] for x in out.get('imports',[])):raise ValueError('import.duplicate-id')
 if not isinstance(selected,list) or len(selected)!=len(set(selected)):raise ValueError('import.selection')
 obs={o['id']:o for o in b['observations']}
 if any(id not in obs or obs[id]['draft'] is None for id in selected):raise ValueError('import.unresolved-adoption')
 out.setdefault('imports',[]).append(b)
 for id in selected:
  o=obs[id];d=copy.deepcopy(o['draft']);d['evidenceRefs'].insert(0,{'artifactId':'manual-'+d['id'],'locator':{'kind':'text-line','line':1}})
  out['sources'].append({'definition':d,'label':o['raw'].get('label') or d['id'],'note':'Imported draft. Review decoding assumptions. SHA256 '+b['sha256'],'origin':b['origin'],'capturedAt':b['capturedAt'],'importRef':{'batchId':b['id'],'observationId':id}})
 return out
def build(state,folder,p):
 for bi,b in enumerate(state.get('imports',[])):
  raw=base64.b64decode(b['bytesBase64'],validate=True);path='data/import-'+str(bi)+('.xlsx' if b['format']=='xlsx' else '.json');(folder/path).write_bytes(raw)
  art={'kind':'evidence-artifact','schemaVersion':'1.1.0','id':'import-'+b['id'],'version':'1.0.0','origin':b['origin'],'file':{'path':path,'sha256':b['sha256'],'mediaType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if b['format']=='xlsx' else 'application/json'},'capturedAt':b['capturedAt'],'product':None,'scope':[b['equipmentInstanceId']]}
  p['schemaVersion']='2.6.0'
  docs=[('evidence/import-'+str(bi)+'.json',art),('evidence/import-batch-'+str(bi)+'.json',b)]
  for i,o in enumerate(b['observations']):
   obs={'kind':'source-observation','schemaVersion':'1.1.0','id':'import-'+b['id']+'-'+o['id'],'version':'1.0.0','evidenceRefs':[{'artifactId':art['id'],'locator':l} for l in o['derivation']],'extractor':b['parser'],'claims':[{'field':'raw','value':o['raw'],'certainty':'explicit'},{'field':'derivation','value':o,'certainty':'inferred'}],'status':'partial' if o['draft'] else 'unsupported'}
   docs.append(('evidence/observation-'+str(bi)+'-'+str(i)+'.json',obs))
  for path,d in docs:
   vc.save(folder/path,d);p['files'].append({'path':path,'kind':d['kind'],'id':d['id'],'version':d['version'],'sha256':vc.hashed(folder/path)})
 for i,r in enumerate(state['sources']):
  if 'importRef' in r:
   path='sources/'+str(i)+'.json';vc.save(folder/path,r['definition']);next(e for e in p['files'] if e['path']==path)['sha256']=vc.hashed(folder/path)
