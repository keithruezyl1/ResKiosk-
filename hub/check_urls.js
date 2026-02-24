const https = require('https');

function check(url) {
    https.request(url, { method: 'HEAD' }, (res) => {
        console.log("HEAD", url, "->", res.statusCode, res.headers.location || '');
    }).end();
}

check("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-multilingual-2023-09-06.tar.bz2");
check("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2");
check("https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-lessac-medium.tar.bz2");
