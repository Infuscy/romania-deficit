"""Minimal PDF text extractor (Flate + literal strings / TJ arrays)."""
import re, sys, zlib

def extract(path):
    data = open(path, 'rb').read()
    out = []
    for m in re.finditer(rb'stream\r?\n', data):
        start = m.end()
        end = data.find(b'endstream', start)
        if end < 0:
            continue
        raw = data[start:end]
        try:
            dec = zlib.decompress(raw)
        except Exception:
            continue
        # extract text show operators
        chunks = []
        for tm in re.finditer(rb'\((?:\\.|[^()\\])*\)|\bTJ\b|\bTj\b|\bTd\b|\bTD\b|\bT\*\b|\bTJ\b', dec):
            tok = tm.group(0)
            if tok.startswith(b'('):
                s = tok[1:-1]
                s = re.sub(rb'\\([nrtbf()\\])', lambda x: {b'n':b'\n',b'r':b'\r',b't':b'\t',b'b':b'\b',b'f':b'\f',b'(' :b'(',b')':b')',b'\\':b'\\'}[x.group(1)], s)
                s = re.sub(rb'\\([0-7]{1,3})', lambda x: bytes([int(x.group(1),8)&255]), s)
                chunks.append(s)
            else:
                chunks.append(b'\n')
        out.append(b''.join(chunks))
    return b'\n'.join(out)

if __name__ == '__main__':
    text = extract(sys.argv[1])
    s = text.decode('latin-1', 'replace')
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            f.write(s)
    else:
        sys.stdout.buffer.write(s.encode('utf-8', 'replace'))
