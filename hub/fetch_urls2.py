import json
import urllib.request
import traceback

try:
    req = urllib.request.Request(
        "https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/asr-models",
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        multi = [a['name'] for a in data['assets'] if 'multi' in a['name'].lower() or 'bi' in a['name'].lower()]
        with open('asr.txt', 'w') as f:
            for m in multi:
                f.write(m + '\n')
except Exception as e:
    with open('asr.txt', 'w') as f:
        f.write(str(e) + '\n' + traceback.format_exc())
