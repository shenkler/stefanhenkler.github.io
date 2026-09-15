#!/usr/bin/env python3
"""Generate publications/index.html from data/henkler_all.bib.

No third-party dependencies. The site remains static: this script runs only at build time.
"""
from pathlib import Path
import html, re

ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "data" / "henkler_all.bib"
TEMPLATE = ROOT / "publications" / "template.html"
OUTPUT = ROOT / "publications" / "index.html"

def balanced(text, pos, opening="{", closing="}"):
    assert text[pos] == opening
    depth, i = 0, pos
    while i < len(text):
        c = text[i]
        if c == opening: depth += 1
        elif c == closing:
            depth -= 1
            if depth == 0: return text[pos+1:i], i+1
        i += 1
    raise ValueError("Unbalanced BibTeX braces")

def split_entries(text):
    out=[]; i=0
    while True:
        m=re.search(r'@(\w+)\s*\{', text[i:], re.I)
        if not m: break
        start=i+m.start(); typ=m.group(1); brace=i+m.end()-1
        content,end=balanced(text,brace)
        comma=content.find(',')
        if comma<0: i=end; continue
        key=content[:comma].strip(); fields=content[comma+1:]
        out.append((typ.lower(),key,fields)); i=end
    return out

def parse_fields(s):
    d={}; i=0; n=len(s)
    while i<n:
        while i<n and (s[i].isspace() or s[i]==','): i+=1
        m=re.match(r'([A-Za-z][\w-]*)\s*=\s*',s[i:])
        if not m: break
        name=m.group(1).lower(); i+=m.end()
        if i<n and s[i]=='{': value,i=balanced(s,i)
        elif i<n and s[i]=='"':
            i+=1; start=i; esc=False
            while i<n:
                if s[i]=='"' and not esc: break
                esc=(s[i]=='\\' and not esc); i+=1
            value=s[start:i]; i+=1
        else:
            start=i
            while i<n and s[i]!=',': i+=1
            value=s[start:i].strip()
        d[name]=value.strip()
    return d

def tex(s):
    # conservative display conversion for common BibTeX sequences in this bibliography
    reps={r'\&':'&', r'\%':'%', r'\_':'_', r'\{':'{', r'\}':'}',
          r'{\"u}':'ü', r'{\"o}':'ö', r'{\"a}':'ä', r'{\"U}':'Ü', r'{\"O}':'Ö', r'{\"A}':'Ä', r'{\ss}':'ß',
          r'\"u':'ü', r'\"o':'ö', r'\"a':'ä', r'\"U':'Ü', r'\"O':'Ö', r'\"A':'Ä'}
    for a,b in reps.items(): s=s.replace(a,b)
    s=re.sub(r'\{([^{}]*)\}',r'\1',s)
    return re.sub(r'\s+',' ',s).strip()

def authors(s):
    if not s: return ''
    parts=re.split(r'\s+and\s+',tex(s))
    return '; '.join(parts)

def anchor(key): return re.sub(r'[^A-Za-z0-9_.:-]+','-',key)

def venue(f,typ):
    bits=[]
    container=f.get('journal') or f.get('booktitle') or f.get('publisher') or f.get('howpublished')
    if container: bits.append(tex(container))
    if f.get('volume'): bits.append('vol. '+tex(f['volume']))
    if f.get('number'): bits.append('no. '+tex(f['number']))
    if f.get('pages'): bits.append('pp. '+tex(f['pages']).replace('--','–'))
    if f.get('address'): bits.append(tex(f['address']))
    return ', '.join(bits)

records=[]
for typ,key,raw in split_entries(BIB.read_text(encoding='utf-8')):
    f=parse_fields(raw); f['_type']=typ; f['_key']=key
    try: y=int(re.sub(r'\D','',f.get('year',''))[:4]) if f.get('year') else -1
    except: y=-1
    f['_year']=y; records.append(f)
records.sort(key=lambda f:(f['_year'], tex(f.get('title','')).lower()), reverse=True)

groups={}
for f in records: groups.setdefault(f['_year'],[]).append(f)
blocks=[]
for y in sorted(groups,reverse=True):
    label=str(y) if y>=0 else 'Undated'
    blocks.append(f'<section class="year-group" aria-labelledby="year-{label}"><h2 id="year-{label}">{label}</h2>')
    for f in groups[y]:
        key=f['_key']; title=tex(f.get('title','Untitled')); auth=authors(f.get('author') or f.get('editor',''))
        ven=venue(f,f['_type'])
        links=[]
        if f.get('doi'):
            doi=tex(f['doi']); links.append(f'<a href="https://doi.org/{html.escape(doi,quote=True)}">DOI</a>')
        if f.get('url'):
            url=tex(f['url']); links.append(f'<a href="{html.escape(url,quote=True)}">Link</a>')
        blocks.append(f'<article class="publication" id="pub-{html.escape(anchor(key))}" data-bibkey="{html.escape(key,quote=True)}">')
        if auth: blocks.append(f'<p class="authors">{html.escape(auth)}</p>')
        blocks.append(f'<p class="title"><cite>{html.escape(title)}</cite></p>')
        if ven: blocks.append(f'<p class="venue">{html.escape(ven)}</p>')
        if links: blocks.append('<p class="links">'+' '.join(links)+'</p>')
        blocks.append('</article>')
    blocks.append('</section>')
body='\n'.join(blocks)
t=TEMPLATE.read_text(encoding='utf-8')
t=re.sub(r'<!-- PUBLICATIONS:START -->.*?<!-- PUBLICATIONS:END -->', '<!-- PUBLICATIONS:START -->\n'+body+'\n  <!-- PUBLICATIONS:END -->', t, flags=re.S)
OUTPUT.write_text(t,encoding='utf-8')
print(f'Generated {OUTPUT.relative_to(ROOT)} with {len(records)} entries.')
