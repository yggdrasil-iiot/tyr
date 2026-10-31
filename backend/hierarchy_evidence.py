"""Editor-side hierarchy evidence: a reviewer note or a plant register, shipped as an ordinary evidence-artifact.

The bytes are kept as the reviewer wrote or the plant exported them; only the artifact wrapper is Tyr's.
"""
import base64,binascii,hashlib
from jsonschema import Draft202012Validator,FormatChecker
import validate_contracts as vc
import import_files
PREFIX='hierarchy-'
LIMIT=1024*1024
MEDIA={'text':'text/plain','csv':'text/csv','xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
EXT={'text':'.txt','csv':'.csv','xlsx':'.xlsx'}
VALIDATOR=Draft202012Validator(vc.load(vc.ROOT/'editor-contracts/1.0.0/hierarchy-evidence.schema.json'),format_checker=FormatChecker())
def require(ok,code):
    if not ok:raise ValueError(code)
def raw(r):
    try:return base64.b64decode(r['bytesBase64'],validate=True)
    except (binascii.Error,ValueError) as e:raise ValueError('hierarchy-evidence.bytes') from e
def check(w,equipment):
    docs=w.get('hierarchyEvidence',[])
    require(isinstance(docs,list) and len(docs)<=64,'hierarchy-evidence.limit')
    ids=set()
    for r in docs:
        require(not list(VALIDATOR.iter_errors(r)),'hierarchy-evidence.schema')
        require(r['id'] not in ids,'hierarchy-evidence.duplicate');ids.add(r['id'])
        b=raw(r);require(len(b)<=LIMIT,'hierarchy-evidence.limit')
        require(hashlib.sha256(b).hexdigest()==r['sha256'],'hierarchy-evidence.digest')
        if r['format']=='xlsx':
            try:import_files.xlsx(b)
            except Exception as e:raise ValueError('hierarchy-evidence.xlsx') from e
        else:
            try:b.decode('utf-8')
            except UnicodeDecodeError as e:raise ValueError('hierarchy-evidence.encoding') from e
        require(set(r['scope'])<=set(equipment),'hierarchy-evidence.scope')
def transition(before,after):
    new={r['id']:r for r in after.get('hierarchyEvidence',[])}
    for r in before.get('hierarchyEvidence',[]):
        n=new.get(r['id'])
        if n is not None and n!=r:require(n['version']!=r['version'],'hierarchy-evidence.version-required')
def build(w,folder,proposal):
    docs=w.get('hierarchyEvidence',[])
    if not docs:return
    (folder/'data').mkdir(exist_ok=True);(folder/'evidence').mkdir(exist_ok=True)
    for i,r in enumerate(docs):
        path='data/hierarchy-'+str(i)+EXT[r['format']];(folder/path).write_bytes(raw(r))
        art={'kind':'evidence-artifact','schemaVersion':'1.1.0','id':PREFIX+r['id'],'version':r['version'],'origin':r['origin'],'file':{'path':path,'sha256':r['sha256'],'mediaType':MEDIA[r['format']]},'capturedAt':r['capturedAt'],'product':r['product'],'scope':list(r['scope'])}
        rel='evidence/hierarchy-'+str(i)+'.json';vc.save(folder/rel,art)
        proposal['files'].append({'path':rel,'kind':art['kind'],'id':art['id'],'version':art['version'],'sha256':vc.hashed(folder/rel)})
