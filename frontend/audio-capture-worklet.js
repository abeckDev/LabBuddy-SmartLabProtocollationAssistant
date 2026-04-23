/**
 * AudioWorklet: Captures microphone audio, resamples to 24kHz, outputs PCM16.
 * Posts Int16Array buffers to the main thread every ~100ms.
 */
class AudioCaptureProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._buffer = [];
        this._targetLength = 2400; // ~100ms at 24kHz
    }

    process(inputs) {
        const channel = inputs[0]?.[0];
        if (!channel || channel.length === 0) return true;

        // Downsample from sampleRate (e.g. 48000) to 24000
        const ratio = sampleRate / 24000;

        for (let i = 0; i < channel.length; i += ratio) {
            const idx = Math.min(Math.floor(i), channel.length - 1);
            const sample = Math.max(-1, Math.min(1, channel[idx]));
            // Float32 → Int16
            this._buffer.push(sample < 0 ? sample * 0x8000 : sample * 0x7FFF);
        }

        if (this._buffer.length >= this._targetLength) {
            const pcm16 = new Int16Array(this._buffer.splice(0, this._targetLength));
            this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
        }

        return true;
    }
}

registerProcessor('audio-capture-processor', AudioCaptureProcessor);
