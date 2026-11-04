"""Imported Vor read bindings: profile 0.1.0 bytes from data-edge commissioning, shipped as an ordinary evidence-artifact.

Tyr does not author the profile. The bytes are kept exactly as imported (Vor and Bifrost hash them); only the artifact
wrapper is Tyr's. Reconciliation against the workspace runs on the built package (command_binding.validate).
"""
import base64,binascii,hashlib
from jsonschema import Draft202012Validator,FormatChecker
import validate_contracts as vc
import command_binding as cb
LIMIT=64*1024
VALIDATOR=Draft202012Validator(vc.load(vc.ROOT/'editor-contracts/1.0.0/read-binding-import.schema.json'),format_checker=FormatChecker())
def require(ok,code):
    if not ok:raise ValueError(code)
def raw(r):
    try:return base64.b64decode(r['bytesBase64'],validate=True)
    except (binascii.Error,ValueError) as e:raise ValueError('read-binding.bytes') from e
def check(w,equipment):
    docs=w.get('readBindings',[])
    require(isinstance(docs,list) and len(docs)<=256,'read-binding.limit')
    ids=set()
    for r in docs:
        require(not list(VALIDATOR.iter_errors(r)),'read-binding.schema')
        require(r['id'] not in ids,'read-binding.duplicate');ids.add(r['id'])
        b=raw(r);require(len(b)<=LIMIT,'read-binding.limit')
        require(hashlib.sha256(b).hexdigest()==r['sha256'],'read-binding.digest')
        require(cb.profile(b,'read-binding.profile')['equipmentInstanceId'] in equipment,'read-binding.equipment')
def transition(before,after):
    new={r['id']:r for r in after.get('readBindings',[])}
    for r in before.get('readBindings',[]):
        n=new.get(r['id'])
        if n is not None and n!=r:require(n['version']!=r['version'],'read-binding.version-required')
def build(w,folder,proposal):
    docs=w.get('readBindings',[])
    if not docs:return
    (folder/'data').mkdir(exist_ok=True);(folder/'evidence').mkdir(exist_ok=True)
    for i,r in enumerate(docs):
        b=raw(r);path='data/read-binding-'+str(i)+'.json';(folder/path).write_bytes(b)
        art={'kind':'evidence-artifact','schemaVersion':'1.1.0','id':cb.PREFIX+r['id'],'version':r['version'],'origin':r['origin'],'file':{'path':path,'sha256':r['sha256'],'mediaType':'application/json'},'capturedAt':r['capturedAt'],'product':r['product'],'scope':[cb.profile(b)['equipmentInstanceId']]}
        rel='evidence/read-binding-'+str(i)+'.json';vc.save(folder/rel,art)
        proposal['files'].append({'path':rel,'kind':art['kind'],'id':art['id'],'version':art['version'],'sha256':vc.hashed(folder/rel)})
