# Speech recognition evaluation

The benchmark accepts a JSON manifest containing only legally usable audio. The
repository does not include a usable evaluation dataset or transcripts and does
not fabricate results. Use the preparation workspace and empty template in
[`evaluation/`](../evaluation/) and
[`evaluation/dataset/manifests/manifest.template.json`](../evaluation/dataset/manifests/manifest.template.json).
Each sample must provide an SHA-256 checksum, language, reference transcript,
dataset name, and licence or consent provenance. `duration_seconds` and tags are
optional.

Use paths relative to the manifest:

```json
{
  "version": 1,
  "samples": [{
    "id": "sample-001",
    "audio_path": "audio/sample-001.wav",
    "checksum_sha256": "<64 lowercase hexadecimal characters>",
    "language": "en",
    "reference_transcript": "A verified transcript.",
    "duration_seconds": 2.4,
    "dataset": "Your licensed dataset",
    "license_or_consent": "License or consent record",
    "tags": ["clean"]
  }]
}
```

## Dataset preparation

Prepare 20–30 genuine recordings where you have permission to use the audio.
Include multiple speakers, more than one language when evaluating multilingual
claims, and a mixture of durations and speaking conditions where practical.
Have a human verify every reference transcript. Do not generate reference
transcripts with Whisper. Synthetic TTS audio may be used only when the exact
audio and source text are retained and the manifest identifies it as synthetic.

For each file:

1. Copy it into a dataset directory outside the application source if it is
   private or restricted.
2. Record its relative path, language, provenance, and human-verified text.
3. Measure or obtain its duration.
4. Generate its checksum:

```powershell
Get-FileHash .\audio\sample-001.wav -Algorithm SHA256
```

Do not commit private recordings, consent records, or restricted datasets.

## Controlled model comparison

The production default remains `small`. The benchmark selects one multilingual
`faster-whisper` model per process, loads it, runs all samples, and releases it
before another model is run. The available comparison sizes are `tiny`, `base`,
`small`, and `medium`; all use the `Systran/faster-whisper-*` multilingual model
family. The benchmark does not change the running API process configuration.

Run from `backend/`:

```text
python -m app.evaluation.benchmark --manifest path/to/manifest.json --model-size tiny --output results-tiny.json
python -m app.evaluation.benchmark --manifest path/to/manifest.json --model-size base --output results-base.json
python -m app.evaluation.benchmark --manifest path/to/manifest.json --model-size small --output results-small.json
python -m app.evaluation.benchmark --manifest path/to/manifest.json --model-size medium --output results-medium.json
```

Run only models supported by the available hardware. The `medium` model is
optional and may require substantially more memory. CSV output is also
available per model:

```text
python -m app.evaluation.benchmark --manifest path/to/manifest.json --model-size tiny --output results-tiny.csv --format csv
```

The JSON output records model and environment configuration, per-sample WER,
identifier, model-load time, per-sample audio duration, inference time,
end-to-end latency, and real-time factor (RTF = inference time / audio
duration). It also reports language groups with mean WER/CER and p50/p95
latency. Failed samples are retained in the output. Peak memory is recorded
when the host provides a reliable `resource` measurement; otherwise it is
`null`.

Normalization uses Unicode NFKC, case folding, punctuation and symbol
replacement with spaces, and whitespace collapsing. Unicode letters, numbers,
and combining marks are preserved; this includes Indic vowel signs and
viramas. No transliteration or diacritic removal is performed.

WER remains whitespace-token based and is therefore less meaningful when word
boundaries are not represented consistently across languages. CER is the
code-point error rate after the same normalization and is a complementary
metric, not grapheme-cluster CER. Grapheme-cluster segmentation is not
introduced without a maintained dependency and a separately versioned metric
contract.

The original Tiny/Base benchmark accuracy values were invalidated after the
normalization bug was found. Their raw hypotheses, latency, and RTF observations
remain preserved in `evaluation/dataset/results/`; they must not be compared
with corrected accuracy values as if they used the same metric definition.
The small-model initialization failure remains a resource diagnostic.

Benchmark infrastructure and mocked tests do not constitute real model
measurements. Model-load time is reported separately from warm per-sample
inference latency. Run against a licensed, verified dataset to obtain actual
results. Do not select a production model from one recording or a small
unbalanced dataset.
