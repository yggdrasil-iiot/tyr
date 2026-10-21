"""Bounded P3-B source contracts; no runtime communication."""
WIDTH={"Int16":2,"UInt16":2,"Int32":4,"UInt32":4,"Int64":8,"Float32":4,"Float64":8,"Boolean":1}
BIT_AREAS={"M","X","Y","L","S","B"}
WORD_AREAS={"D","W","R","ZR","SD","TN","CN"}
def decoded_type(source):
    if source["access"].get("bitOffset") is not None:return "Boolean"
    codec=source["rawRepresentation"].get("codec",{}).get("kind")
    return "Int32" if codec=="bcd16" else source["rawRepresentation"].get("valueType")
def storage_width(source):
    raw=source["rawRepresentation"];codec=raw.get("codec",{})
    if codec.get("kind")=="ascii-fixed":return codec["length"]
    if codec.get("kind")=="s7-date-time":return 8
    return WIDTH.get(raw.get("valueType"))
def rules(s):
    if s["schemaVersion"] not in ("2.1.0","2.2.0","2.4.0"):return []
    a,r=s["access"],s["rawRepresentation"];out=[]
    def add(code):out.append(code)
    if a["kind"]=="device-register":
        bit=a.get("addressUnit")=="bit"
        if bit:
            if r.get("valueType")!="Boolean" or r.get("mode")!="bytes" or r.get("codec") or r.get("bitCoordinate"):add("source.native-bit-representation")
            actual=1
        else:
            if a.get("deviceArea") in BIT_AREAS:add("source.native-bit-unit")
            elif a.get("deviceArea") not in WORD_AREAS:add("source.area-unsupported")
            actual=None if a.get("wordCount") is None else a["wordCount"]*2
    elif a["kind"]=="db-offset":actual=a.get("byteLength")
    else:actual=None
    expected=storage_width(s)
    if actual is not None and expected is not None and actual!=expected:add("source.width")
    codec=r.get("codec",{});kind=codec.get("kind")
    if kind:
        if s["inputStage"]!="raw" or a.get("bitOffset") is not None or r.get("bitCoordinate"):add("source.codec-stage")
        if kind in ("ascii-fixed","s7-date-time") and (r.get("byteOrder")!="big" or r.get("wordOrder")!="high-first"):add("source.codec-wire-order")
        if kind=="s7-date-time":
            if a["kind"]!="db-offset":add("source.codec-profile")
            if codec["timezone"] is None:add("source.timezone-required")
    coord=r.get("bitCoordinate")
    if a.get("bitOffset") is not None:
        if not coord:add("source.bit-coordinate-required")
        elif coord["kind"]=="native-byte":
            if a["bitOffset"]>7 or expected is None or coord["byteIndex"]>=expected:add("source.bit-coordinate")
        elif r.get("valueType") not in ("Int16","UInt16","Int32","UInt32","Int64"):add("source.bit-coordinate")
    elif coord:add("source.bit-coordinate-unused")
    return sorted(set(out))
