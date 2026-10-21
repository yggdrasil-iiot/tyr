"""Pinned cross-graph scalar dependencies. No IO, dynamic lookup or graph flattening."""
class GraphError(ValueError):pass

def order(graphs):
 graphs=list(graphs)
 if not any(e['kind']=='graph' for g in graphs for n in g['nodes'] for e in n['inputs'].values()):return graphs
 by={(g['id'],g['version']):g for g in graphs};deps={k:set() for k in by};heights={};out=[];done=set();depths={}
 if sum(len(g['nodes']) for g in graphs)>8192:raise GraphError('graph.dependency-size')
 for key,g in by.items():
  for n in g['nodes']:
   for e in n['inputs'].values():
    if e['kind']!='graph':continue
    if g['schemaVersion']!='2.17.0':raise GraphError('graph.endpoint-version')
    target=(e['graphRef']['id'],e['graphRef']['version']);other=by.get(target)
    if other is None:raise GraphError('reference.missing')
    if other['equipmentInstanceId']!=g['equipmentInstanceId']:raise GraphError('value.equipment')
    ns=[v for v in other['nodes'] if v['nodeId']==e['nodeId']]
    if len(ns)!=1:raise GraphError('graph.node-missing')
    if ns[0]['valueType']=='FixedArray':raise GraphError('graph.reference-scalar-required')
    deps[key].add(target)
 pending=set(by)
 while pending:
  ready=sorted(k for k in pending if deps[k]<=done)
  if not ready:raise GraphError('graph.dependency-cycle')
  for key in ready:
   depths[key]=1+max((depths[k] for k in deps[key]),default=0)
   if depths[key]>32:raise GraphError('graph.dependency-depth')
   g=by[key];nodes={n['nodeId']:n for n in g['nodes']};local=set(nodes);finished=set()
   while local:
    nr=sorted(id for id in local if all(e['kind']!='node' or e['nodeId'] in finished for e in nodes[id]['inputs'].values()))
    if not nr:raise GraphError('graph.cycle' if all(e['kind']!='node' or e['nodeId'] in nodes for n in nodes.values() for e in n['inputs'].values()) else 'graph.node-missing')
    for id in nr:
     levels=[]
     for e in nodes[id]['inputs'].values():
      if e['kind']=='node':levels.append(heights[(*key,e['nodeId'])])
      elif e['kind']=='graph':levels.append(heights[(e['graphRef']['id'],e['graphRef']['version'],e['nodeId'])])
     heights[(*key,id)]=1+max(levels,default=0)
     if heights[(*key,id)]>128:raise GraphError('graph.path-depth')
     finished.add(id);local.remove(id)
   out.append(g);done.add(key);pending.remove(key)
 return out

def source_refs(graphs,graph_ref,node_id):
 by={(g['id'],g['version']):g for g in graphs};pending=[(False,(graph_ref['id'],graph_ref['version'],node_id))];done=set();active=set();refs=set()
 while pending:
  exiting,key=pending.pop()
  if exiting:active.remove(key);done.add(key);continue
  if key in active:raise GraphError('graph.cycle')
  if key in done:continue
  if len(done)+len(active)>=8192:raise GraphError('graph.dependency-size')
  g=by.get(key[:2])
  if g is None:raise GraphError('reference.missing')
  matches=[n for n in g['nodes'] if n['nodeId']==key[2]]
  if len(matches)!=1:raise GraphError('graph.node-missing')
  active.add(key);pending.append((True,key))
  for e in matches[0]['inputs'].values():
   if e['kind']=='source':refs.add((e['sourceRef']['id'],e['sourceRef']['version']))
   elif e['kind']=='node':pending.append((False,(*key[:2],e['nodeId'])))
   else:pending.append((False,(e['graphRef']['id'],e['graphRef']['version'],e['nodeId'])))
 return sorted(refs)
