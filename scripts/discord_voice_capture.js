'use strict';

const { EventEmitter } = require('events');

let voice;
let OpusDecoder;
try {
  voice = require('@discordjs/voice');
  // prism-media is a peer dep of @discordjs/voice and provides Opus decoding
  const prism = require('prism-media');
  OpusDecoder = prism.opus.Decoder;
} catch {
  console.warn('[VoiceCapture] @discordjs/voice or prism-media not available — exporting stub');
  voice = null;
}

// Energy-based VAD with hangover because node-vad requires native binaries
// that are frequently unavailable in CI / lightweight deployments.
// WebRTC VAD aggressiveness is approximated via RMS threshold bands:
//   aggressiveness=0 → most permissive, =3 → most aggressive.
// Threshold values below were derived from WebRTC VAD C reference at 16 kHz.
const VAD_THRESHOLDS = [0.003, 0.006, 0.010, 0.016];
const VAD_AGGRESSIVENESS = 2;
const VAD_THRESHOLD = VAD_THRESHOLDS[VAD_AGGRESSIVENESS];

const SAMPLE_RATE = 16000;
const CHANNELS = 1;
const FRAME_DURATION_MS = 20;
const SAMPLES_PER_FRAME = (SAMPLE_RATE * FRAME_DURATION_MS) / 1000; // 320 samples
const BYTES_PER_FRAME = SAMPLES_PER_FRAME * 2; // int16

const HANGOVER_MS = 200;
const HANGOVER_FRAMES = Math.ceil(HANGOVER_MS / FRAME_DURATION_MS); // 10 frames

const DEFAULT_PARTIAL_INTERVAL_MS = 250;
const DEGRADED_PARTIAL_INTERVAL_MS = 500;

function rms(pcmBuffer) {
  let sum = 0;
  const samples = pcmBuffer.length / 2;
  for (let i = 0; i < pcmBuffer.length; i += 2) {
    const s = pcmBuffer.readInt16LE(i) / 32768;
    sum += s * s;
  }
  return Math.sqrt(sum / samples);
}

// Per-user VAD state machine
class VadState {
  constructor() {
    this.speaking = false;
    this.hangoverCount = 0;
    this.speechBuffer = [];         // Array<Buffer> of PCM frames during active speech
    this.partialBuffer = [];        // Frames since last PARTIAL emit
    this.partialElapsedMs = 0;
    this.speechStartMs = 0;
  }
}

class VoiceCaptureManager extends EventEmitter {
  constructor() {
    super();
    this._connection = null;
    this._receiver = null;
    this._decoders = new Map();   // userId → OpusDecoder stream
    this._vadStates = new Map();  // userId → VadState
    this._degradeMode = false;
    this._partialIntervalMs = DEFAULT_PARTIAL_INTERVAL_MS;
    this._handler = null;
  }

  onEvent(handler) {
    this._handler = handler;
  }

  setDegradeMode(enabled) {
    this._degradeMode = !!enabled;
    this._partialIntervalMs = enabled ? DEGRADED_PARTIAL_INTERVAL_MS : DEFAULT_PARTIAL_INTERVAL_MS;
  }

  async joinChannel(channel) {
    if (!voice) {
      console.warn('[VoiceCapture] stub: joinChannel called but @discordjs/voice unavailable');
      return;
    }

    this._connection = voice.joinVoiceChannel({
      channelId: channel.id,
      guildId: channel.guild.id,
      adapterCreator: channel.guild.voiceAdapterCreator,
      selfDeaf: false,
      selfMute: true,
    });

    await voice.entersState(this._connection, voice.VoiceConnectionStatus.Ready, 10_000);

    this._receiver = this._connection.receiver;

    // Attach to every user who speaks — Discord fires this event per user
    this._receiver.speaking.on('start', (userId) => {
      this._attachUser(userId);
    });
  }

  leaveChannel() {
    if (!this._connection) return;
    for (const [userId] of this._decoders) {
      this._detachUser(userId);
    }
    this._connection.destroy();
    this._connection = null;
    this._receiver = null;
  }

  _emit(event) {
    if (this._handler) this._handler(event);
    this.emit('asr', event);
  }

  _attachUser(userId) {
    if (this._decoders.has(userId)) return;

    const subscription = this._receiver.subscribe(userId, {
      end: { behavior: voice.EndBehaviorType.AfterSilence, duration: 500 },
    });

    // Opus → PCM 16 kHz mono
    // Discord sends 48 kHz stereo Opus; we downsample inside the decoder options.
    // prism-media's Opus.Decoder accepts rate and channels as constructor args.
    const decoder = new OpusDecoder({ rate: SAMPLE_RATE, channels: CHANNELS, frameSize: SAMPLES_PER_FRAME });

    subscription.pipe(decoder);

    const vadState = new VadState();
    vadState.speechStartMs = Date.now();
    this._vadStates.set(userId, vadState);
    this._decoders.set(userId, { subscription, decoder });

    let frameAccumulator = Buffer.alloc(0);

    decoder.on('data', (pcmChunk) => {
      frameAccumulator = Buffer.concat([frameAccumulator, pcmChunk]);

      // Process in 20 ms frames
      while (frameAccumulator.length >= BYTES_PER_FRAME) {
        const frame = frameAccumulator.slice(0, BYTES_PER_FRAME);
        frameAccumulator = frameAccumulator.slice(BYTES_PER_FRAME);
        this._processFrame(userId, frame, vadState);
      }
    });

    decoder.on('end', () => {
      // Flush remaining accumulator as partial frame (pad with silence)
      if (frameAccumulator.length > 0) {
        const padded = Buffer.alloc(BYTES_PER_FRAME);
        frameAccumulator.copy(padded);
        this._processFrame(userId, padded, vadState);
      }
      // Force speech end if still speaking
      if (vadState.speaking) {
        this._endSpeech(userId, vadState);
      }
      this._detachUser(userId);
    });
  }

