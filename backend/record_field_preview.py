"""Resolve a virtual result-set field before the existing source/graph pipeline."""
import copy,json
import record_fields as rf,record_mappings as rm,record_preview as rp,mapping_templates as mt

def resolve(w,s,sample):
 rf.validate([s]+rm.workspace_docs(w));rm.require(isinstance(sample,dict) and set(sample)=={'resultSet'},'record-field.snapshot-required');snap=sample['resultSet'];rm.schema('virtual-result-set',snap);b=s['recordField'];r=next(r for r in w['recordMappings'] if rm.pin(r)==b['recordMappingRef']);rm.require(snap['resultSetRef']==rm.pin(r['resultSchema']),'record-field.snapshot-pin');rm.timestamp(snap['capturedAt']);rm.require(snap['quality']!='bad','record-field.bad-quality');fs=rm.fields(r);keys=set();selected=[];preserved=[]
 for index,row in enumerate(snap['rows']):
  for f in fs.values():
   v=row.get(f['fieldId']);rm.require(v is not None or f['nullable'],'record-field.required-field')
   if v is not None:rp.cell(f,v)
  key=[row.get(k) for k in r['resultSchema']['keyFields']];rm.require(all(isinstance(k,str) and 0<len(k)<=256 for k in key),'record-field.key-value');token=mt.digest(key);rm.require(token not in keys,'record-field.duplicate-key');keys.add(token);extras={k:v for k,v in row.items() if k not in fs};rm.require(not extras or r['resultSchema']['unknownFields']=='preserve','record-field.unknown-fields')
  if extras:preserved.append(dict(inputRowIndex=index,fields=extras))
  if r['selection']['kind']=='all' or key==r['selection']['key']:selected.append((key,row,index))
 rm.require(len(selected)==1,'record-field.zero-rows' if not selected else 'record-field.many-rows');key,row,index=selected[0];value=row.get(b['fieldId']);default=value is None
 if default:rm.require(b['nullPolicy']=='default','record-field.null-input');value=b['defaultValue']
 rp.cell(fs[b['fieldId']],value)
 return dict(typedValue=value),dict(recordMappingRef=b['recordMappingRef'],fieldId=b['fieldId'],recordKey=key,inputRowIndex=index,resultSetRef=snap['resultSetRef'],inputSha256=mt.digest(snap),capturedAt=snap['capturedAt'],quality=snap['quality'],defaultUsed=default,rawValue=row.get(b['fieldId']),preservedFields=preserved,atomicSnapshot=False)
