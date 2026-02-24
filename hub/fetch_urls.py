import json
import urllib.request

try:
    with urllib.request.urlopen("https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/asr-models") as url:
        data = json.loads(url.read().decode())
        multi = [a['name'] for a in data['assets'] if 'multi' in a['name'] or 'bi' in a['name']]
        with open('asr.txt', 'w') as f:
            for m in multi:
                f.write(m + '\n')
except Exception as e:
    with open('asr.txt', 'w') as f:
        f.write(str(e))
