import re, os, sys, urllib.request, urllib.parse, hashlib, html, concurrent.futures as cf
BASE = 'https://venesia.tilda.ws'
OUT = sys.argv[1]
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36', 'Accept-Encoding': 'identity'}
def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.geturl()
# 1. crawl pages
pages, queue = {}, ['/']
while queue:
    p = queue.pop()
    if p in pages: continue
    try:
        data, final = get(BASE + p)
    except Exception as e:
        print('PAGE FAIL', p, e); pages[p] = None; continue
    t = data.decode('utf-8', 'replace'); pages[p] = t
    for m in re.findall(r'href="(/[a-zA-Z0-9_\-/]*)(?:[?#][^"]*)?"', t):
        m = m.rstrip('/') or '/'
        if m not in pages and not m.startswith('/tilda') and '.' not in m: queue.append(m)
pages = {k: v for k, v in pages.items() if v}
print('pages', len(pages), sorted(pages))
# 2. asset URLs
ASSET = re.compile(r'(?:https?:)?//(?:static|thb|neo|ws)\.tildacdn\.(?:com|info|net)/[^"\'\s()<>\\,&]+')
def norm(u):
    u = html.unescape(u)
    return 'https:' + u if u.startswith('//') else u
def local(u):
    pu = urllib.parse.urlparse(u)
    path = urllib.parse.unquote(pu.path)
    if path.endswith('/') or not os.path.basename(path): path += 'index'
    if pu.query: 
        root, ext = os.path.splitext(path); path = root + '_' + hashlib.md5(pu.query.encode()).hexdigest()[:6] + ext
    return 'tcdn/' + pu.netloc + path
found = set()
for t in pages.values():
    for u in ASSET.findall(t): found.add(norm(u))
done, failed = {}, []
def fetch(u):
    dst = os.path.join(OUT, local(u))
    if os.path.exists(dst): return u, open(dst,'rb').read()
    try:
        data, _ = get(u)
    except Exception as e:
        return u, None
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(data); return u, data
todo = set(found)
while todo:
    with cf.ThreadPoolExecutor(16) as ex:
        res = list(ex.map(fetch, todo))
    todo = set()
    for u, data in res:
        done[u] = data
        if data is None: failed.append(u); continue
        if u.split('?')[0].endswith('.css'):
            css = data.decode('utf-8','replace')
            for v in re.findall(r'url\(\s*["\']?([^"\')]+)', css):
                v = urllib.parse.urljoin(u, v.strip())
                if 'tildacdn' in v and v not in done and not v.startswith('data:'): todo.add(v)
            for v in ASSET.findall(css):
                v = norm(v)
                if v not in done: todo.add(v)
print('assets', len(done), 'failed', len(failed)); [print(' FAIL', f) for f in failed]
# 3. rewrite css
for u, data in done.items():
    if data is None or not u.split('?')[0].endswith('.css'): continue
    p = os.path.join(OUT, local(u)); css = data.decode('utf-8','replace')
    def rep(m):
        v = urllib.parse.urljoin(u, m.group(2).strip())
        if v in done and done[v] is not None:
            return 'url(' + m.group(1) + os.path.relpath(os.path.join(OUT, local(v)), os.path.dirname(p))
        return m.group(0)
    css = re.sub(r'url\(\s*(["\']?)([^"\')]+)', rep, css)
    open(p, 'w', encoding='utf-8').write(css)
# 4. rewrite pages
for p, t in pages.items():
    name = 'index.html' if p == '/' else p.strip('/') + '/index.html'
    depth = name.count('/')
    pre = '../' * depth
    def rep(m):
        u = norm(m.group(0))
        return pre + local(u) if done.get(u) is not None else m.group(0)
    t = ASSET.sub(rep, t)
    # internal links -> relative folders
    def lrep(m):
        tgt = m.group(1).rstrip('/') or '/'
        if tgt in pages:
            return 'href="' + (pre if pre else './') + ('' if tgt == '/' else tgt.strip('/') + '/') + m.group(2) + '"'
        return m.group(0)
    t = re.sub(r'href="(/[a-zA-Z0-9_\-/]*)((?:[?#][^"]*)?)"', lrep, t)
    dst = os.path.join(OUT, name); os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'w', encoding='utf-8').write(t)
print('written')
