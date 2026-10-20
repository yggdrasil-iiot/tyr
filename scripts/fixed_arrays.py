"""Bounded fixed scalar arrays: offline geometry, selection and virtual buffers."""
import copy,itertools,math,re
import source_codecs

class ArrayError(ValueError):
    def __init__(self,code,detail=""):self.code=code;self.detail=detail;super().__init__(code+(": "+detail if detail else ""))

def geometry(s):
    f=s.get("fixedArray")
    if not isinstance(f,dict):raise ArrayError("array.definition-required")
    shape,lower,strides=f.get("shape"),f.get("lowerBounds"),f.get("strides")
    if any(not isinstance(v,list) for v in (shape,lower,strides)) or not 1<=len(shape)<=3 or len(shape)!=len(lower) or len(shape)!=len(strides):raise ArrayError("array.rank")
    if any(type(x) is not int or not 1<=x<=256 for x in shape) or math.prod(shape)>256:raise ArrayError("array.count")
    if any(type(x) is not int or x< -2147483648 or x+n-1>2147483647 for x,n in zip(lower,shape)):raise ArrayError("array.bounds")
    if any(type(x) is not int or not 1<=x<=4096 for x in strides):raise ArrayError("array.stride")
    a,r=s["access"],s["rawRepresentation"];unit=f["strideUnit"];width=source_codecs.storage_width(s)
    if r.get("codec") or r.get("bitCoordinate") or a.get("bitOffset") is not None or width is None:raise ArrayError("array.element-unsupported")
    if r["mode"]=="typed":
        if a["kind"] not in ("symbol","opcua-node") or unit!="element":raise ArrayError("array.stride-unit")
        base,scale,element=0,1,1
    elif a["kind"]=="device-register":
        if unit!="word16" or a.get("addressUnit")!="word16" or width%2:raise ArrayError("array.stride-unit")
        base,scale,element=a.get("addressIndex"),2,width//2
    elif a["kind"]=="db-offset":
        if unit!="byte":raise ArrayError("array.stride-unit")
        base,scale,element=a.get("byteOffset"),1,width
    else:raise ArrayError("array.profile")
    range_=f.get("range",{});start,end=range_.get("start"),range_.get("endExclusive")
    if type(base) is not int or type(start) is not int or type(end) is not int or start!=base or not 0<=start<end<=2147483648:raise ArrayError("array.storage-range")
    capacity=end-start
    if capacity*scale>4096:raise ArrayError("array.buffer-limit")
    offsets=sorted(sum(i*stride for i,stride in zip(coords,strides)) for coords in itertools.product(*(range(n) for n in shape)))
    if any(b<a+element for a,b in zip(offsets,offsets[1:])):raise ArrayError("array.overlap")
    if offsets[-1]+element>capacity:raise ArrayError("array.storage-range","Required endExclusive="+str(start+offsets[-1]+element))
    return {"shape":shape,"lowerBounds":lower,"upperBounds":[l+n-1 for l,n in zip(lower,shape)],"strides":strides,"strideUnit":unit,"range":range_,"base":base,"elementExtent":element,"unitScale":scale,"elementCount":math.prod(shape),"bufferLength":capacity*scale,"requiredExtent":offsets[-1]+element}

def rules(s):
    if "fixedArray" not in s:return []
    try:geometry(s);return []
    except ArrayError as e:return [e.code]
    except (KeyError,TypeError,ValueError):return ["array.definition-invalid"]

def index(s,indices):
    g=geometry(s)
    if not isinstance(indices,list) or len(indices)!=len(g["shape"]) or any(type(i) is not int for i in indices):raise ArrayError("array.index-rank")
    if any(not l<=i<=h for i,l,h in zip(indices,g["lowerBounds"],g["upperBounds"])):raise ArrayError("array.index-range","indices="+str(indices)+"; lower="+str(g["lowerBounds"])+"; upper="+str(g["upperBounds"]))
    offset=sum((i-l)*stride for i,l,stride in zip(indices,g["lowerBounds"],g["strides"]))
    coordinate=g["base"]+offset
    access=copy.deepcopy(s["access"])
    if access["kind"]=="device-register":access["addressIndex"]=coordinate;address=access["deviceArea"]+str(coordinate)+" (decimal index)"
    elif access["kind"]=="db-offset":access["byteOffset"]=coordinate;address="DB"+str(access["dbNumber"])+".byte"+str(coordinate)
    else:address=s["rawAddressText"]+" / logical indices "+str(indices)+" / slot "+str(offset)
    return {**g,"indices":indices,"offset":offset,"byteOffset":offset*g["unitScale"] if g["strideUnit"]!="element" else None,"slotOffset":offset if g["strideUnit"]=="element" else None,"resolvedAccess":access,"resolvedAddress":address}

def validate_sample(s,sample):
    g=geometry(s)
    if not isinstance(sample,dict):raise ArrayError("sample.missing")
    if s["rawRepresentation"]["mode"]=="typed":
        if set(sample)!={"typedValues"} or not isinstance(sample["typedValues"],list):raise ArrayError("array.sample-mode","typedValues flat storage slots required")
        if len(sample["typedValues"])!=g["bufferLength"]:raise ArrayError("array.sample-length","Expected "+str(g["bufferLength"])+" slots")
        # Padded slots may be null; selected null is diagnosed separately.
        if any(v is not None and not isinstance(v,(str,int,float,bool)) for v in sample["typedValues"]):raise ArrayError("array.sample-shape","Nested/native structures unsupported")
    else:
        text=sample.get("bytesHex")
        if set(sample)!={"bytesHex"} or not isinstance(text,str) or len(text)>12288 or not re.fullmatch(r"[0-9a-fA-F\s]*",text):raise ArrayError("sample.hex")
        try:data=bytes.fromhex(text)
        except ValueError:raise ArrayError("sample.hex")
        if len(data)!=g["bufferLength"]:raise ArrayError("array.sample-length","Expected "+str(g["bufferLength"])+" bytes")
    return g

def select(s,sample,indices):
    detail=index(s,indices);validate_sample(s,sample)
    scalar=copy.deepcopy(s);scalar.pop("fixedArray");scalar["access"]=detail["resolvedAccess"]
    if s["rawRepresentation"]["mode"]=="typed":
        value=sample["typedValues"][detail["slotOffset"]]
        if value is None:raise ArrayError("array.element-missing","indices="+str(indices))
        payload={"typedValue":value}
    else:
        data=bytes.fromhex(sample["bytesHex"]);start=detail["byteOffset"]
        payload={"bytesHex":data[start:start+source_codecs.storage_width(s)].hex()}
    return scalar,payload,detail
