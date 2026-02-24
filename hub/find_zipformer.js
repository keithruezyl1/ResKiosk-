const https = require('https');

https.get('https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/asr-models', { headers: { 'User-Agent': 'node.js' } }, res => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
        try {
            const json = JSON.parse(data);
            if (!json.assets) {
                console.log("No assets:", data);
                return;
            }
            json.assets.forEach(a => {
                if (a.name.includes('stream') && a.name.includes('zipformer')) {
                    if (a.name.includes('multi') || a.name.includes('bi')) {
                        console.log(a.name);
                    }
                }
            });
        } catch (e) { console.error(e); }
    });
});
