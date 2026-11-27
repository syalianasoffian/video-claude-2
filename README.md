# KeyMan Policy — "3 Kerisauan Business Owner" (HyperFrames)

Vertical 1080×1920 video built with HyperFrames from the infographic, voiced with a clone of the
owner's voice (Malaysian F5-TTS v2, reference taken from the previous Hibah Takaful video after Demucs vocal separation).

- `keyman/` — HyperFrames project (`index.html` root, `compositions/*.html` scenes, `assets/`).
  Preview: `npx hyperframes preview`; render: `npx hyperframes render -o out.mp4`.
- `tools/voice/` — script lines, TTS generation, assembly, alignment and the generator for `index.html`,
  `assets/cues.js` and `compositions/captions.html` (`build.py`).
- `tools/audio/` — layered SFX synthesis and MusicGen music bed.
- `preview/` — draft render for review.
