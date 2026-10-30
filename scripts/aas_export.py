"""Semantic definition -> AAS v3.1 ConceptDescriptions, written beside the definition, never into a bundle or proposal.

One ConceptDescription per distinct semanticId, with an IEC 61360 data specification for what the standard
has fields for (name, definition, data type, unit) and Tyr extensions for the rest (valueType, unit status,
role, range, structure). A second file is an unsigned in-toto/SLSA provenance statement that pins the raw
input bytes and the exporter; it records where the export came from and approves nothing.

usage: python scripts/aas_export.py <semantic-definition.json> --language en --out <dir>
"""
import argparse,hashlib,json,sys
from importlib.metadata import version as package_version
from pathlib import Path
import p3a_contracts as p3a
import validate_contracts as vc
from aas_core3_1 import jsonization,types as T,verification

AAS_CORE='1.0.0'
IEC61360='https://admin-shell.io/DataSpecificationTemplates/DataSpecificationIEC61360/3/0'
ENVIRONMENT='aas-environment.json'
PROVENANCE='aas-environment.provenance.json'
# Only numeric types with a known unit map to a measure; without a unit AASc-3a-009 forbids it and a count would be a guess.
DATA_TYPES={'Boolean':T.DataTypeIEC61360.BOOLEAN,'String':T.DataTypeIEC61360.STRING}
MEASURES={'Double':T.DataTypeIEC61360.REAL_MEASURE,'Int32':T.DataTypeIEC61360.INTEGER_MEASURE}

class Refused(ValueError):pass
def require(ok,code):
    if not ok:raise Refused(code)

def walk(members):
    for m in members:
        yield m
        yield from walk(m.get('members',()))

def extension(name,value,value_type=T.DataTypeDefXSD.STRING):return T.Extension(name=name,value_type=value_type,value=value)

def concept(m,language):
    """The ConceptDescription for one member. Two members with one semanticId must project to the same one."""
    kind=m['valueType'];iec=dict(preferred_name=[T.LangStringPreferredNameTypeIEC61360(language,m['name'])],
                               definition=[T.LangStringDefinitionTypeIEC61360(language,m['description'])])
    ext=[extension('tyr:valueType',kind)]
    if 'members' in m:
        ext.append(extension('tyr:members',json.dumps([c['semanticId'] for c in m['members']])))
        if kind=='StructureArray':ext+=[extension('tyr:shape',json.dumps(m['shape'])),extension('tyr:lowerBounds',json.dumps(m['lowerBounds']))]
    else:
        unit=m['unit'];ext.append(extension('tyr:unitStatus',unit['status']))
        if unit['status']=='known':iec.update(unit=unit['code'],data_type=MEASURES.get(kind,DATA_TYPES.get(kind)))
        else:iec.update(data_type=DATA_TYPES.get(kind))
        ext.append(extension('tyr:role',m['role']))
        if m['range'] is not None:ext+=[extension('tyr:range.low',m['range']['low'],T.DataTypeDefXSD.DECIMAL),extension('tyr:range.high',m['range']['high'],T.DataTypeDefXSD.DECIMAL)]
    spec=T.EmbeddedDataSpecification(T.Reference(T.ReferenceTypes.EXTERNAL_REFERENCE,[T.Key(T.KeyTypes.GLOBAL_REFERENCE,IEC61360)]),T.DataSpecificationIEC61360(**iec))
    return T.ConceptDescription(id=m['semanticId'],extensions=ext,embedded_data_specifications=[spec])

def environment(doc,language):
    require(not p3a.schema_errors('semantic-definition',doc),'aas.input-schema')
    require(not list(verification.verify_bcp_47_language_tag(language)),'aas.language-invalid')
    # AASc-002 and AASc-3a-008: IEC 61360 needs the preferred name and definition in English. The tag says what
    # language Tyr's name/description text is in; it is stated, not detected, so anything but English is refused.
    require(verification.is_bcp_47_for_english(language),'aas.language-not-english')
    seen={}
    for m in walk(doc['members']):
        cd=jsonization.to_jsonable(concept(m,language))
        require(seen.setdefault(m['semanticId'],cd)==cd,'aas.semantic-conflict:'+m['semanticId'])
    env=jsonization.environment_from_jsonable({'conceptDescriptions':list(seen.values())})
    errors=list(verification.verify(env))
    require(not errors,'aas.verify:'+'; '.join(f'{e.path}: {e.cause}' for e in errors[:3]))
    return env

def text(value):return json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n'

def export(source,language):
    """Return {file name: text}. Reads the raw bytes once so the provenance digest is of exactly what was parsed."""
    require(package_version('aas-core3.1')==AAS_CORE,'aas.sdk-version')
    raw=Path(source).read_bytes()
    try:doc=json.loads(raw.decode('utf-8'),object_pairs_hook=vc.pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
    except (UnicodeDecodeError,ValueError):raise Refused('aas.input-unreadable')
    require(isinstance(doc,dict) and doc.get('kind')=='semantic-definition','aas.input-kind')
    env_text=text(jsonization.to_jsonable(environment(doc,language)))
    require(jsonization.to_jsonable(jsonization.environment_from_jsonable(json.loads(env_text)))==json.loads(env_text),'aas.round-trip')
    statement={'_type':'https://in-toto.io/Statement/v1',
               'subject':[{'name':ENVIRONMENT,'digest':{'sha256':hashlib.sha256(env_text.encode('utf-8')).hexdigest()}}],
               'predicateType':'https://slsa.dev/provenance/v1',
               'predicate':{'buildDefinition':{'buildType':'urn:tyr:aas-export:v1','externalParameters':{'language':language},
                                               'resolvedDependencies':[{'name':Path(source).name,'digest':{'sha256':hashlib.sha256(raw).hexdigest()},
                                                                        'annotations':{k:doc[k] for k in ('kind','schemaVersion','id','version')}}]},
                            'runDetails':{'builder':{'id':'urn:tyr:aas-export','version':{'aas-core3.1':AAS_CORE,'IDTA-01001':'3.1','IDTA-01003-a':'3.1'}}}}}
    return {ENVIRONMENT:env_text,PROVENANCE:text(statement)}

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--language',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:files=export(a.source,a.language)
    except Refused as e:
        print('refused: '+str(e),file=sys.stderr);return 3
    except OSError:
        print('refused: aas.input-unreadable',file=sys.stderr);return 3
    a.out.mkdir(parents=True,exist_ok=True)
    for name,body in files.items():(a.out/name).write_text(body,encoding='utf-8',newline='\n')
    print(json.dumps({'written':sorted(files),'conceptDescriptions':len(json.loads(files[ENVIRONMENT]).get('conceptDescriptions',[]))}))
    return 0

if __name__=='__main__':sys.exit(main())
