import re, sys, glob, os
root = sys.argv[1]
BAD = re.compile(r'googletagmanager|mc\.yandex\.ru|top-fwz1|topmailru|_tmr|yandex_metrika|ym\(\d', re.I)
GUARD = '''<meta name="robots" content="noindex, nofollow">
<script>/* Portfolio-Archiv: Formulare senden nichts */
(function(){var msg='Это архивная копия сайта для портфолио — заявки отсюда не отправляются.';
function stop(e){var f=e.target.closest&&e.target.closest('form');if(!f)return;e.preventDefault();e.stopImmediatePropagation();alert(msg);}
window.addEventListener('submit',stop,true);
window.addEventListener('click',function(e){if(e.target.closest&&e.target.closest('form .t-submit, form [type=submit]'))stop(e);},true);
window.addEventListener('keydown',function(e){if(e.key==='Enter'&&e.target.closest&&e.target.closest('form')&&e.target.tagName!=='TEXTAREA')stop(e);},true);})();
</script>
'''
for f in glob.glob(os.path.join(root, '**/index.html'), recursive=True):
    if '/tcdn/' in f: continue
    t = open(f, encoding='utf-8').read()
    n0 = len(t)
    t = re.sub(r'<script\b[^>]*>.*?</script>', lambda m: '' if BAD.search(m.group(0)) else m.group(0), t, flags=re.S)
    t = re.sub(r'<noscript\b[^>]*>.*?</noscript>', lambda m: '' if BAD.search(m.group(0)) else m.group(0), t, flags=re.S)
    if 'Portfolio-Archiv' not in t:
        t = t.replace('<head>', '<head>\n' + GUARD, 1)
    open(f, 'w', encoding='utf-8').write(t)
    left = BAD.findall(t)
    print(os.path.relpath(f, root), n0 - len(t), 'left:', set(left) or '-')
