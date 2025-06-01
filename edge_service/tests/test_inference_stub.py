import numpy as np
import pytest
from inference import EdgeInference

def test_engine_load_missing(tmp_path):
    # Pass an empty directory to force FileNotFoundError
    with pytest.raises(FileNotFoundError):
        EdgeInference(model_dir=str(tmp_path))

def test_infer_methods_return_types(tmp_path):
    # Create dummy files
    (tmp_path / "object_detection.trt").write_text("")
    (tmp_path / "activity_recognition.trt").write_text("")
    engine = EdgeInference(model_dir=str(tmp_path))
    tensor = np.zeros((3, 224, 224), dtype=np.float32)
    objs = engine.infer_objects(tensor)
    act = engine.infer_activity(tensor)
    assert isinstance(objs, list)
    assert isinstance(act, str)