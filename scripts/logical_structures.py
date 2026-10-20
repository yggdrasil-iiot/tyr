"""Bounded canonical logical structures; no vendor memory layout or device IO."""
import copy,itertools,json,math,re
CONTAINERS={"Structure","StructureArray"}
class StructureError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def path_key(path):
    if len(path)==1 and path[0].get("kind")=="member":return path[0]["memberId"]
    return json.dumps(path,sort_keys=True,separators=(",",":"),ensure_ascii=True)
def label(path):
    out=""
    for x in path:
        if x["kind"]=="index":out+="["+",".join(map(str,x["indices"]))+"]"
        elif re.fullmatch(r"[a-z][a-z0-9_-]*",x["memberId"]):out+=("." if out else "")+x["memberId"]
        else:out+="["+json.dumps(x["memberId"],ensure_ascii=False)+"]"
    return out
def preflight(model):
    pending=[(model.get("members",[]),1)];count=0
    while pending:
        nodes,depth=pending.pop()
        if depth>8:raise StructureError("structure.depth")
        if not isinstance(nodes,list):continue
        for n in nodes:
            count+=1
            if count>256:raise StructureError("structure.size")
            if isinstance(n,dict) and "members" in n:pending.append((n["members"],depth+1))
def layout(model):
    if model.get("schemaVersion")!="2.12.0":
        ids=[m["memberId"] for m in model["members"]]
        if len(ids)!=len(set(ids)):raise StructureError("semantic.duplicate")
        return {"leaves":{m["memberId"]:{"member":m,"memberPath":[{"kind":"member","memberId":m["memberId"]}],"label":m["memberId"]} for m in model["members"]},"definitions":model["members"],"arrays":[]}
    preflight(model)
    leaves={};definitions=[];arrays=[];count=0
    def walk(nodes,paths,depth):
        nonlocal count
        if depth>8:raise StructureError("structure.depth")
        ids=set()
        for n in nodes:
            count+=1
            if count>256:raise StructureError("structure.size")
            if n["memberId"] in ids:raise StructureError("semantic.duplicate")
            ids.add(n["memberId"]);definitions.append(n)
            nextpaths=[p+[{"kind":"member","memberId":n["memberId"]}] for p in paths]
            if n["valueType"]=="Structure":walk(n["members"],nextpaths,depth+1)
            elif n["valueType"]=="StructureArray":
                shape,bounds=n["shape"],n["lowerBounds"]
                if len(shape)!=len(bounds) or any(type(x) is not int for x in shape+bounds):raise StructureError("structure.array-rank")
                if math.prod(shape)>256 or any(b+s-1>2147483647 for b,s in zip(bounds,shape)):raise StructureError("structure.array-range")
                indices=list(itertools.product(*(range(b,b+s) for b,s in zip(bounds,shape))))
                expanded=[]
                for p in nextpaths:
                    arrays.append({"memberPath":p,"shape":shape,"lowerBounds":bounds})
                    expanded.extend(p+[{"kind":"index","indices":list(ix)}] for ix in indices)
                if len(expanded)>256:raise StructureError("structure.size")
                walk(n["members"],expanded,depth+1)
            else:
                for p in nextpaths:
                    if len(leaves)>=256:raise StructureError("structure.size")
                    leaves[path_key(p)]={"member":n,"memberPath":p,"label":label(p)}
    walk(model["members"],[[]],1)
    return {"leaves":leaves,"definitions":definitions,"arrays":arrays}
def resolve(model,path):
    if not isinstance(path,list) or not path:raise StructureError("mapping.member-path")
    nodes=model["members"];i=0
    while i<len(path):
        ep=path[i]
        if ep.get("kind")!="member":raise StructureError("mapping.member-path")
        n=next((x for x in nodes if x["memberId"]==ep.get("memberId")),None)
        if n is None:raise StructureError("mapping.member")
        i+=1
        if n["valueType"]=="StructureArray":
            if i>=len(path) or path[i].get("kind")!="index":raise StructureError("structure.index-required")
            ix=path[i].get("indices",[]);shape,bounds=n["shape"],n["lowerBounds"]
            if len(ix)!=len(shape):raise StructureError("structure.array-rank")
            if any(type(x) is not int or x<b or x>=b+s for x,b,s in zip(ix,bounds,shape)):raise StructureError("structure.index-range")
            i+=1
        if n["valueType"] in CONTAINERS:
            if i==len(path):raise StructureError("structure.whole-mapping")
            nodes=n["members"]
        else:
            if i!=len(path):raise StructureError("mapping.member-path")
            return n
    raise StructureError("structure.whole-mapping")
def signature(n):
    if n["valueType"] not in CONTAINERS:return {k:n[k] for k in ("role","valueType","unit")}
    out={"valueType":n["valueType"],"members":{m["memberId"]:{"semanticId":m["semanticId"],"signature":signature(m)} for m in n["members"]}}
    if n["valueType"]=="StructureArray":out.update(shape=n["shape"],lowerBounds=n["lowerBounds"])
    return out
def assemble(model,values):
    def build(nodes,path):
        out={}
        for n in nodes:
            p=path+[{"kind":"member","memberId":n["memberId"]}]
            if n["valueType"]=="Structure":v=build(n["members"],p)
            elif n["valueType"]=="StructureArray":
                def axis(k,ix):
                    if k==len(n["shape"]):return build(n["members"],p+[{"kind":"index","indices":ix}])
                    return [axis(k+1,ix+[i]) for i in range(n["lowerBounds"][k],n["lowerBounds"][k]+n["shape"][k])]
                v=axis(0,[])
            else:v=values.get(path_key(p))
            out[n["memberId"]]=v
        return out
    layout(model)
    return build(model["members"],[])
