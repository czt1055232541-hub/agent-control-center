import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request, urllib.parse, json

print('Verifying SearXNG integration for OpenClaw...')
print()

# 1. Verify it's the real SearXNG
r = urllib.request.urlopen('http://127.0.0.1:8888/')
body = r.read().decode('utf-8')
assert 'SearXNG' in body, 'Not the real SearXNG!'
print('1. Real SearXNG confirmed')

# 2. Test JSON API format (what OpenClaw expects)
q = 'OpenClaw web search'
url = 'http://127.0.0.1:8888/search?q={}&format=json'.format(urllib.parse.quote(q))
r = urllib.request.urlopen(url)
data = json.loads(r.read().decode('utf-8'))
results = data.get('results', [])
print('2. JSON API works: {} results'.format(len(results)))

engines = set(r2.get('engine', '?') for r2 in results)
print('   Engines: {}'.format(', '.join(sorted(engines))))

for res in results[:3]:
    print('   - [{}] {}'.format(res.get('engine', '?'), res.get('title', '')[:50]))

# 3. Verify required fields
for i, res in enumerate(results):
    assert 'url' in res, 'Result {} missing url!'.format(i)
    assert 'title' in res, 'Result {} missing title!'.format(i)
print('3. All results have required fields (url, title)')

# 4. Chinese query
q2 = '人工智能'
url2 = 'http://127.0.0.1:8888/search?q={}&format=json&language=zh-CN'.format(urllib.parse.quote(q2))
r2 = urllib.request.urlopen(url2)
data2 = json.loads(r2.read().decode('utf-8'))
results2 = data2.get('results', [])
engines2 = set(r3.get('engine', '?') for r3 in results2)
print('4. Chinese OK: {} results from {}'.format(len(results2), ', '.join(sorted(engines2))))

print()
print('=== ALL CHECKS PASSED ===')
print('SearXNG is ready for OpenClaw agents!')
