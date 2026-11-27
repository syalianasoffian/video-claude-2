"""Generate two music sections with MusicGen (tense -> uplifting). usage: musicgen.py out_prefix"""
import sys, warnings, torch, numpy as np, soundfile as sf
warnings.filterwarnings("ignore")
from transformers import AutoProcessor, MusicgenForConditionalGeneration

torch.set_num_threads(4); torch.manual_seed(7)
M = "facebook/musicgen-small"
proc = AutoProcessor.from_pretrained(M)
model = MusicgenForConditionalGeneration.from_pretrained(M)
P = {
    "tense": "modern minimal suspense underscore for a business ad, ticking hi-hat pulse, deep warm sub bass, "
             "muted plucked synth ostinato in A minor, subtle cinematic tension, clean mix, no vocals, 100 bpm",
    "bright": "uplifting modern corporate pop, warm piano chords and bright plucks, soft claps and kick, "
              "hopeful and reassuring, major key, clean professional mix, no vocals, 100 bpm",
}
for name, sec in [(n, s) for n, s in zip(sys.argv[2::2], sys.argv[3::2])]:
    inp = proc(text=[P[name]], padding=True, return_tensors="pt")
    tokens = int(float(sec) * 50) + 10
    with torch.no_grad():
        a = model.generate(**inp, do_sample=True, guidance_scale=3.5, max_new_tokens=tokens)
    sr = model.config.audio_encoder.sampling_rate
    sf.write(f"{sys.argv[1]}_{name}.wav", a[0, 0].numpy(), sr)
    print(name, sec, "done", flush=True)