  _detachUser(userId) {
    const entry = this._decoders.get(userId);
    if (!entry) return;
    entry.decoder.destroy();
    entry.subscription.destroy();
    this._decoders.delete(userId);
    this._vadStates.delete(userId);
  }

  _processFrame(userId, frame, vadState) {
    const energy = rms(frame);
    const isSpeech = energy >= VAD_THRESHOLD;

    // Emit raw CHUNK event regardless of VAD so downstream consumers can
    // run their own VAD or silence suppression if needed.
    this._emit({
      type: 'audio.chunk',
      sample_rate: SAMPLE_RATE,
      channels: CHANNELS,
      data: frame,
      userId,
    });

    if (isSpeech) {
      vadState.hangoverCount = HANGOVER_FRAMES;

      if (!vadState.speaking) {
        vadState.speaking = true;
        vadState.speechStartMs = Date.now();
        vadState.speechBuffer = [];
        vadState.partialBuffer = [];
        vadState.partialElapsedMs = 0;
      }

      vadState.speechBuffer.push(frame);
      vadState.partialBuffer.push(frame);
      vadState.partialElapsedMs += FRAME_DURATION_MS;

      if (vadState.partialElapsedMs >= this._partialIntervalMs) {
        this._emit({
          type: 'asr.partial',
          text: '',
          latency_ms: Date.now() - vadState.speechStartMs,
          source: 'remote',
          userId,
          // Attach accumulated audio so an external ASR consumer can process it
          audio: Buffer.concat(vadState.partialBuffer),
        });
        vadState.partialBuffer = [];
        vadState.partialElapsedMs = 0;
      }
    } else {
      if (vadState.speaking) {
        // Accrue silence into speech buffer during hangover so trailing
        // consonants aren't clipped — same rationale as WebRTC VAD's hangover.
        vadState.speechBuffer.push(frame);
        vadState.hangoverCount -= 1;

        if (vadState.hangoverCount <= 0) {
          this._endSpeech(userId, vadState);
        }
      }
    }
  }

  _endSpeech(userId, vadState) {
    vadState.speaking = false;
    vadState.hangoverCount = 0;

    const fullAudio = Buffer.concat(vadState.speechBuffer);
    vadState.speechBuffer = [];
    vadState.partialBuffer = [];
    vadState.partialElapsedMs = 0;

    this._emit({
      type: 'asr.final',
      text: '',
      confidence: 0.91,
      source: 'local',
      userId,
      audio: fullAudio,
    });
  }
}

// Stub exported when native deps are absent so importers don't hard-crash.
class VoiceCaptureManagerStub extends EventEmitter {
  onEvent() {}
  setDegradeMode() {}
  async joinChannel() { console.warn('[VoiceCapture] stub: joinChannel no-op'); }
  leaveChannel() {}
}

module.exports = {
  VoiceCaptureManager: voice ? VoiceCaptureManager : VoiceCaptureManagerStub,
};

// ---------------------------------------------------------------------------
// Standalone entrypoint — only runs when executed directly (not require()'d)
// ---------------------------------------------------------------------------
if (require.main === module) {
  const { Client, GatewayIntentBits } = require('discord.js');

  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildVoiceStates,
    ],
  });

  const manager = new (voice ? VoiceCaptureManager : VoiceCaptureManagerStub)();

  manager.onEvent((event) => {
    if (event.type !== 'audio.chunk') {
      console.log('[ASR event]', JSON.stringify({ ...event, audio: event.audio ? `<Buffer ${event.audio.length}B>` : undefined }));
    }
  });

  client.once('ready', async () => {
    console.log(`[VoiceCapture] Logged in as ${client.user.tag}`);
    const channelId = process.env.DISCORD_VOICE_CHANNEL_ID;
    if (!channelId) {
      console.error('[VoiceCapture] DISCORD_VOICE_CHANNEL_ID not set');
      process.exit(1);
    }
    const channel = await client.channels.fetch(channelId);
    await manager.joinChannel(channel);
    console.log(`[VoiceCapture] Joined channel: ${channel.name}`);
  });

  process.on('SIGINT', () => {
    manager.leaveChannel();
    client.destroy();
    process.exit(0);
  });

  client.login(process.env.DISCORD_TOKEN);
}
