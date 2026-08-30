

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import torch
from PIL import Image, UnidentifiedImageError

from app.models.image_models import (
    Detection,
    ImageAnalysisResponse,
)


logger = logging.getLogger(__name__)


# Exceptions


class ImageAnalysisError(Exception):
    """Base exception for image-analysis failures."""


class InvalidImageError(ImageAnalysisError):
    """Raised when image data is invalid."""


class VisionModelError(ImageAnalysisError):
    """Raised when model loading or inference fails."""


# Image Analyzer


class ImageAnalyzer:
    """
    CPU-only CivicSight image analyzer.

    The public contract intentionally remains classification-based
    because the current roadmap uses a pretrained local vision
    classifier without custom training.

    Public methods:

        validate_image_bytes()
        load_image()
        predict()
        analyze()

    Compatibility helpers:

        _find_keyword_match()
        _infer_infrastructure()
        _infer_issue()
        _infer_condition()
        _infer_severity()
        _build_detection()
    """

    # Model configuration

    DEFAULT_MODEL_NAME = os.getenv(
        "CIVICSIGHT_VISION_MODEL",
        "google/vit-base-patch16-224",
    )

    MAX_IMAGE_SIZE_BYTES = (
        10 * 1024 * 1024
    )

    MAX_PREDICTIONS = 5

    MIN_ACCEPTABLE_CONFIDENCE = 0.35

    HIGH_CONFIDENCE_THRESHOLD = 0.70

    MEDIUM_CONFIDENCE_THRESHOLD = 0.50

    # Infrastructure keywords

    INFRASTRUCTURE_KEYWORDS: Dict[
        str,
        Tuple[str, ...],
    ] = {
        "road": (
            "road",
            "highway",
            "asphalt road",
            "street",
            "pavement",
            "paved road",
            "roadway",
        ),
        "bridge": (
            "bridge",
            "overpass",
            "flyover",
        ),
        "drainage": (
            "drainage",
            "drain",
            "gutter",
            "sewer",
            "ditch",
        ),
        "streetlight": (
            "streetlight",
            "street light",
            "street lamp",
            "lamp post",
            "lamp",
            "light pole",
        ),
        "building": (
            "building",
            "house",
            "structure",
        ),
        "water facility": (
            "water tank",
            "water tower",
            "reservoir",
            "water facility",
        ),
    }

    # Issue keywords

    ISSUE_KEYWORDS: Dict[
        str,
        Tuple[str, ...],
    ] = {
        "pothole": (
            "pothole",
            "pot hole",
        ),
        "crack": (
            "crack",
            "cracked",
            "cracking",
            "road crack",
        ),
        "surface damage": (
            "damaged pavement",
            "damaged road",
            "broken road",
            "road damage",
            "surface damage",
            "damaged surface",
            "broken pavement",
            "pavement damage",
        ),
        "construction activity": (
            "construction",
            "construction site",
            "construction activity",
            "road work",
            "roadwork",
            "work in progress",
        ),
        "damaged structure": (
            "damaged structure",
            "broken structure",
            "collapsed structure",
            "deteriorated structure",
        ),
        "broken streetlight": (
            "broken streetlight",
            "broken street light",
            "damaged streetlight",
            "damaged street light",
        ),
        "deteriorated pavement": (
            "deteriorated pavement",
            "worn pavement",
            "deteriorated road",
        ),
        "garbage accumulation": (
            "garbage",
            "trash",
            "waste",
            "dumpster",
            "rubbish",
            "litter",
        ),
        "damaged drainage": (
            "damaged drain",
            "broken drain",
            "damaged drainage",
            "broken drainage",
        ),
    }

    # Human-readable labels

    INFRASTRUCTURE_LABELS: Dict[
        str,
        str,
    ] = {
        "road": "Road",
        "bridge": "Bridge",
        "drainage": "Drainage",
        "streetlight": "Streetlight",
        "building": "Public Building",
        "water facility": "Water Facility",
        "road facility": "Road Facility",
        "other": "Other",
    }

    # Singleton state

    _default_analyzer: Optional[
        "ImageAnalyzer"
    ] = None

    _singleton_lock = Lock()

    # Initialization

    def __init__(
        self,
        model_name: Optional[str] = None,
        *,
        device: str = "cpu",
    ) -> None:
        """
        Initialize the analyzer.

        Model and processor are loaded lazily.
        """

        normalized_device = str(
            device
        ).strip().lower()

        if normalized_device != "cpu":
            raise ValueError(
                "ImageAnalyzer supports CPU inference only."
            )

        selected_model = (
            model_name
            if model_name is not None
            else self.DEFAULT_MODEL_NAME
        )

        selected_model = str(
            selected_model
        ).strip()

        if not selected_model:
            raise ValueError(
                "model_name cannot be empty."
            )

        self.model_name = selected_model

        # Keep torch.device because the existing tests
        # explicitly check analyzer.device.type.
        self.device = torch.device(
            "cpu"
        )

        # These attributes intentionally remain available.
        # The test suite injects fake processor/model objects
        # through them.
        self._processor: Any = None

        self._model: Any = None

        self._load_lock = Lock()

    # Model loading

    def _load_model(self) -> None:
        """
        Lazily load the Hugging Face vision model and processor.
        """

        if (
            self._processor is not None
            and self._model is not None
        ):
            return

        with self._load_lock:

            if (
                self._processor is not None
                and self._model is not None
            ):
                return

            try:
                from transformers import (
                    AutoImageProcessor,
                    AutoModelForImageClassification,
                )

                processor = (
                    AutoImageProcessor.from_pretrained(
                        self.model_name
                    )
                )

                model = (
                    AutoModelForImageClassification
                    .from_pretrained(
                        self.model_name
                    )
                )

                model = model.to(
                    self.device
                )

                model.eval()

                self._processor = processor
                self._model = model

                logger.info(
                    "Loaded CivicSight vision model: %s",
                    self.model_name,
                )

            except Exception as exc:

                self._processor = None
                self._model = None

                logger.exception(
                    "Failed to load image-analysis model."
                )

                raise VisionModelError(
                    "Unable to load the image-analysis model."
                ) from exc

    # Image validation

    @classmethod
    def validate_image_bytes(
        cls,
        image_bytes: bytes,
    ) -> bytes:
        """
        Validate raw image bytes.
        """

        if not isinstance(
            image_bytes,
            bytes,
        ):
            raise InvalidImageError(
                "Image data must be bytes."
            )

        if not image_bytes:
            raise InvalidImageError(
                "Image data is empty"
            )

        if len(image_bytes) > (
            cls.MAX_IMAGE_SIZE_BYTES
        ):
            raise InvalidImageError(
                "Image data exceeds the maximum allowed size."
            )

        return image_bytes

    # Image loading

    @classmethod
    def load_image(
        cls,
        image_bytes: bytes,
    ) -> Image.Image:
        """
        Decode image bytes and convert them to RGB.
        """

        cls.validate_image_bytes(
            image_bytes
        )

        try:

            with Image.open(
                io.BytesIO(
                    image_bytes
                )
            ) as image:

                image.load()

                return image.convert(
                    "RGB"
                ).copy()

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
        ) as exc:

            raise InvalidImageError(
                "Image data is not a valid supported image."
            ) from exc

    # Prediction

    def predict(
        self,
        image: Image.Image,
    ) -> List[
        Tuple[
            str,
            float,
        ]
    ]:
        """
        Run image classification.

        Returns at most five predictions:

            [
                ("label", confidence),
                ...
            ]

        This method intentionally returns two-tuples because
        the current CivicSight test/API contract is classification
        based.

        Bounding boxes are not fabricated.
        """

        if not isinstance(
            image,
            Image.Image,
        ):
            raise InvalidImageError(
                "predict() requires a PIL.Image.Image."
            )

        # The processor should always receive RGB.
        image = image.convert(
            "RGB"
        )

        self._load_model()

        if (
            self._processor is None
            or self._model is None
        ):
            raise VisionModelError(
                "Vision model is not initialized."
            )

        try:

            # Processor

            inputs = self._processor(
                images=image,
                return_tensors="pt",
            )

            # Move tensor inputs to CPU

            if isinstance(
                inputs,
                Mapping,
            ):

                inputs = {
                    key: (
                        value.to(
                            self.device
                        )
                        if hasattr(
                            value,
                            "to",
                        )
                        else value
                    )
                    for key, value
                    in inputs.items()
                }

            elif hasattr(
                inputs,
                "to",
            ):

                inputs = inputs.to(
                    self.device
                )

            # Inference

            with torch.no_grad():

                outputs = self._model(
                    **inputs
                )

            # Obtain logits

            logits = getattr(
                outputs,
                "logits",
                None,
            )

            if logits is None:

                logits = getattr(
                    outputs,
                    "logits_per_image",
                    None,
                )

            if logits is None:

                raise RuntimeError(
                    "Model returned no logits."
                )

            if not isinstance(
                logits,
                torch.Tensor,
            ):
                logits = torch.as_tensor(
                    logits
                )

            # Validate logits

            if logits.ndim == 1:

                logits = logits.unsqueeze(
                    0
                )

            if (
                logits.ndim != 2
                or logits.shape[0] == 0
                or logits.shape[1] == 0
            ):

                raise RuntimeError(
                    "Model returned invalid logits."
                )

            # Convert logits to probabilities

            probabilities = torch.softmax(
                logits[0],
                dim=-1,
            )

            # Model labels

            config = getattr(
                self._model,
                "config",
                None,
            )

            id2label = getattr(
                config,
                "id2label",
                {},
            )

            if not isinstance(
                id2label,
                Mapping,
            ):
                id2label = {}

            # Sort highest confidence first

            values, indices = torch.sort(
                probabilities,
                descending=True,
            )

            predictions: List[
                Tuple[
                    str,
                    float,
                ]
            ] = []

            for value, index in zip(
                values.tolist(),
                indices.tolist(),
            ):

                numeric_index = int(
                    index
                )

                label = id2label.get(
                    numeric_index,
                    id2label.get(
                        str(numeric_index),
                        f"class_{numeric_index}",
                    ),
                )

                confidence = float(
                    value
                )

                confidence = max(
                    0.0,
                    min(
                        1.0,
                        confidence,
                    ),
                )

                predictions.append(
                    (
                        str(label),
                        confidence,
                    )
                )

                if len(predictions) >= (
                    self.MAX_PREDICTIONS
                ):
                    break

            return predictions

        except VisionModelError:
            raise

        except Exception as exc:

            logger.exception(
                "Image inference failed."
            )

            raise VisionModelError(
                "Image inference failed"
            ) from exc

    # Keyword matching

    @staticmethod
    def _find_keyword_match(
        label: str,
        keyword_map: Mapping[
            str,
            Sequence[str],
        ],
    ) -> Optional[str]:
        """
        Find the most specific keyword match.

        Matching:
        - case-insensitive
        - underscore-normalized
        - whitespace-normalized
        - substring-based
        - longest keyword wins
        """

        if label is None:
            return None

        normalized_label = str(
            label
        ).strip().lower()

        normalized_label = (
            normalized_label.replace(
                "_",
                " ",
            )
        )

        normalized_label = " ".join(
            normalized_label.split()
        )

        matches: List[
            Tuple[int, str]
        ] = []

        for category, keywords in (
            keyword_map.items()
        ):

            for keyword in keywords:

                normalized_keyword = str(
                    keyword
                ).strip().lower()

                normalized_keyword = (
                    normalized_keyword.replace(
                        "_",
                        " ",
                    )
                )

                normalized_keyword = " ".join(
                    normalized_keyword.split()
                )

                if not normalized_keyword:
                    continue

                if normalized_keyword in (
                    normalized_label
                ):

                    matches.append(
                        (
                            len(
                                normalized_keyword
                            ),
                            category,
                        )
                    )

        if not matches:
            return None

        matches.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return matches[0][1]

    # Infrastructure inference

    @classmethod
    def _infer_infrastructure(
        cls,
        predictions: Sequence[
            Tuple[
                str,
                float,
            ]
        ],
    ) -> str:
        """
        Infer infrastructure category from predictions.
        """

        if not predictions:
            return "Infrastructure"

        for label, _confidence in predictions:

            match = cls._find_keyword_match(
                label,
                cls.INFRASTRUCTURE_KEYWORDS,
            )

            if match is not None:

                return cls.INFRASTRUCTURE_LABELS.get(
                    match,
                    match.capitalize(),
                )

        # Road-related issue labels imply road
        # infrastructure.
        for label, _confidence in predictions:

            issue_match = (
                cls._find_keyword_match(
                    label,
                    cls.ISSUE_KEYWORDS,
                )
            )

            if issue_match in {
                "pothole",
                "crack",
                "surface damage",
                "deteriorated pavement",
                "construction activity",
            }:

                return "Road"

        return "Infrastructure"

    # Issue inference

    @classmethod
    def _infer_issue(
        cls,
        predictions: Sequence[
            Tuple[
                str,
                float,
            ]
        ],
    ) -> str:
        """
        Infer the primary infrastructure issue.
        """

        if not predictions:
            return (
                "Visible infrastructure condition"
            )

        for label, _confidence in predictions:

            match = cls._find_keyword_match(
                label,
                cls.ISSUE_KEYWORDS,
            )

            if match is not None:
                return match

        return (
            "Visible infrastructure condition"
        )

    # Condition inference

    @classmethod
    def _infer_condition(
        cls,
        issue: str,
        predictions: Sequence[
            Tuple[
                str,
                float,
            ]
        ],
    ) -> str:
        """
        Infer coarse infrastructure condition.
        """

        normalized_issue = (
            str(issue)
            .strip()
            .lower()
            .replace(
                "_",
                " ",
            )
        )

        damage_issues = {
            "pothole",
            "crack",
            "surface damage",
            "damaged structure",
            "broken streetlight",
            "deteriorated pavement",
            "damaged drainage",
        }

        if normalized_issue in damage_issues:
            return "Poor"

        if normalized_issue == (
            "garbage accumulation"
        ):
            return "Fair"

        for label, _confidence in predictions:

            normalized_label = (
                str(label)
                .strip()
                .lower()
                .replace(
                    "_",
                    " ",
                )
            )

            if any(
                keyword in normalized_label
                for keyword in (
                    "clean",
                    "good",
                    "new",
                    "well maintained",
                    "well-maintained",
                )
            ):
                return "Good"

            if any(
                keyword in normalized_label
                for keyword in (
                    "worn",
                    "fair",
                    "aging",
                    "aged",
                    "moderate",
                    "wear",
                )
            ):
                return "Fair"

        return "Fair"

    # Severity inference

    @staticmethod
    def _infer_severity(
        *,
        condition: str,
        confidence: float,
    ) -> str:
        """
        Infer initial visual severity.

        Rules:

            Poor + confidence >= 0.70 -> High
            Poor + confidence <  0.70 -> Medium
            Fair + confidence >= 0.50 -> Medium
            Fair + confidence <  0.50 -> Low
            Everything else            -> Low
        """

        normalized_condition = (
            str(condition)
            .strip()
            .lower()
        )

        try:
            numeric_confidence = float(
                confidence
            )
        except (
            TypeError,
            ValueError,
        ):
            numeric_confidence = 0.0

        numeric_confidence = max(
            0.0,
            min(
                1.0,
                numeric_confidence,
            ),
        )

        if normalized_condition == "poor":

            if (
                numeric_confidence
                >= 0.70
            ):
                return "High"

            return "Medium"

        if normalized_condition == "fair":

            if (
                numeric_confidence
                >= 0.50
            ):
                return "Medium"

            return "Low"

        return "Low"

    # Detection builder

    @staticmethod
    def _build_detection(
        label: str,
        confidence: float,
        bounding_box: Optional[
            Tuple[
                float,
                float,
                float,
                float,
            ]
        ] = None,
    ) -> Detection:
        """
        Build a classification Detection.

        Bounding boxes are intentionally ignored unless
        explicitly supplied.

        The default classification path produces no fake
        bounding-box coordinates.
        """

        try:
            numeric_confidence = float(
                confidence
            )
        except (
            TypeError,
            ValueError,
        ):
            numeric_confidence = 0.0

        numeric_confidence = max(
            0.0,
            min(
                1.0,
                numeric_confidence,
            ),
        )

        # Current roadmap/model is classification based.
        # Do not fabricate coordinates.
        if bounding_box is None:

            return Detection(
                label=str(label),
                confidence=numeric_confidence,
                x_min=None,
                y_min=None,
                x_max=None,
                y_max=None,
            )

        # Defensive support for future explicitly supplied
        # coordinates while keeping classification behavior
        # unchanged.
        try:

            x_min, y_min, x_max, y_max = (
                float(value)
                for value in bounding_box
            )

        except (
            TypeError,
            ValueError,
        ):

            return Detection(
                label=str(label),
                confidence=numeric_confidence,
                x_min=None,
                y_min=None,
                x_max=None,
                y_max=None,
            )

        x_min = max(
            0.0,
            min(
                1.0,
                x_min,
            ),
        )

        y_min = max(
            0.0,
            min(
                1.0,
                y_min,
            ),
        )

        x_max = max(
            0.0,
            min(
                1.0,
                x_max,
            ),
        )

        y_max = max(
            0.0,
            min(
                1.0,
                y_max,
            ),
        )

        if x_min > x_max:
            x_min, x_max = (
                x_max,
                x_min,
            )

        if y_min > y_max:
            y_min, y_max = (
                y_max,
                y_min,
            )

        return Detection(
            label=str(label),
            confidence=numeric_confidence,
            x_min=x_min,
            y_min=y_min,
            x_max=x_max,
            y_max=y_max,
        )

    # Full analysis

    def analyze(
        self,
        image_bytes: bytes,
        *,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> ImageAnalysisResponse:
        """
        Analyze an infrastructure image.
        """

        image = self.load_image(
            image_bytes
        )

        predictions = self.predict(
            image
        )

        if not predictions:

            raise VisionModelError(
                "no predictions"
            )

        # Primary prediction

        primary_label = str(
            predictions[0][0]
        )

        primary_confidence = float(
            predictions[0][1]
        )

        # Infrastructure

        infrastructure = (
            self._infer_infrastructure(
                predictions
            )
        )

        # Issue

        detected_issue = (
            self._infer_issue(
                predictions
            )
        )

        # Condition

        condition = (
            self._infer_condition(
                detected_issue,
                predictions,
            )
        )

        # Low-confidence protection

        if (
            primary_confidence
            < self.MIN_ACCEPTABLE_CONFIDENCE
        ):

            detected_issue = (
                "Visible infrastructure condition"
            )

        severity = self._infer_severity(
            condition=condition,
            confidence=primary_confidence,
        )

        # Detections

        detections = [
            self._build_detection(
                label=label,
                confidence=confidence,
            )
            for label, confidence in predictions[
                : self.MAX_PREDICTIONS
            ]
        ]

        # Metadata

        metadata: Dict[
            str,
            Any,
        ] = {
            "model": self.model_name,
            "device": self.device.type,
            "image_width": image.width,
            "image_height": image.height,
            "analysis_type": (
                "image_classification"
            ),
            "bounding_boxes_available": False,
            "top_model_label": primary_label,
        }

        # Optional filename

        if filename is not None:

            safe_filename = str(
                filename
            )

            # Handle both Windows and POSIX path
            # separators so API metadata never exposes
            # the user's local directory structure.
            safe_filename = (
                safe_filename
                .replace("\\", "/")
            )

            safe_filename = Path(
                safe_filename
            ).name

            if safe_filename:
                metadata[
                    "filename"
                ] = safe_filename

        # Optional content type

        if content_type is not None:

            metadata[
                "content_type"
            ] = str(
                content_type
            )

        # Validated response

        return ImageAnalysisResponse(
            infrastructure=infrastructure,
            detected_issue=detected_issue,
            condition=condition,
            confidence=primary_confidence,
            severity=severity,
            detections=detections,
            metadata=metadata,
        )


# Singleton


_default_analyzer: Optional[
    ImageAnalyzer
] = None


def get_image_analyzer() -> ImageAnalyzer:
    """
    Return the process-wide ImageAnalyzer singleton.
    """

    global _default_analyzer

    if _default_analyzer is not None:
        return _default_analyzer

    with ImageAnalyzer._singleton_lock:

        if _default_analyzer is None:

            _default_analyzer = ImageAnalyzer()

    return _default_analyzer


# Convenience API


def analyze_image(
    image_bytes: bytes,
    *,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
) -> ImageAnalysisResponse:
    """
    Analyze an image using the process-wide analyzer.
    """

    return get_image_analyzer().analyze(
        image_bytes,
        filename=filename,
        content_type=content_type,
    )


# Public exports



__all__ = [
    "ImageAnalysisError",
    "InvalidImageError",
    "VisionModelError",
    "ImageAnalyzer",
    "get_image_analyzer",
    "analyze_image",
]