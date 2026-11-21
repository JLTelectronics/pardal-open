import os, re

SHARE = os.environ.get("KICAD_SHARE") or next(
    (d for d in ("/usr/share/kicad", "/Applications/KiCad/KiCad.app/Contents/SharedSupport") if os.path.isdir(d)),
    "/usr/share/kicad")
SYS_SYM = os.path.join(SHARE, "symbols")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
LOCAL_LIBS = {"lcsc": os.path.join(PROJ, "libs", "lcsc.kicad_sym"), "pardal": os.path.join(PROJ, "libs", "pardal.kicad_sym"),
              "pardal_cm3": os.path.join(PROJ, "libs", "pardal_cm3.kicad_sym")}

def tokenize(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in " \t\r\n":
            i += 1
        elif c in "()":
            yield c; i += 1
        elif c == '"':
            j = i + 1; buf = []
            while s[j] != '"':
                if s[j] == "\\":
                    buf.append(s[j + 1]); j += 2
                else:
                    buf.append(s[j]); j += 1
            yield ('"', "".join(buf)); i = j + 1
        else:
            j = i
            while j < n and s[j] not in ' \t\r\n()"':
                j += 1
            yield s[i:j]; i = j

class Q(str):
    pass

def parse(s):
    stack = [[]]
    for t in tokenize(s):
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop(); stack[-1].append(x)
        elif isinstance(t, tuple):
            stack[-1].append(Q(t[1]))
        else:
            stack[-1].append(t)
    return stack[0][0]

def dump(x, ind=0):
    if isinstance(x, list):
        if not x:
            return "()"
        simple = all(not isinstance(e, list) for e in x)
        if simple:
            return "(" + " ".join(dump(e) for e in x) + ")"
        out = "(" + dump(x[0])
        for e in x[1:]:
            if isinstance(e, list):
                out += "\n" + "\t" * (ind + 1) + dump(e, ind + 1)
            else:
                out += " " + dump(e)
        return out + "\n" + "\t" * ind + ")"
    if isinstance(x, Q):
        return '"' + x.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    return str(x)

def find(node, key):
    return [e for e in node if isinstance(e, list) and e and e[0] == key]

def find1(node, key):
    r = find(node, key)
    return r[0] if r else None

_cache = {}

def load_lib(lib):
    if lib not in _cache:
        path = LOCAL_LIBS.get(lib, os.path.join(SYS_SYM, lib + ".kicad_sym"))
        tree = parse(open(path, encoding="utf-8").read())
        _cache[lib] = {e[1]: e for e in find(tree, "symbol")}
    return _cache[lib]

def get_symbol(lib_id):
    import copy
    lib, name = lib_id.split(":", 1)
    syms = load_lib(lib)
    sym = copy.deepcopy(syms[name])
    ext = find1(sym, "extends")
    if ext:
        parent = copy.deepcopy(get_symbol(lib + ":" + ext[1]))
        child_props = {p[1]: p for p in find(sym, "property")}
        newp = []
        for e in parent:
            if isinstance(e, list) and e and e[0] == "property" and e[1] in child_props:
                newp.append(child_props.pop(e[1]))
            else:
                newp.append(e)
        idx = max(i for i, e in enumerate(newp) if isinstance(e, list) and e and e[0] == "property")
        for p in child_props.values():
            idx += 1; newp.insert(idx, p)
        pname = parent[1].split(":")[-1]
        for e in newp:
            if isinstance(e, list) and e and e[0] == "symbol" and isinstance(e[1], str):
                e[1] = Q(e[1].replace(pname, name, 1))
        sym = newp
    sym[1] = Q(lib_id)
    return sym

def pins(lib_id):
    sym = get_symbol(lib_id)
    name = lib_id.split(":", 1)[1]
    out = []
    for sub in find(sym, "symbol"):
        m = re.match(r".*_(\d+)_(\d+)$", sub[1])
        unit = int(m.group(1))
        for p in find(sub, "pin"):
            at = find1(p, "at")
            ln = find1(p, "length")
            nm = find1(p, "name")[1]
            nr = find1(p, "number")[1]
            out.append((unit, str(nr), str(nm), p[1], float(at[1]), float(at[2]),
                        float(at[3]) if len(at) > 3 else 0.0, float(ln[1]) if ln else 2.54))
    return out

def units(lib_id):
    return sorted({u for u, *_ in pins(lib_id) if u > 0}) or [1]

def prop(lib_id, key):
    sym = get_symbol(lib_id)
    for p in find(sym, "property"):
        if p[1] == key:
            return str(p[2])
    return ""
