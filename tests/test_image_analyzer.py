"""
CivicSight ImageAnalyzer test suite.

These tests are deterministic and do not download or execute a real
Hugging Face model. The service's processor/model slots are replaced with
small fakes so the tests focus on CivicSight behavior and API contracts.
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
import torch
from PIL import Image

import app.services.image_analyzer as image_analyzer_module

from app.services.image_analyzer import (
    ImageAnalysisError,
    ImageAnalyzer,
    InvalidImageError,
    VisionModelError,
    analyze_image,
    get_image_analyzer,
)


def create_test_image(
    image_format: str = "PNG",
    size: tuple[int, int] = (224, 224),
) -> bytes:
    image = Image.new("RGB", size, color=(120, 140, 160))
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


class FakeProcessor:
    def __init__(self):
        self.calls = []

    def __call__(self, *, images, return_tensors):
        self.calls.append(images)
        assert isinstance(images, Image.Image)
        assert return_tensors == "pt"
        return {
            "pixel_values": torch.zeros(
                (1, 3, 224, 224),
                dtype=torch.float32,
            )
        }


class FakeConfig:
    id2label = {
        0: "road",
        1: "pothole",
        2: "cracked pavement",
        3: "street",
        4: "building",
    }


class FakeModel:
    def __init__(self, logits: torch.Tensor | None = None):
        self.config = FakeConfig()
        self._logits = (
            logits
            if logits is not None
            else torch.tensor(
                [[5.0, 3.0, 1.0, 0.5, 0.1]],
                dtype=torch.float32,
            )
        )
        self.to_called_with = None
        self.eval_called = False
        self.called = False

    def to(self, device):
        self.to_called_with = device
        return self

    def eval(self):
        self.eval_called = True
        return self

    def __call__(self, **inputs):
        self.called = True
        assert "pixel_values" in inputs
        return SimpleNamespace(logits=self._logits)


class FakeProcessorFailure:
    def __call__(self, **kwargs):
        raise RuntimeError("processor failure")


class FakeModelFailure(FakeModel):
    def __call__(self, **inputs):
        raise RuntimeError("model inference failure")


def make_mocked_analyzer(
    *,
    logits: torch.Tensor | None = None,
) -> ImageAnalyzer:
    analyzer = ImageAnalyzer(model_name="test/model")
    analyzer._processor = FakeProcessor()
    analyzer._model = FakeModel(logits=logits)
    return analyzer


# ============================================================
# Initialization
# ============================================================

def test_analyzer_initializes_with_cpu():
    analyzer = ImageAnalyzer()
    assert analyzer.device.type == "cpu"
    assert analyzer.model_name == ImageAnalyzer.DEFAULT_MODEL_NAME


def test_analyzer_rejects_non_cpu_device():
    with pytest.raises(ValueError, match="CPU inference only|supports CPU inference only"):
        ImageAnalyzer(device="cuda")


def test_analyzer_accepts_custom_model_name():
    analyzer = ImageAnalyzer(model_name="test/custom-model")
    assert analyzer.model_name == "test/custom-model"


def test_analyzer_does_not_load_model_during_construction():
    analyzer = ImageAnalyzer(model_name="test/model")
    assert analyzer._model is None


def test_analyzer_does_not_load_processor_during_construction():
    analyzer = ImageAnalyzer(model_name="test/model")
    assert analyzer._processor is None


# ============================================================
# Image validation/loading
# ============================================================

def test_validate_image_bytes_accepts_valid_bytes():
    ImageAnalyzer.validate_image_bytes(create_test_image())


def test_validate_image_bytes_rejects_empty_bytes():
    with pytest.raises(InvalidImageError, match="Image data is empty"):
        ImageAnalyzer.validate_image_bytes(b"")


def test_validate_image_bytes_rejects_oversized_input(monkeypatch):
    monkeypatch.setattr(ImageAnalyzer, "MAX_IMAGE_SIZE_BYTES", 10)
    with pytest.raises(InvalidImageError):
        ImageAnalyzer.validate_image_bytes(b"x" * 11)


@pytest.mark.parametrize("image_format", ["PNG", "JPEG", "WEBP", "BMP"])
def test_load_image_supports_common_formats(image_format):
    image = ImageAnalyzer.load_image(
        create_test_image(image_format=image_format)
    )
    assert isinstance(image, Image.Image)
    assert image.mode == "RGB"


def test_load_image_preserves_dimensions():
    image = ImageAnalyzer.load_image(
        create_test_image(size=(320, 180))
    )
    assert image.size == (320, 180)


def test_load_image_converts_rgba_to_rgb():
    image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    loaded = ImageAnalyzer.load_image(buffer.getvalue())

    assert loaded.mode == "RGB"


def test_load_image_converts_grayscale_to_rgb():
    image = Image.new("L", (100, 100), color=100)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    loaded = ImageAnalyzer.load_image(buffer.getvalue())

    assert loaded.mode == "RGB"


def test_load_image_rejects_corrupt_bytes():
    with pytest.raises(InvalidImageError, match="valid supported image"):
        ImageAnalyzer.load_image(b"not-an-image")


def test_load_image_rejects_empty_bytes():
    with pytest.raises(InvalidImageError):
        ImageAnalyzer.load_image(b"")


# ============================================================
# Prediction
# ============================================================

def test_predict_returns_list():
    analyzer = make_mocked_analyzer()
    result = analyzer.predict(Image.new("RGB", (224, 224)))
    assert isinstance(result, list)


def test_predict_returns_at_most_five_predictions():
    analyzer = make_mocked_analyzer(
        logits=torch.arange(20, dtype=torch.float32).reshape(1, 20)
    )
    result = analyzer.predict(Image.new("RGB", (224, 224)))
    assert len(result) <= 5


def test_predict_returns_sorted_predictions():
    analyzer = make_mocked_analyzer()
    result = analyzer.predict(Image.new("RGB", (224, 224)))

    confidences = [confidence for _, confidence in result]
    assert confidences == sorted(confidences, reverse=True)


def test_predict_returns_string_labels():
    analyzer = make_mocked_analyzer()
    result = analyzer.predict(Image.new("RGB", (224, 224)))
    assert all(isinstance(label, str) for label, _ in result)


def test_predict_returns_float_confidences():
    analyzer = make_mocked_analyzer()
    result = analyzer.predict(Image.new("RGB", (224, 224)))
    assert all(isinstance(confidence, float) for _, confidence in result)


def test_predict_confidence_is_between_zero_and_one():
    analyzer = make_mocked_analyzer()
    result = analyzer.predict(Image.new("RGB", (224, 224)))
    assert all(0.0 <= confidence <= 1.0 for _, confidence in result)


def test_predict_converts_non_rgb_image():
    processor = FakeProcessor()
    analyzer = make_mocked_analyzer()
    analyzer._processor = processor

    analyzer.predict(Image.new("L", (64, 64), color=100))

    assert len(processor.calls) == 1
    assert processor.calls[0].mode == "RGB"


def test_predict_calls_model():
    analyzer = make_mocked_analyzer()
    analyzer.predict(Image.new("RGB", (224, 224)))
    assert analyzer._model.called is True


def test_predict_processor_failure_becomes_vision_model_error():
    analyzer = make_mocked_analyzer()
    analyzer._processor = FakeProcessorFailure()

    with pytest.raises(VisionModelError, match="Image inference failed"):
        analyzer.predict(Image.new("RGB", (224, 224)))


def test_predict_model_failure_becomes_vision_model_error():
    analyzer = make_mocked_analyzer()
    analyzer._model = FakeModelFailure()

    with pytest.raises(VisionModelError, match="Image inference failed"):
        analyzer.predict(Image.new("RGB", (224, 224)))


# ============================================================
# Keyword mapping
# ============================================================

@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("road", "road"),
        ("Highway", "road"),
        ("asphalt road", "road"),
        ("street", "road"),
        ("bridge", "bridge"),
        ("drainage ditch", "drainage"),
        ("street lamp", "streetlight"),
        ("lamp post", "streetlight"),
        ("building", "building"),
    ],
)
def test_find_keyword_match(label, expected):
    result = ImageAnalyzer._find_keyword_match(
        label,
        ImageAnalyzer.INFRASTRUCTURE_KEYWORDS,
    )
    assert result == expected


def test_find_keyword_match_is_case_insensitive():
    result = ImageAnalyzer._find_keyword_match(
        "BROKEN STREETLIGHT",
        ImageAnalyzer.INFRASTRUCTURE_KEYWORDS,
    )
    assert result == "streetlight"


def test_find_keyword_match_normalizes_underscores():
    result = ImageAnalyzer._find_keyword_match(
        "street_light",
        ImageAnalyzer.INFRASTRUCTURE_KEYWORDS,
    )
    assert result == "streetlight"


def test_find_keyword_match_returns_none_for_unknown_label():
    result = ImageAnalyzer._find_keyword_match(
        "airplane",
        ImageAnalyzer.INFRASTRUCTURE_KEYWORDS,
    )
    assert result is None


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("pothole", "pothole"),
        ("deep crack", "crack"),
        ("damaged pavement", "surface damage"),
        ("broken road", "surface damage"),
        ("construction", "construction activity"),
    ],
)
def test_issue_keyword_mapping(label, expected):
    result = ImageAnalyzer._find_keyword_match(
        label,
        ImageAnalyzer.ISSUE_KEYWORDS,
    )
    assert result == expected


# ============================================================
# Inference helpers
# ============================================================

def test_infer_infrastructure_from_predictions():
    result = ImageAnalyzer._infer_infrastructure(
        [("pothole", 0.90), ("road", 0.80)]
    )
    assert result == "Road"


def test_infer_infrastructure_uses_prediction_order():
    result = ImageAnalyzer._infer_infrastructure(
        [("bridge", 0.60), ("road", 0.95)]
    )
    assert result == "Bridge"


def test_infer_infrastructure_has_safe_fallback():
    result = ImageAnalyzer._infer_infrastructure(
        [("airplane", 0.90)]
    )
    assert result == "Infrastructure"


@pytest.mark.parametrize(
    ("predictions", "expected"),
    [
        ([("pothole", 0.90)], "pothole"),
        ([("cracked pavement", 0.90)], "crack"),
        ([("damaged road", 0.90)], "surface damage"),
        ([("construction site", 0.90)], "construction activity"),
    ],
)
def test_infer_issue(predictions, expected):
    result = ImageAnalyzer._infer_issue(predictions)
    assert result == expected


def test_infer_issue_has_safe_fallback():
    result = ImageAnalyzer._infer_issue([("airplane", 0.90)])
    assert result == "Visible infrastructure condition"


@pytest.mark.parametrize(
    "issue",
    [
        "pothole",
        "crack",
        "surface damage",
        "damaged structure",
        "broken streetlight",
        "deteriorated pavement",
    ],
)
def test_infer_condition_returns_poor_for_damage(issue):
    result = ImageAnalyzer._infer_condition(issue, [])
    assert result == "Poor"


def test_infer_condition_detects_good_prediction():
    result = ImageAnalyzer._infer_condition(
        "Visible infrastructure condition",
        [("clean road", 0.90)],
    )
    assert result == "Good"


def test_infer_condition_detects_fair_prediction():
    result = ImageAnalyzer._infer_condition(
        "Visible infrastructure condition",
        [("worn road", 0.90)],
    )
    assert result == "Fair"


def test_infer_condition_defaults_to_fair():
    result = ImageAnalyzer._infer_condition(
        "Visible infrastructure condition",
        [("airplane", 0.90)],
    )
    assert result == "Fair"


@pytest.mark.parametrize(
    ("condition", "confidence", "expected"),
    [
        ("Poor", 0.0, "Medium"),
        ("Poor", 0.69, "Medium"),
        ("Poor", 0.70, "High"),
        ("Poor", 1.0, "High"),
        ("Fair", 0.50, "Medium"),
        ("Good", 0.95, "Low"),
        ("Unknown", 0.95, "Low"),
        ("Critical", 0.95, "Low"),
    ],
)
def test_infer_severity(condition, confidence, expected):
    result = ImageAnalyzer._infer_severity(
        condition=condition,
        confidence=confidence,
    )
    assert result == expected


# ============================================================
# Detection
# ============================================================

def test_build_detection_creates_valid_detection():
    detection = ImageAnalyzer._build_detection(
        label="pothole",
        confidence=0.85,
    )
    assert detection.label == "pothole"
    assert detection.confidence == 0.85


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (-1.0, 0.0),
        (0.0, 0.0),
        (0.5, 0.5),
        (1.0, 1.0),
        (2.0, 1.0),
    ],
)
def test_build_detection_clamps_confidence(confidence, expected):
    detection = ImageAnalyzer._build_detection(
        label="test",
        confidence=confidence,
    )
    assert detection.confidence == expected


def test_detection_has_no_fake_bounding_box():
    detection = ImageAnalyzer._build_detection(
        label="pothole",
        confidence=0.85,
    )
    assert detection.x_min is None
    assert detection.y_min is None
    assert detection.x_max is None
    assert detection.y_max is None


# ============================================================
# End-to-end analysis
# ============================================================

def test_analyze_returns_valid_response():
    analyzer = make_mocked_analyzer()

    result = analyzer.analyze(
        create_test_image(),
        filename="road_damage.jpg",
        content_type="image/jpeg",
    )

    assert result.infrastructure
    assert result.detected_issue
    assert result.condition
    assert result.severity
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.detections) <= 5

    assert result.metadata["model"] == analyzer.model_name
    assert result.metadata["device"] == "cpu"
    assert result.metadata["image_width"] == 224
    assert result.metadata["image_height"] == 224
    assert result.metadata["filename"] == "road_damage.jpg"
    assert result.metadata["content_type"] == "image/jpeg"


def test_analyze_works_without_optional_metadata():
    analyzer = make_mocked_analyzer()

    result = analyzer.analyze(create_test_image())

    assert result.infrastructure
    assert result.detected_issue
    assert result.condition
    assert result.severity
    assert "filename" not in result.metadata
    assert "content_type" not in result.metadata


def test_analyze_sanitizes_filename_to_basename():
    analyzer = make_mocked_analyzer()

    result = analyzer.analyze(
        create_test_image(),
        filename=r"C:\private\folder\road.png",
    )

    assert result.metadata["filename"] == "road.png"


def test_analyze_rejects_invalid_image_before_inference():
    analyzer = make_mocked_analyzer()

    with pytest.raises(InvalidImageError):
        analyzer.analyze(b"not-an-image")

    assert analyzer._model.called is False


def test_analyze_rejects_empty_image_before_inference():
    analyzer = make_mocked_analyzer()

    with pytest.raises(InvalidImageError):
        analyzer.analyze(b"")

    assert analyzer._model.called is False


def test_analyze_raises_when_predictions_are_empty(monkeypatch):
    analyzer = make_mocked_analyzer()

    monkeypatch.setattr(
        analyzer,
        "predict",
        lambda image: [],
    )

    with pytest.raises(VisionModelError, match="no predictions"):
        analyzer.analyze(create_test_image())


# ============================================================
# API contract
# ============================================================

def test_analyze_response_is_pydantic_model():
    from app.models.image_models import ImageAnalysisResponse

    analyzer = make_mocked_analyzer()
    result = analyzer.analyze(create_test_image())

    assert isinstance(result, ImageAnalysisResponse)


def test_response_is_json_serializable():
    import json

    analyzer = make_mocked_analyzer()
    result = analyzer.analyze(
        create_test_image(),
        filename="test.png",
        content_type="image/png",
    )

    if hasattr(result, "model_dump"):
        payload = result.model_dump()
    else:
        payload = result.dict()

    encoded = json.dumps(payload)
    decoded = json.loads(encoded)

    assert decoded["infrastructure"]
    assert decoded["detected_issue"]
    assert decoded["condition"]
    assert decoded["severity"]
    assert isinstance(decoded["detections"], list)
    assert isinstance(decoded["metadata"], dict)


# ============================================================
# Convenience functions
# ============================================================

def test_get_image_analyzer_returns_singleton(monkeypatch):
    monkeypatch.setattr(
        image_analyzer_module,
        "_default_analyzer",
        None,
    )

    first = get_image_analyzer()
    second = get_image_analyzer()

    assert first is second
    assert isinstance(first, ImageAnalyzer)


def test_analyze_image_delegates_to_default_analyzer(monkeypatch):
    class FakeAnalyzer:
        def analyze(
            self,
            image_bytes,
            *,
            filename=None,
            content_type=None,
        ):
            return {
                "length": len(image_bytes),
                "filename": filename,
                "content_type": content_type,
            }

    fake = FakeAnalyzer()

    monkeypatch.setattr(
        image_analyzer_module,
        "get_image_analyzer",
        lambda: fake,
    )

    result = analyze_image(
        b"abc",
        filename="test.png",
        content_type="image/png",
    )

    assert result == {
        "length": 3,
        "filename": "test.png",
        "content_type": "image/png",
    }


# ============================================================
# Exceptions
# ============================================================

def test_invalid_image_error_inherits_base_error():
    assert issubclass(
        InvalidImageError,
        ImageAnalysisError,
    )


def test_vision_model_error_inherits_base_error():
    assert issubclass(
        VisionModelError,
        ImageAnalysisError,
    )


# ============================================================
# Determinism
# ============================================================

def test_predict_is_deterministic():
    analyzer = make_mocked_analyzer()
    image = Image.new("RGB", (224, 224))

    first = analyzer.predict(image)
    second = analyzer.predict(image)

    assert first == second


def test_analyze_is_deterministic():
    image_bytes = create_test_image()

    first = make_mocked_analyzer().analyze(image_bytes)
    second = make_mocked_analyzer().analyze(image_bytes)

    assert first.infrastructure == second.infrastructure
    assert first.detected_issue == second.detected_issue
    assert first.condition == second.condition
    assert first.severity == second.severity
    assert first.confidence == second.confidence


def test_predict_limits_results_to_top_five():
    logits = torch.arange(
        20,
        dtype=torch.float32,
    ).reshape(1, 20)

    analyzer = make_mocked_analyzer(logits=logits)

    predictions = analyzer.predict(
        Image.new("RGB", (224, 224))
    )

    assert len(predictions) == 5

    confidences = [
        confidence
        for _, confidence in predictions
    ]

    assert confidences == sorted(
        confidences,
        reverse=True,
    )