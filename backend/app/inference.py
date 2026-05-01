"""
RescueVision Edge - ONNX Inference Engine
"""

from __future__ import annotations

import time
from typing import Dict, List, Tuple

import cv2
import numpy as np
import onnxruntime as ort


class RescueVisionInference:
    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        input_size: int = 640,
    ) -> None:
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size

        available = ort.get_available_providers()
        preferred = ["CPUExecutionProvider"]
        self.providers = [p for p in preferred if p in available] or available

        self.session = ort.InferenceSession(self.model_path, providers=self.providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def update_config(self, conf_threshold: float, iou_threshold: float, input_size: int) -> None:
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size

    def run(self, image_path: str) -> Tuple[List[Dict], float, int, int]:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to read image: {image_path}")

        img_h, img_w = image.shape[:2]
        blob, gain, pad_w, pad_h = self._preprocess(image)

        start = time.perf_counter()
        output = self.session.run([self.output_name], {self.input_name: blob})[0]
        inference_ms = (time.perf_counter() - start) * 1000.0

        detections = self._postprocess(output, gain, pad_w, pad_h, img_w, img_h)
        return detections, inference_ms, img_w, img_h

    def _preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float, int, int]:
        h, w = image.shape[:2]
        target = self.input_size

        gain = min(target / w, target / h)
        new_w, new_h = int(round(w * gain)), int(round(h * gain))

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        canvas = np.full((target, target, 3), 114, dtype=np.uint8)
        pad_w = (target - new_w) // 2
        pad_h = (target - new_h) // 2
        canvas[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = resized

        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        blob = rgb.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))
        blob = np.expand_dims(blob, axis=0)
        return blob, gain, pad_w, pad_h

    def _postprocess(
        self,
        raw_output: np.ndarray,
        gain: float,
        pad_w: int,
        pad_h: int,
        orig_w: int,
        orig_h: int,
    ) -> List[Dict]:
        preds = np.squeeze(raw_output)
        if preds.ndim == 1:
            preds = np.expand_dims(preds, axis=0)

        # Normalize shape to [num_boxes, num_attrs]
        if preds.ndim == 2 and preds.shape[0] < preds.shape[1]:
            if preds.shape[0] <= 85:
                preds = preds.T
        elif preds.ndim != 2:
            return []

        boxes_xyxy: List[List[float]] = []
        scores: List[float] = []
        rel_centers: List[Tuple[float, float]] = []

        for row in preds:
            if row.shape[0] < 5:
                continue

            x, y, w, h = row[:4]
            cls_scores = row[4:]

            if cls_scores.size == 1:
                score = float(cls_scores[0])
            else:
                score = float(np.max(cls_scores))

            if score < self.conf_threshold:
                continue

            x1 = float(x - w / 2.0)
            y1 = float(y - h / 2.0)
            x2 = float(x + w / 2.0)
            y2 = float(y + h / 2.0)

            # Undo letterbox padding and scaling.
            x1 = (x1 - pad_w) / gain
            y1 = (y1 - pad_h) / gain
            x2 = (x2 - pad_w) / gain
            y2 = (y2 - pad_h) / gain

            x1 = max(0.0, min(x1, float(orig_w - 1)))
            y1 = max(0.0, min(y1, float(orig_h - 1)))
            x2 = max(0.0, min(x2, float(orig_w - 1)))
            y2 = max(0.0, min(y2, float(orig_h - 1)))

            if x2 <= x1 or y2 <= y1:
                continue

            boxes_xyxy.append([x1, y1, x2, y2])
            scores.append(score)

            cx = ((x1 + x2) / 2.0) / float(orig_w)
            cy = ((y1 + y2) / 2.0) / float(orig_h)
            rel_centers.append((cx, cy))

        if not boxes_xyxy:
            return []

        nms_boxes = [[b[0], b[1], b[2] - b[0], b[3] - b[1]] for b in boxes_xyxy]
        kept = cv2.dnn.NMSBoxes(nms_boxes, scores, self.conf_threshold, self.iou_threshold)

        if kept is None or len(kept) == 0:
            return []

        detections: List[Dict] = []
        for idx in np.array(kept).reshape(-1).tolist():
            x1, y1, x2, y2 = boxes_xyxy[idx]
            cx_rel, cy_rel = rel_centers[idx]
            detections.append(
                {
                    "confidence": round(float(scores[idx]), 4),
                    "box": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    "cx_rel": float(np.clip(cx_rel, 0.0, 1.0)),
                    "cy_rel": float(np.clip(cy_rel, 0.0, 1.0)),
                }
            )

        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections
