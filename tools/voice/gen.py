"""Zero-shot voice clone with Malaysian F5-TTS v2. usage: gen.py <ref> <takes> [ids...]"""
import sys, os, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import torch
from f5_tts.api import F5TTS
from lines import LINES

torch.set_num_threads(4)
REFS = {
    "A": ("ref/refA.wav", "untuk cover beban komitmen dia, dan kerana dia seorang breadwinner of the family. "
                          "Tunggu apa lagi, dapatkan konsultasi percuma daripada saya."),
    "B": ("ref/refB.wav", "Seorang doktor, lelaki umur tiga puluh dua tahun, tidak merokok, apply hibah sejuta ini "
                          "dengan caruman RM seratus tiga puluh sebulan sahaja."),
}
ref_key, takes = sys.argv[1], int(sys.argv[2])
only = set(sys.argv[3:])
M = "/home/user/work/models"
tts = F5TTS(model="F5TTS_Base", ckpt_file=f"{M}/v2_model_last.pt", vocab_file=f"{M}/vocab.txt", device="cpu")
ref_wav, ref_txt = REFS[ref_key]
os.makedirs("takes", exist_ok=True)
for lid, text in LINES:
    if only and lid not in only: continue
    for k in range(takes):
        out = f"takes/{lid}_{ref_key}{k}.wav"
        if os.path.exists(out): continue
        t0 = time.time()
        tts.infer(ref_file=ref_wav, ref_text=ref_txt, gen_text=text, file_wave=out,
                  seed=100 + k * 17, nfe_step=32, speed=1.0, remove_silence=False, show_info=lambda *a: None)
        print(out, f"{time.time() - t0:.1f}s", flush=True)
