"""ONNX Runtime inference for PP-OCRv5 detection + recognition."""

from __future__ import annotations

import copy
import math
from pathlib import Path

import cv2
import numpy as np
import pyclipper
from shapely.geometry import Polygon

_MODELS_DIR = Path(__file__).parent / "models"

_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)

_RESIZE_LONG = 960
_STRIDE = 128

_REC_HEIGHT = 48
_REC_CHANNELS = 3
_REC_WIDTH = 320
_REC_BATCH = 6

_DOC_ORI_LABELS = ["0", "90", "180", "270"]
_TEXTLINE_ORI_LABELS = ["0_degree", "180_degree"]


class OnnxSession:
    def __init__(self, model_path: str | Path):
        from onnxruntime import (
            GraphOptimizationLevel,
            InferenceSession,
            SessionOptions,
        )

        opts = SessionOptions()
        opts.log_severity_level = 4
        opts.enable_cpu_mem_arena = False
        opts.graph_optimization_level = GraphOptimizationLevel.ORT_ENABLE_ALL

        providers = [
            ("CPUExecutionProvider", {"arena_extend_strategy": "kSameAsRequested"}),
        ]
        self.session = InferenceSession(
            str(model_path), sess_options=opts, providers=providers
        )
        self._input_names = [i.name for i in self.session.get_inputs()]
        self._output_names = [o.name for o in self.session.get_outputs()]

    def __call__(self, input_array: np.ndarray) -> list[np.ndarray]:
        feed = dict(zip(self._input_names, [input_array]))
        return self.session.run(self._output_names, feed)


