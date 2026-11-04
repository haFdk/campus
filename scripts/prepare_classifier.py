"""Explicit official download, pinned revision. Never invoked by server startup."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == '__main__':
    from huggingface_hub import snapshot_download
    from app.services.classification import MODEL_ID, MODEL_REVISION
    from app.config import Config
    target = Config.CLASSIFICATION_MODEL_PATH
    print('Downloading pinned mDeBERTa (~558 MB weights, ~579 MB total) to', target, flush=True)
    snapshot_download(MODEL_ID, revision=MODEL_REVISION, local_dir=target,
                      allow_patterns=['config.json', 'model.safetensors', '*token*.json',
                                      'spm.model', 'README.md'], max_workers=2)
    print('Download complete. Run scripts/evaluate_classifier.py to verify offline inference.')
