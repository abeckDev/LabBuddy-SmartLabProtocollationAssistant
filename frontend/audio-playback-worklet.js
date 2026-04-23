/**
 * AudioWorklet: Receives PCM16 24kHz audio, upsamples to context sampleRate, plays back.
 * Accepts messages: ArrayBuffer (audio data) or 'clear' (flush buffer on barge-in).
 */
class AudioPlaybackProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._buffer = new Float32Array(0);

        this.port.onmessage = (e) => {
            if (e.data === 'clear') {
                this._buffer = new Float32Array(0);
                return;
            }

            // Decode PCM16 Int16 → Float32
            const int16 = new Int16Array(e.data);
            const float32 = new Float32Array(int16.length);
            for (let i = 0; i < int16.length; i++) {
                float32[i] = int16[i] / 32768.0;
            }

            // Upsample from 24kHz to sampleRate (e.g. 48kHz)
            const ratio = sampleRate / 24000;
            const outLen = Math.ceil(float32.length * ratio);
            const upsampled = new Float32Array(outLen);
            for (let i = 0; i < outLen; i++) {
                const srcIdx = Math.min(Math.floor(i / ratio), float32.length - 1);
                upsampled[i] = float32[srcIdx];
            }

            // Append to playback buffer
            const newBuf = new Float32Array(this._buffer.length + upsampled.length);
            newBuf.set(this._buffer);
            newBuf.set(upsampled, this._buffer.length);
            this._buffer = newBuf;
        };
    }

    process(inputs, outputs) {
        const output = outputs[0]?.[0];
        if (!output) return true;

        if (this._buffer.length >= output.length) {
            output.set(this._buffer.subarray(0, output.length));
            this._buffer = this._buffer.subarray(output.length);
        } else if (this._buffer.length > 0) {
            output.set(this._buffer);
            output.fill(0, this._buffer.length);
            this._buffer = new Float32Array(0);
        }
        // else: output is already zeroed (silence)

        return true;
    }
}

registerProcessor('audio-playback-processor', AudioPlaybackProcessor);