def det_preprocess(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    src_h, src_w = img.shape[:2]

    if src_h > src_w:
        ratio = float(_RESIZE_LONG) / src_h
    else:
        ratio = float(_RESIZE_LONG) / src_w

    resize_h = int(src_h * ratio)
    resize_w = int(src_w * ratio)

    resize_h = (resize_h + _STRIDE - 1) // _STRIDE * _STRIDE
    resize_w = (resize_w + _STRIDE - 1) // _STRIDE * _STRIDE

    resized = cv2.resize(img, (resize_w, resize_h))

    ratio_h = resize_h / float(src_h)
    ratio_w = resize_w / float(src_w)

    normalized = (resized.astype(np.float32) / 255.0 - _IMAGENET_MEAN) / _IMAGENET_STD
    chw = normalized.transpose(2, 0, 1)
    blob = chw[np.newaxis, :].astype(np.float32)
    shape = np.array([[src_h, src_w, ratio_h, ratio_w]], dtype=np.float32)
    return blob, shape


class DBPostProcess:
    def __init__(
        self,
        thresh: float = 0.3,
        box_thresh: float = 0.5,
        max_candidates: int = 1000,
        unclip_ratio: float = 1.5,
        use_dilation: bool = True,
    ):
        self.thresh = thresh
        self.box_thresh = box_thresh
        self.max_candidates = max_candidates
        self.unclip_ratio = unclip_ratio
        self.min_size = 3
        self.dilation_kernel = np.array([[1, 1], [1, 1]]) if use_dilation else None

    def __call__(
        self, pred: np.ndarray, shape_list: np.ndarray
    ) -> list[np.ndarray]:
        pred = pred[:, 0, :, :]
        segmentation = pred > self.thresh

        all_boxes = []
        for batch_idx in range(pred.shape[0]):
            src_h, src_w, ratio_h, ratio_w = shape_list[batch_idx]
            mask = segmentation[batch_idx]
            if self.dilation_kernel is not None:
                mask = cv2.dilate(mask.astype(np.uint8), self.dilation_kernel)
            boxes = self._boxes_from_bitmap(pred[batch_idx], mask, src_w, src_h)
            all_boxes.append(boxes)
        return all_boxes

    def _boxes_from_bitmap(
        self,
        pred: np.ndarray,
        bitmap: np.ndarray,
        dest_width: float,
        dest_height: float,
    ) -> np.ndarray:
        height, width = bitmap.shape
        contours, _ = cv2.findContours(
            (bitmap * 255).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        num_contours = min(len(contours), self.max_candidates)

        boxes = []
        for i in range(num_contours):
            contour = contours[i]
            points, sside = self._get_mini_boxes(contour)
            if sside < self.min_size:
                continue
            points = np.array(points)
            score = self._box_score_fast(pred, points.reshape(-1, 2))
            if score < self.box_thresh:
                continue

            expanded = self._unclip(points)
            box, sside = self._get_mini_boxes(expanded.reshape(-1, 1, 2))
            if sside < self.min_size + 2:
                continue
            box = np.array(box)
            box[:, 0] = np.clip(np.round(box[:, 0] / width * dest_width), 0, dest_width)
            box[:, 1] = np.clip(
                np.round(box[:, 1] / height * dest_height), 0, dest_height
            )
            boxes.append(box.astype(np.int16))

        return np.array(boxes, dtype=np.int16) if boxes else np.empty((0, 4, 2), dtype=np.int16)

    def _unclip(self, box: np.ndarray) -> np.ndarray:
        poly = Polygon(box)
        distance = poly.area * self.unclip_ratio / poly.length
        offset = pyclipper.PyclipperOffset()
        offset.AddPath(box.tolist(), pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
        return np.array(offset.Execute(distance))

    @staticmethod
    def _get_mini_boxes(contour):
        bounding_box = cv2.minAreaRect(contour)
        points = sorted(cv2.boxPoints(bounding_box).tolist(), key=lambda x: x[0])
        if points[1][1] > points[0][1]:
            idx1, idx4 = 0, 1
        else:
            idx1, idx4 = 1, 0
        if points[3][1] > points[2][1]:
            idx2, idx3 = 2, 3
        else:
            idx2, idx3 = 3, 2
        box = [points[idx1], points[idx2], points[idx3], points[idx4]]
        return box, min(bounding_box[1])

    @staticmethod
    def _box_score_fast(bitmap: np.ndarray, box: np.ndarray) -> float:
        h, w = bitmap.shape[:2]
        box = box.copy()
        xmin = np.clip(np.floor(box[:, 0].min()).astype(int), 0, w - 1)
        xmax = np.clip(np.ceil(box[:, 0].max()).astype(int), 0, w - 1)
        ymin = np.clip(np.floor(box[:, 1].min()).astype(int), 0, h - 1)
        ymax = np.clip(np.ceil(box[:, 1].max()).astype(int), 0, h - 1)

        mask = np.zeros((ymax - ymin + 1, xmax - xmin + 1), dtype=np.uint8)
        box[:, 0] -= xmin
        box[:, 1] -= ymin
        cv2.fillPoly(mask, box.reshape(1, -1, 2).astype(np.int32), 1)
        return cv2.mean(bitmap[ymin : ymax + 1, xmin : xmax + 1], mask)[0]


def get_rotate_crop_image(img: np.ndarray, points: np.ndarray) -> np.ndarray:
    points = np.float32(points)
    crop_width = int(
        max(
            np.linalg.norm(points[0] - points[1]),
            np.linalg.norm(points[2] - points[3]),
        )
    )
    crop_height = int(
        max(
            np.linalg.norm(points[0] - points[3]),
            np.linalg.norm(points[1] - points[2]),
        )
    )
    dst = np.float32(
        [[0, 0], [crop_width, 0], [crop_width, crop_height], [0, crop_height]]
    )
    M = cv2.getPerspectiveTransform(points, dst)
    result = cv2.warpPerspective(
        img,
        M,
        (crop_width, crop_height),
        borderMode=cv2.BORDER_REPLICATE,
        flags=cv2.INTER_CUBIC,
    )
    if result.shape[0] * 1.0 / max(result.shape[1], 1) >= 1.5:
        result = np.rot90(result)
    return result


def rec_preprocess(
    img: np.ndarray, max_wh_ratio: float
) -> np.ndarray:
    target_w = int(_REC_HEIGHT * max_wh_ratio)
    h, w = img.shape[:2]
    ratio = w / float(h)
    resized_w = min(int(math.ceil(_REC_HEIGHT * ratio)), target_w)

    resized = cv2.resize(img, (resized_w, _REC_HEIGHT))
    resized = resized.astype(np.float32).transpose(2, 0, 1) / 255.0
    resized = (resized - 0.5) / 0.5

    padded = np.zeros((_REC_CHANNELS, _REC_HEIGHT, target_w), dtype=np.float32)
    padded[:, :, :resized_w] = resized
    return padded


class CTCLabelDecode:
    def __init__(self, character_dict_path: str | Path):
        with open(character_dict_path, encoding="utf-8") as f:
            chars = [line.rstrip("\n\r") for line in f]
        chars.append(" ")
        self.character = ["blank"] + chars

    def __call__(self, preds: np.ndarray) -> list[tuple[str, float]]:
        preds_idx = preds.argmax(axis=2)
        preds_prob = preds.max(axis=2)
        results = []
        for batch_idx in range(preds_idx.shape[0]):
            char_list = []
            conf_list = []
            for t in range(preds_idx.shape[1]):
                idx = int(preds_idx[batch_idx, t])
                if idx == 0:
                    continue
                if t > 0 and preds_idx[batch_idx, t - 1] == idx:
                    continue
                char_list.append(self.character[idx])
                conf_list.append(float(preds_prob[batch_idx, t]))
            text = "".join(char_list)
            score = float(np.mean(conf_list)) if conf_list else 0.0
            results.append((text, score))
        return results


def sorted_boxes(boxes: np.ndarray) -> list[np.ndarray]:
    sorted_list = sorted(boxes, key=lambda x: (x[0][1], x[0][0]))
    result = list(sorted_list)
    for i in range(len(result) - 1):
        if (
            abs(result[i + 1][0][1] - result[i][0][1]) < 10
            and result[i + 1][0][0] < result[i][0][0]
        ):
            result[i], result[i + 1] = result[i + 1], result[i]
    return result


def _order_points_clockwise(pts: np.ndarray) -> np.ndarray:
    x_sorted = pts[np.argsort(pts[:, 0]), :]
    left = x_sorted[:2, :]
    right = x_sorted[2:, :]
    left = left[np.argsort(left[:, 1]), :]
    tl, bl = left[0], left[1]
    right = right[np.argsort(right[:, 1]), :]
    tr, br = right[0], right[1]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def _clip_det_res(points: np.ndarray, h: int, w: int) -> np.ndarray:
    points[:, 0] = np.clip(points[:, 0], 0, w - 1)
    points[:, 1] = np.clip(points[:, 1], 0, h - 1)
    return points


def _filter_det_boxes(
    boxes: np.ndarray, img_shape: tuple[int, int]
) -> np.ndarray:
    h, w = img_shape
    filtered = []
    for box in boxes:
        box = _order_points_clockwise(box.astype(np.float32))
        box = _clip_det_res(box, h, w)
        rect_w = int(np.linalg.norm(box[0] - box[1]))
        rect_h = int(np.linalg.norm(box[0] - box[3]))
        if rect_w <= 3 or rect_h <= 3:
            continue
        filtered.append(box)
    return np.array(filtered) if filtered else np.empty((0, 4, 2), dtype=np.float32)


def _cls_preprocess_doc_ori(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    if h < w:
        ratio = 256.0 / h
    else:
        ratio = 256.0 / w
    new_h, new_w = int(h * ratio), int(w * ratio)
    resized = cv2.resize(img, (new_w, new_h))
    top = (new_h - 224) // 2
    left = (new_w - 224) // 2
    cropped = resized[top : top + 224, left : left + 224]
    normalized = (cropped.astype(np.float32) / 255.0 - _IMAGENET_MEAN) / _IMAGENET_STD
    return normalized.transpose(2, 0, 1)[np.newaxis].astype(np.float32)


def _cls_preprocess_textline_ori(img: np.ndarray) -> np.ndarray:
    resized = cv2.resize(img, (160, 80))
    normalized = (resized.astype(np.float32) / 255.0 - _IMAGENET_MEAN) / _IMAGENET_STD
    return normalized.transpose(2, 0, 1)[np.newaxis].astype(np.float32)


class OnnxOCR:
    def __init__(self, models_dir: str | Path | None = None, text_score: float = 0.5):
        models_dir = Path(models_dir) if models_dir else _MODELS_DIR

        det_path = models_dir / "PP-OCRv5_server_det.onnx"
        rec_path = models_dir / "latin_PP-OCRv5_mobile_rec.onnx"
        dict_path = models_dir / "latin_v5_dict.txt"

        self.det_session = OnnxSession(det_path)
        self.rec_session = OnnxSession(rec_path)
        self.postprocess = DBPostProcess()
        self.ctc_decode = CTCLabelDecode(dict_path)
        self.text_score = text_score

        doc_ori_path = models_dir / "PP-LCNet_x1_0_doc_ori.onnx"
        if doc_ori_path.exists():
            self.doc_ori_session = OnnxSession(doc_ori_path)
        else:
            self.doc_ori_session = None

        textline_ori_path = models_dir / "PP-LCNet_x1_0_textline_ori.onnx"
        if textline_ori_path.exists():
            self.textline_ori_session = OnnxSession(textline_ori_path)
        else:
            self.textline_ori_session = None

    def _correct_doc_orientation(self, img: np.ndarray) -> np.ndarray:
        if self.doc_ori_session is None:
            return img
        blob = _cls_preprocess_doc_ori(img)
        logits = self.doc_ori_session(blob)[0]
        cls_idx = int(np.argmax(logits[0]))
        label = _DOC_ORI_LABELS[cls_idx]
        if label == "90":
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if label == "180":
            return cv2.rotate(img, cv2.ROTATE_180)
        if label == "270":
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        return img

    def _correct_textline_orientation(self, crop: np.ndarray) -> np.ndarray:
        if self.textline_ori_session is None:
            return crop
        blob = _cls_preprocess_textline_ori(crop)
        logits = self.textline_ori_session(blob)[0]
        cls_idx = int(np.argmax(logits[0]))
        if _TEXTLINE_ORI_LABELS[cls_idx] == "180_degree":
            return cv2.rotate(crop, cv2.ROTATE_180)
        return crop

    def __call__(self, img: np.ndarray) -> list[list] | None:
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        img = self._correct_doc_orientation(img)

        dt_boxes = self._detect(img)
        if dt_boxes is None or len(dt_boxes) == 0:
            return None

        dt_boxes = sorted_boxes(dt_boxes)
        crops = [get_rotate_crop_image(img, copy.deepcopy(box)) for box in dt_boxes]
        crops = [self._correct_textline_orientation(c) for c in crops]
        rec_results = self._recognize(crops)

        output = []
        for box, (text, score) in zip(dt_boxes, rec_results):
            if score >= self.text_score:
                box_list = box.tolist() if isinstance(box, np.ndarray) else box
                output.append([box_list, text, score])
        return output if output else None

    def _detect(self, img: np.ndarray) -> np.ndarray | None:
        ori_shape = img.shape[:2]
        blob, shape_list = det_preprocess(img)
        preds = self.det_session(blob)
        boxes_batch = self.postprocess(preds[0], shape_list)
        if len(boxes_batch) == 0 or len(boxes_batch[0]) == 0:
            return None
        return _filter_det_boxes(boxes_batch[0], ori_shape)

    def _recognize(self, img_list: list[np.ndarray]) -> list[tuple[str, float]]:
        if not img_list:
            return []

        width_ratios = [img.shape[1] / float(img.shape[0]) for img in img_list]
        indices = np.argsort(np.array(width_ratios))

        num = len(img_list)
        results: list[tuple[str, float]] = [("", 0.0)] * num

        for start in range(0, num, _REC_BATCH):
            end = min(num, start + _REC_BATCH)
            max_wh_ratio = 0.0
            for i in range(start, end):
                h, w = img_list[indices[i]].shape[:2]
                max_wh_ratio = max(max_wh_ratio, w / float(h))

            batch = []
            for i in range(start, end):
                norm = rec_preprocess(img_list[indices[i]], max_wh_ratio)
                batch.append(norm[np.newaxis, :])

            batch_array = np.concatenate(batch).astype(np.float32)
            preds = self.rec_session(batch_array)
            decoded = self.ctc_decode(preds[0])

            for j, res in enumerate(decoded):
                results[indices[start + j]] = res

        return results
