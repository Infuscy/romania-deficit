"""PDF text extractor v2: Flate streams + ToUnicode CMap decoding."""
import re, sys, zlib

def decompress_streams(data):
    for m in re.finditer(rb'stream\r?\n', data):
        start = m.end()
        end = data.find(b'endstream', start)
        if end < 0:
            continue
        raw = data[start:end]
        try:
            yield zlib.decompress(raw)
        except Exception:
            continue

def build_tounicode(streams):
    """Global code->unicode map from all ToUnicode CMaps."""
    cmap = {}
    for dec in streams:
        if b'beginbfchar' not in dec and b'beginbfrange' not in dec:
            continue
        # bfchar: <src> <dst>
        for blk in re.findall(rb'beginbfchar(.*?)endbfchar', dec, re.S):
            for src, dst in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
                code = int(src, 16)
                uni = ''.join(chr(int(dst[i:i+4], 16)) for i in range(0, len(dst), 4))
                cmap[code] = uni
        # bfrange: <start> <end> <dst>  OR  <start> <end> [<d1> <d2> ...]
        for blk in re.findall(rb'beginbfrange(.*?)endbfrange', dec, re.S):
            for a, b, arr in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]', blk, re.S):
                start_c, end_c = int(a, 16), int(b, 16)
                dsts = re.findall(rb'<([0-9A-Fa-f]+)>', arr)
                for i, d in enumerate(dsts):
                    if start_c + i <= end_c:
                        uni = ''.join(chr(int(d[j:j+4], 16)) for j in range(0, len(d), 4))
                        cmap[start_c + i] = uni
            blk_wo = re.sub(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[.*?\]', b'', blk, flags=re.S)
            for a, b, d in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk_wo):
                start_c, end_c, base = int(a, 16), int(b, 16), int(d, 16)
                width = len(d)
                for i in range(end_c - start_c + 1):
                    cmap[start_c + i] = chr(base + i)
    return cmap

def decode_string(raw, cmap):
    # try 2-byte codes first if they all map
    if len(raw) % 2 == 0 and cmap:
        two = ''.join(cmap.get(int.from_bytes(raw[i:i+2], 'big'), '') for i in range(0, len(raw), 2))
        if two and all(cmap.get(int.from_bytes(raw[i:i+2], 'big')) for i in range(0, len(raw), 2)):
            return two
    out = []
    i = 0
    while i < len(raw):
        two = int.from_bytes(raw[i:i+2], 'big') if i + 2 <= len(raw) else None
        one = raw[i]
        if two in cmap:
            out.append(cmap[two]); i += 2
        elif one in cmap:
            out.append(cmap[one]); i += 1
        else:
            out.append(chr(one)); i += 1
    return ''.join(out)

def unescape(s):
    s = re.sub(rb'\\([nrtbf()\\])', lambda x: {b'n':b'\n',b'r':b'\r',b't':b'\t',b'b':b'\b',b'f':b'\f',b'(' :b'(',b')':b')',b'\\':b'\\'}[x.group(1)], s)
    s = re.sub(rb'\\([0-7]{1,3})', lambda x: bytes([int(x.group(1),8)&255]), s)
    s = s.replace(b'\\\n', b'')
    return s

TOKEN = re.compile(rb'\((?:\\.|[^()\\])*\)|<[0-9A-Fa-f\s]*>|\bTJ\b|\bTj\b|\bTd\b|\bTD\b|\bT\*\b|\bTf\b|\bET\b')

def pick(raw_bytes, cmap):
    dec = decode_string(raw_bytes, cmap)
    raw = raw_bytes.decode('latin-1', 'replace')
    raw_clean = re.sub(r'[\x00-\x1f]', '', raw)
    if re.fullmatch(r'[-\d.,%\s]+', raw_clean or '') and re.search(r'\d', raw_clean):
        return raw_clean
    return dec

def extract_text(streams, cmap):
    parts = []
    for dec in streams:
        if b'Tj' not in dec and b'TJ' not in dec:
            continue
        chunks = []
        for tm in TOKEN.finditer(dec):
            tok = tm.group(0)
            if tok.startswith(b'('):
                chunks.append(pick(unescape(tok[1:-1]), cmap))
            elif tok.startswith(b'<'):
                hx = re.sub(rb'\s', b'', tok[1:-1])
                try:
                    raw = bytes.fromhex(hx.decode())
                except Exception:
                    continue
                chunks.append(pick(raw, cmap))
            elif tok in (b'Td', b'TD', b'T*', b'ET'):
                chunks.append('\n')
        parts.append(''.join(chunks))
    return '\n'.join(parts)

if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    streams = list(decompress_streams(data))
    cmap = build_tounicode(streams)
    s = extract_text(streams, cmap)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            f.write(s)
    else:
        sys.stdout.buffer.write(s.encode('utf-8', 'replace'))
