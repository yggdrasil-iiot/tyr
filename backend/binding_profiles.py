"""Authored forseti binding profiles: occupancy-binding and incident-binding 0.1.0, shipped as evidence-artifact 1.1.0 files.

Unlike read bindings and server certificates, these bytes are Tyr's own output: the workspace record holds the profile object,
vc.save writes it as the artifact's data file, and the wrapper pins the SHA-256 of those bytes. Bifrost re-reads the file with its
own parser (OccupancyBindingProfile, IncidentBindingProfile); Tyr's parsers run on the same bytes here and at package validation.
scope lists the stations the profile covers, as equipment instance ids (spec "Binding profiles"); Bifrost does not compare it
with a rule's stations, Tyr requires it to name workspace equipment.
"""
import json
from jsonschema import Draft202012Validator,FormatChecker
import validate_contracts as vc
import attribution_rule as ar
import impact_rule as ir
SECTIONS={'occupancyBindings':('occupancy-binding',ar.PREFIX,ar.MEDIA,ar.occupancy_profile,'attribution.binding-profile'),
          'incidentBindings':('incident-binding',ir.PREFIX,ir.MEDIA,ir.incident_profile,'impact.binding-profile')}
VALIDATORS={k:Draft202012Validator(vc.load(vc.ROOT/'editor-contracts/1.0.0'/(v[0]+'.schema.json')),format_checker=FormatChecker()) for k,v in SECTIONS.items()}
LIMIT=64
def require(ok,code):
    if not ok:raise ValueError(code)
def bytes_of(r):
    """The data file bytes: what vc.save writes (indent 2, ensure_ascii False, LF, final newline)."""
    return (json.dumps(r['profile'],ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def check(w,equipment):
    for section,(name,prefix,media,parse,code) in SECTIONS.items():
        docs=w.get(section,[])
        require(isinstance(docs,list) and len(docs)<=LIMIT,name+'.limit')
        ids=set()
        for r in docs:
            require(not list(VALIDATORS[section].iter_errors(r)),name+'.schema')
            require(r['id'] not in ids,name+'.duplicate');ids.add(r['id'])
            parse(bytes_of(r),code)   # the spec's code, as Bifrost will report it on the same bytes
            require(set(r['scope'])<=set(equipment),name+'.scope')
def transition(before,after):
    for section,(name,*_) in SECTIONS.items():
        new={r['id']:r for r in after.get(section,[])}
        for r in before.get(section,[]):
            n=new.get(r['id'])
            if n is not None and n!=r:require(n['version']!=r['version'],name+'.version-required')
def build(w,folder,proposal):
    for section,(name,prefix,media,parse,code) in SECTIONS.items():
        docs=w.get(section,[])
        if not docs:continue
        (folder/'data').mkdir(exist_ok=True);(folder/'evidence').mkdir(exist_ok=True)
        for i,r in enumerate(docs):
            path='data/'+name+'-'+str(i)+'.json';vc.save(folder/path,r['profile'])
            art={'kind':'evidence-artifact','schemaVersion':'1.1.0','id':prefix+r['id'],'version':r['version'],'origin':r['origin'],'file':{'path':path,'sha256':vc.hashed(folder/path),'mediaType':media},'capturedAt':r['capturedAt'],'product':r['product'],'scope':list(r['scope'])}
            rel='evidence/'+name+'-'+str(i)+'.json';vc.save(folder/rel,art)
            proposal['files'].append({'path':rel,'kind':art['kind'],'id':art['id'],'version':art['version'],'sha256':vc.hashed(folder/rel)})
