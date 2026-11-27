"""Word-level transcription with HF Whisper. usage: transcribe.py in.wav out.json"""
import sys, json, warnings
warnings.filterwarnings("ignore")
import torch, librosa
from transformers import pipeline

torch.set_num_threads(4)
pipe = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cpu")
for path, out in zip(sys.argv[1::2], sys.argv[2::2]):
    y, _ = librosa.load(path, sr=16000)
    r = pipe(y, return_timestamps="word", generate_kwargs={"language": "malay", "task": "transcribe"}, chunk_length_s=30)
    words = [{"w": c["text"].strip(), "s": c["timestamp"][0], "e": c["timestamp"][1]} for c in r["chunks"]]
    json.dump({"text": r["text"], "words": words}, open(out, "w"), ensure_ascii=False, indent=0)
    print(path, "|", r["text"])
