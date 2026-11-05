"""Imported OPC UA server certificates: the DER a command link's endpointRef names, shipped as an evidence-artifact.

Tyr does not issue or edit the certificate. The DER is kept exactly as imported (Bifrost and Heimdall compare these
bytes); only the artifact wrapper and the declared scope are Tyr's. The thumbprint and the subjectAltName URI are
derived here for review; the link's own copies are checked against the DER on the built package (command_binding).
"""
import base64,binascii,hashlib
from jsonschema import Draft202012Validator,FormatChecker
import validate_contracts as vc
import server_certificate as sc
LIMIT=16*1024
VALIDATOR=Draft202012Validator(vc.load(vc.ROOT/'editor-contracts/1.0.0/server-certificate-import.schema.json'),format_checker=FormatChecker())
def require(ok,code):
    if not ok:raise ValueError(code)
def raw(r):
    try:return base64.b64decode(r['bytesBase64'],validate=True)
    except (binascii.Error,ValueError) as e:raise ValueError('server-certificate.bytes') from e
def derive(der):
    """(thumbprintSha1, applicationUri) for review, with Tyr's refusal codes."""
    try:return sc.parse(der)
    except ValueError as e:raise ValueError('server-certificate.'+('san-uri' if str(e)=='san-uri' else 'der')) from e
def imported(req):
    """The import step: a DER or PEM file in, the DER and what the reviewer approves out. Nothing is stored here."""
    require(isinstance(req,dict) and set(req)=={'bytesBase64'} and isinstance(req['bytesBase64'],str),'server-certificate.import-request')
    try:b=base64.b64decode(req['bytesBase64'],validate=True)
    except (binascii.Error,ValueError) as e:raise ValueError('server-certificate.bytes') from e
    require(len(b)<=4*LIMIT,'server-certificate.limit')
    try:der=sc.der(b)
    except ValueError as e:raise ValueError('server-certificate.der') from e
    require(len(der)<=LIMIT,'server-certificate.limit');t,u=derive(der)
    return {'bytesBase64':base64.b64encode(der).decode(),'sha256':hashlib.sha256(der).hexdigest(),'thumbprintSha1':t,'applicationUri':u}
def check(w,equipment):
    docs=w.get('serverCertificates',[])
    require(isinstance(docs,list) and len(docs)<=256,'server-certificate.limit')
    ids=set()
    for r in docs:
        require(not list(VALIDATOR.iter_errors(r)),'server-certificate.schema')
        require(r['id'] not in ids,'server-certificate.duplicate');ids.add(r['id'])
        b=raw(r);require(len(b)<=LIMIT,'server-certificate.limit')
        require(hashlib.sha256(b).hexdigest()==r['sha256'],'server-certificate.digest')
        derive(b);require(set(r['scope'])<=set(equipment),'server-certificate.equipment')
def transition(before,after):
    new={r['id']:r for r in after.get('serverCertificates',[])}
    for r in before.get('serverCertificates',[]):
        n=new.get(r['id'])
        if n is not None and n!=r:require(n['version']!=r['version'],'server-certificate.version-required')
def build(w,folder,proposal):
    docs=w.get('serverCertificates',[])
    if not docs:return
    (folder/'data').mkdir(exist_ok=True);(folder/'evidence').mkdir(exist_ok=True)
    for i,r in enumerate(docs):
        path='data/server-certificate-'+str(i)+'.der';(folder/path).write_bytes(raw(r))
        art={'kind':'evidence-artifact','schemaVersion':'1.1.0','id':sc.PREFIX+r['id'],'version':r['version'],'origin':r['origin'],'file':{'path':path,'sha256':r['sha256'],'mediaType':sc.MEDIA},'capturedAt':r['capturedAt'],'product':r['product'],'scope':list(r['scope'])}
        rel='evidence/server-certificate-'+str(i)+'.json';vc.save(folder/rel,art)
        proposal['files'].append({'path':rel,'kind':art['kind'],'id':art['id'],'version':art['version'],'sha256':vc.hashed(folder/rel)})
