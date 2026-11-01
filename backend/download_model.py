from faster_whisper import WhisperModel

# Import the same settings used by the FastAPI application so a default Docker
# build pre-downloads the actual default runtime model (`small`).
from app.core.config import settings

model_size = settings.model_size
print(f"Pre-downloading Whisper model: {model_size}...")
WhisperModel(model_size, device=settings.device, compute_type=settings.compute_type)
print("Download complete!")
