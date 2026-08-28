"""
CivicSight video processing service.

Responsibilities:
- Validate video input.
- Open videos using OpenCV.
- Read video metadata.
- Select representative frames.
- Extract frames as JPEG bytes.
- Pass extracted frames to ImageAnalyzer when requested.
- Aggregate image-analysis results.

This module does not:
- define FastAPI routes
- call Groq
- calculate priority
- implement separate video AI
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PIL import Image

from app.models.image_models import ImageAnalysisResponse
from app.services.image_analyzer import (
    ImageAnalyzer,
    ImageAnalysisError,
    get_image_analyzer,
)

logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    """Base exception for video-processing failures."""


class InvalidVideoError(VideoProcessingError):
    """Raised when the supplied video cannot be opened or processed."""


@dataclass(frozen=True)
class VideoMetadata:
    """Basic metadata extracted from a video."""

    frame_count: int
    fps: float
    duration_seconds: float
    width: int
    height: int
    codec: str


@dataclass(frozen=True)
class VideoFrame:
    """A representative video frame."""

    index: int
    timestamp_seconds: float
    image_bytes: bytes


class VideoProcessor:
    """
    Process site videos by extracting representative frames.

    The processor deliberately does not implement a separate video
    recognition model. Extracted frames are passed to ImageAnalyzer.
    """

    DEFAULT_FRAME_COUNT = 5
    MAX_FRAME_COUNT = 30

    MAX_VIDEO_SIZE_BYTES = 200 * 1024 * 1024

    JPEG_QUALITY = 90

    def __init__(
        self,
        image_analyzer: ImageAnalyzer | None = None,
    ) -> None:
        """
        Initialize the video processor.

        Args:
            image_analyzer: Optional analyzer dependency.
                Supplying one makes testing easier.
        """
        self.image_analyzer = image_analyzer or get_image_analyzer()

    @staticmethod
    def validate_video_bytes(video_bytes: bytes) -> None:
        """Validate raw video bytes before writing them to OpenCV."""
        if not video_bytes:
            raise InvalidVideoError("Video data is empty.")

        if len(video_bytes) > VideoProcessor.MAX_VIDEO_SIZE_BYTES:
            raise InvalidVideoError(
                "Video exceeds the maximum supported size of 200 MB."
            )

    @staticmethod
    def _write_temporary_video(video_bytes: bytes) -> str:
        """
        Write video bytes to a temporary file.

        OpenCV's VideoCapture is more reliable with a filesystem path
        than with an in-memory BytesIO object, especially on Windows.
        """
        import os
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".mp4",
                delete=False,
            ) as temporary_file:
                temporary_file.write(video_bytes)
                return temporary_file.name
        except OSError as exc:
            logger.exception("Unable to create temporary video file.")
            raise VideoProcessingError(
                "Unable to prepare video for processing."
            ) from exc

    @staticmethod
    def _remove_temporary_file(path: str) -> None:
        """Safely remove a temporary video file."""
        import os

        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            logger.warning(
                "Unable to remove temporary video file: %s",
                path,
            )

    @staticmethod
    def _fourcc_to_string(codec_value: float) -> str:
        """Convert OpenCV FOURCC value into a readable string."""
        try:
            value = int(codec_value)

            chars = [
                chr((value >> 0) & 0xFF),
                chr((value >> 8) & 0xFF),
                chr((value >> 16) & 0xFF),
                chr((value >> 24) & 0xFF),
            ]

            result = "".join(chars)

            if all(32 <= ord(char) <= 126 for char in result):
                return result

        except (TypeError, ValueError):
            pass

        return "unknown"

    @staticmethod
    def _open_capture(video_path: str) -> cv2.VideoCapture:
        """Open a video using OpenCV."""
        capture = cv2.VideoCapture(video_path)

        if not capture.isOpened():
            capture.release()
            raise InvalidVideoError(
                "The supplied video could not be opened."
            )

        return capture

    def get_metadata(self, video_bytes: bytes) -> VideoMetadata:
        """
        Read basic video metadata.

        Raises:
            InvalidVideoError: If the video cannot be opened.
        """
        self.validate_video_bytes(video_bytes)

        temporary_path = self._write_temporary_video(video_bytes)
        capture: cv2.VideoCapture | None = None

        try:
            capture = self._open_capture(temporary_path)

            frame_count = int(
                capture.get(cv2.CAP_PROP_FRAME_COUNT)
            )

            fps = float(
                capture.get(cv2.CAP_PROP_FPS)
            )

            width = int(
                capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            )

            height = int(
                capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            )

            codec = self._fourcc_to_string(
                capture.get(cv2.CAP_PROP_FOURCC)
            )

            if frame_count <= 0:
                raise InvalidVideoError(
                    "Video contains no readable frames."
                )

            if width <= 0 or height <= 0:
                raise InvalidVideoError(
                    "Video has invalid dimensions."
                )

            if not np.isfinite(fps) or fps < 0:
                fps = 0.0

            if fps > 0:
                duration_seconds = frame_count / fps
            else:
                duration_seconds = 0.0

            return VideoMetadata(
                frame_count=frame_count,
                fps=fps,
                duration_seconds=duration_seconds,
                width=width,
                height=height,
                codec=codec,
            )

        except InvalidVideoError:
            raise

        except Exception as exc:
            logger.exception("Failed to read video metadata.")
            raise InvalidVideoError(
                "Unable to read video metadata."
            ) from exc

        finally:
            if capture is not None:
                capture.release()

            self._remove_temporary_file(temporary_path)

    @classmethod
    def _normalize_frame_count(
        cls,
        frame_count: int,
    ) -> int:
        """Validate and normalize requested representative-frame count."""
        if not isinstance(frame_count, int):
            raise ValueError(
                "frame_count must be an integer."
            )

        if frame_count < 1:
            raise ValueError(
                "frame_count must be at least 1."
            )

        return min(frame_count, cls.MAX_FRAME_COUNT)

    @staticmethod
    def _calculate_frame_indices(
        total_frames: int,
        frame_count: int,
    ) -> list[int]:
        """
        Calculate evenly distributed representative frame indices.

        For one requested frame, the middle frame is selected.
        For multiple frames, the first and last frames are included.
        """
        if total_frames <= 0:
            raise InvalidVideoError(
                "Video contains no readable frames."
            )

        if frame_count <= 1:
            return [total_frames // 2]

        if frame_count >= total_frames:
            return list(range(total_frames))

        indices = np.linspace(
            0,
            total_frames - 1,
            num=frame_count,
            dtype=np.int64,
        )

        return sorted(set(int(index) for index in indices))

    @classmethod
    def _encode_frame(
        cls,
        frame: np.ndarray,
    ) -> bytes:
        """Convert an OpenCV BGR frame to JPEG bytes."""
        if frame is None or frame.size == 0:
            raise InvalidVideoError(
                "An extracted video frame is empty."
            )

        try:
            success, encoded = cv2.imencode(
                ".jpg",
                frame,
                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    cls.JPEG_QUALITY,
                ],
            )

            if not success:
                raise InvalidVideoError(
                    "Unable to encode extracted video frame."
                )

            return encoded.tobytes()

        except InvalidVideoError:
            raise

        except Exception as exc:
            logger.exception("Failed to encode video frame.")
            raise VideoProcessingError(
                "Unable to encode extracted video frame."
            ) from exc

    def extract_frames(
        self,
        video_bytes: bytes,
        *,
        frame_count: int = DEFAULT_FRAME_COUNT,
    ) -> list[VideoFrame]:
        """
        Extract evenly distributed representative frames.

        Args:
            video_bytes: Raw video bytes.
            frame_count: Number of representative frames.

        Returns:
            List of VideoFrame objects.

        Raises:
            InvalidVideoError: If the video cannot be read.
        """
        self.validate_video_bytes(video_bytes)

        frame_count = self._normalize_frame_count(frame_count)

        temporary_path = self._write_temporary_video(video_bytes)
        capture: cv2.VideoCapture | None = None

        try:
            capture = self._open_capture(temporary_path)

            total_frames = int(
                capture.get(cv2.CAP_PROP_FRAME_COUNT)
            )

            fps = float(
                capture.get(cv2.CAP_PROP_FPS)
            )

            if total_frames <= 0:
                raise InvalidVideoError(
                    "Video contains no readable frames."
                )

            if not np.isfinite(fps) or fps < 0:
                fps = 0.0

            indices = self._calculate_frame_indices(
                total_frames=total_frames,
                frame_count=frame_count,
            )

            extracted_frames: list[VideoFrame] = []

            for index in indices:
                capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    index,
                )

                success, frame = capture.read()

                if not success or frame is None:
                    logger.warning(
                        "Unable to read video frame at index %s.",
                        index,
                    )
                    continue

                image_bytes = self._encode_frame(frame)

                if fps > 0:
                    timestamp_seconds = index / fps
                else:
                    timestamp_seconds = 0.0

                extracted_frames.append(
                    VideoFrame(
                        index=index,
                        timestamp_seconds=float(timestamp_seconds),
                        image_bytes=image_bytes,
                    )
                )

            if not extracted_frames:
                raise InvalidVideoError(
                    "No readable frames could be extracted from the video."
                )

            return extracted_frames

        except InvalidVideoError:
            raise

        except Exception as exc:
            logger.exception("Video frame extraction failed.")
            raise VideoProcessingError(
                "Unable to extract representative video frames."
            ) from exc

        finally:
            if capture is not None:
                capture.release()

            self._remove_temporary_file(temporary_path)

    @staticmethod
    def _aggregate_results(
        results: list[ImageAnalysisResponse],
    ) -> ImageAnalysisResponse:
        """
        Aggregate representative-frame analysis.

        The frame with the highest model confidence is used as the
        primary structured result. Metadata records how many frames
        were analyzed.

        This avoids inventing a second video-specific AI scoring system.
        """
        if not results:
            raise VideoProcessingError(
                "No image-analysis results are available."
            )

        primary = max(
            results,
            key=lambda result: result.confidence,
        )

        metadata: dict[str, Any] = dict(
            primary.metadata or {}
        )

        metadata["frames_analyzed"] = len(results)

        return primary.model_copy(
            update={
                "metadata": metadata,
            }
        )

    def analyze_video(
        self,
        video_bytes: bytes,
        *,
        frame_count: int = DEFAULT_FRAME_COUNT,
        filename: str | None = None,
    ) -> ImageAnalysisResponse:
        """
        Extract representative frames and analyze them.

        Each representative frame is passed to ImageAnalyzer.
        No separate video model is used.
        """
        frames = self.extract_frames(
            video_bytes,
            frame_count=frame_count,
        )

        results: list[ImageAnalysisResponse] = []

        for frame_number, frame in enumerate(frames):
            try:
                result = self.image_analyzer.analyze(
                    frame.image_bytes,
                    filename=filename,
                    content_type="image/jpeg",
                )

                metadata = dict(result.metadata or {})
                metadata["video_frame_index"] = frame.index
                metadata["video_frame_number"] = frame_number + 1
                metadata["video_timestamp_seconds"] = (
                    frame.timestamp_seconds
                )

                result = result.model_copy(
                    update={
                        "metadata": metadata,
                    }
                )

                results.append(result)

            except ImageAnalysisError:
                logger.warning(
                    "Image analysis failed for video frame %s.",
                    frame.index,
                    exc_info=True,
                )

        if not results:
            raise VideoProcessingError(
                "Video frames were extracted, but none could be analyzed."
            )

        return self._aggregate_results(results)


_default_video_processor: VideoProcessor | None = None


def get_video_processor() -> VideoProcessor:
    """
    Return the process-wide VideoProcessor instance.
    """
    global _default_video_processor

    if _default_video_processor is None:
        _default_video_processor = VideoProcessor()

    return _default_video_processor


def extract_video_frames(
    video_bytes: bytes,
    *,
    frame_count: int = VideoProcessor.DEFAULT_FRAME_COUNT,
) -> list[VideoFrame]:
    """
    Convenience function for future API integration.
    """
    return get_video_processor().extract_frames(
        video_bytes,
        frame_count=frame_count,
    )


def analyze_video(
    video_bytes: bytes,
    *,
    frame_count: int = VideoProcessor.DEFAULT_FRAME_COUNT,
    filename: str | None = None,
) -> ImageAnalysisResponse:
    """
    Convenience function for future API integration.
    """
    return get_video_processor().analyze_video(
        video_bytes,
        frame_count=frame_count,
        filename=filename,
    )