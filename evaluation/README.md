# Multilingual evaluation dataset

This directory is a local workspace for preparing a small, reproducible
Whisper evaluation dataset. The repository does not include recordings,
transcripts, consent records, or benchmark results.

## Directory layout

```text
evaluation/
  dataset/
    audio/       # permitted recordings; do not add private files to Git
    manifests/   # completed manifest and the empty template
    results/     # JSON/CSV benchmark output
```

The initial target is 20–30 genuine recordings across English (`en`), Telugu
(`te`), Hindi (`hi`), and Malayalam (`ml`), subject to availability and
permission. Use multiple speakers and a mixture of duration and recording
conditions where practical. Fewer samples are acceptable when consent or
language availability is limited; record those limitations in the manifest
metadata or evaluation report.

## Add recordings

1. Obtain explicit permission or use a dataset whose license permits this
   evaluation. Keep consent or license evidence outside the repository when it
   contains personal information.
2. Copy permitted audio files into `dataset/audio/`, using stable names such
   as `en-speaker-01-001.wav`. Do not rename a file after its checksum is
   recorded.
3. Use a supported audio format: `.webm`, `.wav`, `.mp3`, `.m4a`, `.ogg`,
   `.mp4`, `.aac`, or `.flac`.
4. Record the speaker/language conditions with non-sensitive tags such as
   `clean`, `moderate-noise`, or `short`.

Do not download data automatically, commit private recordings, or use a
recording without documented permission.

## Create reference transcripts

Every `reference_transcript` must be manually verified against the recording
by a qualified human. Preserve the spoken words, language, and intended
orthography. Do not generate ground truth with Whisper or another ASR model.
Do not silently translate, paraphrase, or "correct" what was spoken.

Synthetic audio is out of scope for the initial dataset. If it is later used,
keep the exact source text and generated audio together and label the sample
as synthetic; it must not be presented as human-speech evidence.

## Manifest fields

Copy `dataset/manifests/manifest.template.json` to a new manifest, for example
`dataset/manifests/v1.json`. Paths are relative to the manifest file:
`../audio/example.wav` refers to `dataset/audio/example.wav`.

Each sample requires:

- `id`: unique stable identifier.
- `audio_path`: relative or absolute audio path.
- `checksum_sha256`: 64 lowercase hexadecimal SHA-256 characters.
- `language`: BCP-47-style identifier used consistently in the dataset:
  `en`, `te`, `hi`, or `ml`.
- `reference_transcript`: manually verified transcript.
- `dataset`: source dataset name/version or `local-consented-recordings`.
- `license_or_consent`: license name/URL or a consent-record identifier.

Optional fields:

- `duration_seconds`: positive number.
- `tags`: list of non-empty strings.

## Calculate and verify checksums

From the repository root:

```powershell
Get-FileHash .\evaluation\dataset\audio\en-speaker-01-001.wav -Algorithm SHA256
```

Copy the lowercase `Hash` value into `checksum_sha256`. After copying or
transferring files, run the validator again; it recomputes each checksum and
rejects missing or changed files.

## Validate the completed manifest

The empty template is intentionally not loadable because the application
schema requires at least one sample. After adding real entries, run:

```powershell
Set-Location .\backend
python -m app.evaluation.validate_manifest ..\evaluation\dataset\manifests\v1.json
```

This validates the JSON schema, resolves paths relative to the manifest, checks
that each audio file exists, and verifies its SHA-256 checksum. It does not
load model weights or run inference.

## Run the benchmark

Run models sequentially from `backend/`, writing results outside the manifest
directory:

```powershell
python -m app.evaluation.benchmark --manifest ..\evaluation\dataset\manifests\v1.json --model-size tiny --output ..\evaluation\dataset\results\results-tiny.json
python -m app.evaluation.benchmark --manifest ..\evaluation\dataset\manifests\v1.json --model-size base --output ..\evaluation\dataset\results\results-base.json
python -m app.evaluation.benchmark --manifest ..\evaluation\dataset\manifests\v1.json --model-size small --output ..\evaluation\dataset\results\results-small.json
```

`medium` is optional and should only be run when the CPU and memory capacity
are sufficient:

```powershell
python -m app.evaluation.benchmark --manifest ..\evaluation\dataset\manifests\v1.json --model-size medium --output ..\evaluation\dataset\results\results-medium.json
```

The benchmark uses the existing multilingual `faster-whisper` model family.
It does not change the production default, which remains `small`.

## Optional ViH Varnamala import

The target dataset is
`ViH-research-labs/ViH-Varnamala`. Its Hugging Face metadata declares CC BY
4.0, but access is gated: accept the dataset conditions on Hugging Face and
authenticate with a token before importing. The current published metadata
exposes only a `train` split, so the importer refuses it and will not create an
evaluation set from training data. If the publisher adds a dedicated
evaluation split, install the optional importer dependency and run:

```powershell
python -m pip install -r .\backend\requirements-evaluation.txt
$env:HF_TOKEN = "your-token"
Set-Location .\backend
python -m app.evaluation.import_vih_varnamala `
  --split validation `
  --revision main `
  --manifest ..\evaluation\dataset\manifests\vih-varnamala-v1.json `
  --audio-dir ..\evaluation\dataset\audio `
  --excluded ..\evaluation\dataset\manifests\vih-varnamala-excluded.json
python -m app.evaluation.validate_manifest `
  ..\evaluation\dataset\manifests\vih-varnamala-v1.json
```

The importer streams rows, selects five non-empty samples per `en`, `hi`, `te`,
and `ml`, preserves the native transcript, records the source ID/revision/split,
computes SHA-256 checksums, and writes excluded-row reasons. It does not load
Whisper weights or run a benchmark. Downloaded audio remains ignored by Git.

## Imported Kathbath subset

The current local subset was imported from
`ayush-shunyalabs/Indic_ASR_Eval` at revision
`7c1d7dde6aee30d98075522bc9ec9eb26898f6ab`, configuration `kathbath`, split
`test`. It contains five rows each for Hindi, Telugu, and Malayalam. The
compiled dataset is published under CC BY 4.0 and requires attribution to
ayush-shunyalabs and ViH Research Labs. The compilation identifies Kathbath as
an AI4Bharat source. AI4Bharat's upstream Kathbath page describes the dataset
packaging as CC0 while noting that it does not own all raw text rights;
preserve both notices and verify upstream terms before redistributing audio.

To reproduce the import:

```powershell
Set-Location .\backend
python -m app.evaluation.import_indic_asr_eval `
  --manifest ..\evaluation\dataset\manifests\v1.json `
  --audio-dir ..\evaluation\dataset\audio `
  --excluded ..\evaluation\dataset\manifests\v1-excluded.json
python -m app.evaluation.validate_manifest `
  ..\evaluation\dataset\manifests\v1.json
```

The manifest records the pinned revision, configuration, split, source row
identity, native-script transcript, duration, and SHA-256 checksum. The
excluded-row file records non-target-language rows encountered before the
target quotas were filled.
