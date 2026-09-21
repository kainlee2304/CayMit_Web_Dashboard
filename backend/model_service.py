"""
AI inference service for jackfruit tree and fruit disease classification.
Optimized with on-demand (lazy) loading and low-memory profile for cloud deployment.
"""
import json
import math
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import torch
from dotenv import load_dotenv
from PIL import Image, ImageChops, ImageStat
from torchvision import models, transforms

# Limit PyTorch CPU threads to prevent memory explosion on cloud containers
try:
    torch.set_num_threads(1)
except Exception:
    pass

yolo_config_path = Path(__file__).parent.parent / ".ultralytics"
yolo_config_path.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(yolo_config_path))
os.environ.setdefault("YOLO_OFFLINE", "1")
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
from ultralytics import YOLO

try:
    from inference_sdk import InferenceHTTPClient
except ImportError:
    InferenceHTTPClient = None

try:
    from transformers import AutoImageProcessor, AutoModelForImageClassification
except ImportError:
    AutoImageProcessor = None
    AutoModelForImageClassification = None

load_dotenv()

CLASS_NAMES = os.getenv(
    "CLASS_NAMES",
    "pink_disease,stem_cracking_gummosis,batocera_rufomaculata,stripe_canker"
).split(",")

JACKFRUIT_CLASS_NAMES = os.getenv(
    "JACKFRUIT_CLASS_NAMES",
    "healthy,fruit_borer,fruit_rot,anthracnose"
).split(",")

BASE_DIR = Path(__file__).parent.parent
NOT_JACKFRUIT_CLASS = "not_jackfruit"

SUBJECT_CONFIDENCE_THRESHOLD = float(os.getenv("SUBJECT_CONFIDENCE_THRESHOLD", "0.80"))
SUBJECT_MARGIN_THRESHOLD = float(os.getenv("SUBJECT_MARGIN_THRESHOLD", "0.20"))
SUBJECT_ENTROPY_THRESHOLD = float(os.getenv("SUBJECT_ENTROPY_THRESHOLD", "0.78"))
SUBJECT_AMBIGUITY_THRESHOLD = float(os.getenv("SUBJECT_AMBIGUITY_THRESHOLD", "0.04"))
GENERAL_OBJECT_THRESHOLD = float(os.getenv("GENERAL_OBJECT_THRESHOLD", "0.35"))
JACKFRUIT_IMAGENET_THRESHOLD = float(os.getenv("JACKFRUIT_IMAGENET_THRESHOLD", "0.10"))
ROBOFLOW_FRUIT_THRESHOLD = float(os.getenv("ROBOFLOW_FRUIT_THRESHOLD", "0.65"))
FRUIT_IDENTITY_OTHER_MIN_CONFIDENCE = float(os.getenv("FRUIT_IDENTITY_OTHER_MIN_CONFIDENCE", "0.15"))
FRUIT_IDENTITY_JACKFRUIT_MIN_CONFIDENCE = float(os.getenv("FRUIT_IDENTITY_JACKFRUIT_MIN_CONFIDENCE", "0.15"))
FRUIT_IDENTITY_JACKFRUIT_MIN_MARGIN = float(os.getenv("FRUIT_IDENTITY_JACKFRUIT_MIN_MARGIN", "0.015"))
AUTO_ROUTE_ALL_REQUESTS = os.getenv("AUTO_ROUTE_ALL_REQUESTS", "true").strip().lower() in {"1", "true", "yes", "on"}

CONFLICTING_OBJECTS = {
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "sandwich", "hot dog", "pizza", "donut", "cake", "chair", "couch", "bed",
    "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
}


class ModelService:
    """Load and run YOLO classification models plus EfficientNet-B0 checkpoints with on-demand lazy loading."""

    def __init__(self):
        self.models: Dict[str, object] = {}
        self.model_types: Dict[str, str] = {}
        self.class_names: Dict[str, List[str]] = {}
        self.available_candidates: Dict[str, tuple] = {}
        self.general_object_guard = None
        self.imagenet_guard = None
        self.roboflow_client = None
        self.roboflow_model_id = os.getenv("ROBOFLOW_FRUIT_MODEL_ID", "fruits-zr4m9-g3ff6/1")
        self.roboflow_retry_after = 0.0
        self.fruit_identity_processor = None
        self.fruit_identity_model = None
        self.fruit_identity_name = "dima806/fruit_100_types_image_detection"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.efficientnet_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self._discover_models()
        self._configure_roboflow()

    def _configure_roboflow(self):
        if InferenceHTTPClient is None:
            return
        api_url = os.getenv("ROBOFLOW_API_URL", "https://serverless.roboflow.com").strip()
        api_key = os.getenv("ROBOFLOW_API_KEY", "").strip() or None
        is_local = api_url.startswith("http://localhost") or api_url.startswith("http://127.0.0.1")
        if api_key or is_local:
            self.roboflow_client = InferenceHTTPClient(api_url=api_url, api_key=api_key)
            print(f"[ModelService] Roboflow fruit detector enabled: {self.roboflow_model_id}")
        else:
            print("[ModelService] Roboflow fruit detector disabled: missing ROBOFLOW_API_KEY")

    def _resolve_path(self, raw_path: Optional[str], default_rel: str) -> Optional[Path]:
        if raw_path:
            p = Path(raw_path)
            if p.exists():
                return p
            p_base = (BASE_DIR / raw_path).resolve()
            if p_base.exists():
                return p_base
            clean_name = p.name
            p_model = BASE_DIR / "models" / clean_name
            if p_model.exists():
                return p_model

        default_p = (BASE_DIR / "models" / default_rel).resolve()
        if default_p.exists():
            return default_p
        return None

    def _discover_models(self):
        yolo_candidates = {
            "best_11": (os.getenv("MODEL_PATH_11"), "best_11.pt", "yolo_cls", CLASS_NAMES),
            "best_26": (os.getenv("MODEL_PATH_26"), "best_26.pt", "yolo_cls", CLASS_NAMES),
            "jackfruit_yolov26m_cls": (os.getenv("JACKFRUIT_YOLO_MODEL_PATH"), "best.pt", "yolo_cls", JACKFRUIT_CLASS_NAMES),
        }
        optional_detectors = {
            "stem_branch_detector": (os.getenv("MODEL_PATH_STEM_DET"), "stem_det.pt", "yolo_detect", []),
            "jackfruit_detector": (os.getenv("MODEL_PATH_FRUIT_DET"), "fruit_det.pt", "yolo_detect", []),
        }

        for name, (raw_path, def_name, mtype, cnames) in {**yolo_candidates, **optional_detectors}.items():
            resolved = self._resolve_path(raw_path, def_name)
            if resolved and resolved.exists():
                self.available_candidates[name] = (resolved, mtype, cnames)
                self.model_types[name] = mtype
                self.class_names[name] = cnames
                print(f"[ModelService] Discovered model: {name} at {resolved.name}")
            else:
                print(f"[ModelService] Model file not found: {raw_path or def_name}")

        eff_resolved = self._resolve_path(
            os.getenv("JACKFRUIT_EFFICIENTNET_MODEL_PATH"), "best_jackfruit_model.pth"
        )
        if eff_resolved and eff_resolved.exists():
            self.available_candidates["jackfruit_efficientnet_b0"] = (eff_resolved, "efficientnet_b0", JACKFRUIT_CLASS_NAMES)
            self.model_types["jackfruit_efficientnet_b0"] = "efficientnet_b0"
            self.class_names["jackfruit_efficientnet_b0"] = JACKFRUIT_CLASS_NAMES
            print(f"[ModelService] Discovered model: jackfruit_efficientnet_b0 at {eff_resolved.name}")

    def get_model(self, name: str):
        if name in self.models:
            return self.models[name]
        if name not in self.available_candidates:
            return None

        resolved, mtype, cnames = self.available_candidates[name]
        print(f"[ModelService] On-demand loading: {name} ({resolved.name})...")
        try:
            if mtype == "efficientnet_b0":
                self._load_efficientnet(name, str(resolved))
            else:
                model = YOLO(str(resolved))
                self.models[name] = model
                self.model_types[name] = "yolo_detect" if model.task == "detect" else "yolo_cls"
                if hasattr(model, "names") and model.names:
                    self.class_names[name] = list(model.names.values())
            print(f"[ModelService] OK: {name} loaded in memory.")
        except Exception as exc:
            print(f"[ModelService] Error loading model {name}: {exc}")
        return self.models.get(name)

    def _load_efficientnet(self, name: str, path: str):
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        state_dict = checkpoint
        class_names: Optional[List[str]] = None

        if isinstance(checkpoint, dict):
            for key in ("class_names", "classes", "idx_to_class"):
                if key in checkpoint:
                    value = checkpoint[key]
                    class_names = [value[i] for i in sorted(value)] if isinstance(value, dict) else list(value)
                    break

            for key in ("model_state_dict", "state_dict", "model"):
                if key in checkpoint and isinstance(checkpoint[key], dict):
                    state_dict = checkpoint[key]
                    break

        if not isinstance(state_dict, dict):
            raise ValueError("Checkpoint khong chua state_dict hop le")

        state_dict = {
            key.replace("module.", ""): value
            for key, value in state_dict.items()
            if hasattr(value, "shape")
        }

        classifier_weight = None
        for key in ("classifier.1.weight", "classifier.weight", "_fc.weight"):
            if key in state_dict:
                classifier_weight = state_dict[key]
                break

        num_classes = len(class_names or JACKFRUIT_CLASS_NAMES)
        if classifier_weight is not None:
            num_classes = int(classifier_weight.shape[0])

        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = torch.nn.Linear(in_features, num_classes)
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        if missing or unexpected:
            print(f"[ModelService] EfficientNet load note - missing: {missing}, unexpected: {unexpected}")

        model.to(self.device)
        model.eval()
        self.models[name] = model
        self.model_types[name] = "efficientnet_b0"
        self.class_names[name] = self._normalize_class_names(class_names, num_classes)

    def _normalize_class_names(self, class_names: Optional[List[str]], num_classes: int) -> List[str]:
        names = class_names or JACKFRUIT_CLASS_NAMES
        if len(names) < num_classes:
            names = names + [f"class_{idx}" for idx in range(len(names), num_classes)]
        return names[:num_classes]

    def _get_general_guard(self):
        if self.general_object_guard is not None:
            return self.general_object_guard
        try:
            gen_guard_resolved = self._resolve_path(os.getenv("GENERAL_OBJECT_MODEL_PATH"), "yolo11n_general.pt")
            if gen_guard_resolved and gen_guard_resolved.exists():
                self.general_object_guard = YOLO(str(gen_guard_resolved))
                print("[ModelService] OK: general object guard loaded")
        except Exception as exc:
            print(f"[ModelService] General guard not loaded: {exc}")
        return self.general_object_guard

    def _get_imagenet_guard(self):
        if self.imagenet_guard is not None:
            return self.imagenet_guard
        try:
            img_guard_resolved = self._resolve_path(os.getenv("IMAGENET_GUARD_MODEL_PATH"), "efficientnet_b0_imagenet.pth")
            if img_guard_resolved and img_guard_resolved.exists():
                guard = models.efficientnet_b0(weights=None)
                state_dict = torch.load(str(img_guard_resolved), map_location=self.device, weights_only=True)
                guard.load_state_dict(state_dict)
                guard.to(self.device).eval()
                self.imagenet_guard = guard
                print("[ModelService] OK: ImageNet jackfruit guard loaded")
        except Exception as exc:
            print(f"[ModelService] ImageNet guard not loaded: {exc}")
        return self.imagenet_guard

    def _get_fruit_identity_model(self):
        if self.fruit_identity_model is not None and self.fruit_identity_processor is not None:
            return self.fruit_identity_model, self.fruit_identity_processor
        try:
            fruit_id_resolved = self._resolve_path(os.getenv("FRUIT_IDENTITY_MODEL_PATH"), "fruit_100_vit")
            if (
                fruit_id_resolved
                and fruit_id_resolved.exists()
                and AutoImageProcessor is not None
                and AutoModelForImageClassification is not None
                and (fruit_id_resolved / "model.safetensors").exists()
            ):
                self.fruit_identity_processor = AutoImageProcessor.from_pretrained(
                    str(fruit_id_resolved), local_files_only=True, use_fast=True
                )
                self.fruit_identity_model = AutoModelForImageClassification.from_pretrained(
                    str(fruit_id_resolved), local_files_only=True
                ).to(self.device).eval()
                print("[ModelService] OK: ViT 100-fruit identity guard loaded")
        except Exception as exc:
            print(f"[ModelService] ViT guard not loaded: {exc}")
        return self.fruit_identity_model, self.fruit_identity_processor

    def predict(self, image: Image.Image, model_name: str = "auto") -> dict:
        """
        Run inference on an image.
        Returns: {predicted_class, confidence, all_scores, model_used}
        """
        if model_name == "auto" or AUTO_ROUTE_ALL_REQUESTS:
            return self._predict_auto(image)

        guard_reason = self._guard_reason(image)
        if guard_reason:
            return self._rejected_result(model_name, guard_reason)

        if model_name not in self.available_candidates:
            available = list(self.available_candidates.keys())
            if not available:
                raise ValueError("Khong co model nao duoc tim thay!")
            model_name = available[0]

        model_type = self.model_types.get(model_name, "yolo_cls")
        if model_type == "efficientnet_b0":
            result = self._predict_efficientnet(image, model_name)
        elif model_type == "yolo_detect":
            result = self._predict_detection(image, model_name)
        else:
            result = self._predict_yolo(image, model_name)
        return self._apply_subject_gate(result, self._subject_for_model(model_name))

    def _predict_raw(self, image: Image.Image, model_name: str) -> dict:
        model_type = self.model_types.get(model_name, "yolo_cls")
        if model_type == "efficientnet_b0":
            return self._predict_efficientnet(image, model_name)
        if model_type == "yolo_detect":
            return self._predict_detection(image, model_name)
        return self._predict_yolo(image, model_name)

    @staticmethod
    def _subject_for_model(model_name: str) -> str:
        return "fruit" if model_name.startswith("jackfruit_") else "tree"

    def _routing_models(self) -> List[tuple]:
        candidates = []
        tree_model = os.getenv("TREE_DISEASE_MODEL", "best_11")
        fruit_model = os.getenv("FRUIT_DISEASE_MODEL", "jackfruit_yolov26m_cls")
        if tree_model in self.available_candidates:
            candidates.append(("tree", tree_model))
        if fruit_model in self.available_candidates:
            candidates.append(("fruit", fruit_model))
        return candidates

    @staticmethod
    def _score_metrics(result: dict) -> tuple:
        try:
            scores = json.loads(result.get("all_scores") or "{}")
        except (TypeError, json.JSONDecodeError):
            scores = {}
        values = sorted((float(value) for value in scores.values()), reverse=True)
        confidence = float(result.get("confidence", 0.0))
        margin = confidence - (values[1] if len(values) > 1 else 0.0)
        if len(values) > 1:
            entropy = -sum(value * math.log(max(value, 1e-12)) for value in values)
            entropy /= math.log(len(values))
        else:
            entropy = 1.0 if not values else 0.0
        strength = confidence * max(margin, 0.0) * max(1.0 - entropy, 0.0)
        return confidence, margin, entropy, strength

    def _is_subject_confident(self, result: dict) -> bool:
        confidence, margin, entropy, _ = self._score_metrics(result)
        return (
            confidence >= SUBJECT_CONFIDENCE_THRESHOLD
            and margin >= SUBJECT_MARGIN_THRESHOLD
            and entropy <= SUBJECT_ENTROPY_THRESHOLD
        )

    @staticmethod
    def _rejected_result(model_used: str, reason: str) -> dict:
        return {
            "predicted_class": NOT_JACKFRUIT_CLASS,
            "confidence": 0.0,
            "all_scores": json.dumps({}),
            "model_used": model_used,
            "boxes": [],
            "task": "classify",
            "is_jackfruit": False,
            "subject_type": "unknown",
            "status": "not_jackfruit",
            "message": reason,
        }

    def _apply_subject_gate(self, result: dict, subject_type: str) -> dict:
        if not self._is_subject_confident(result):
            return self._rejected_result(
                result.get("model_used", "unknown"),
                "Không phát hiện trái mít hoặc cây mít đủ độ tin cậy.",
            )
        return {
            **result,
            "is_jackfruit": True,
            "subject_type": subject_type,
            "status": "detected",
            "message": "Đã phát hiện đối tượng mít và phân tích bệnh.",
        }

    def _predict_auto(self, image: Image.Image) -> dict:
        guard_reason = self._guard_reason(image)
        if guard_reason:
            return self._rejected_result("auto", guard_reason)

        remote_detection = self._detect_fruit_with_roboflow(image)
        if remote_detection["status"] == "other_fruit":
            fruit_names = ", ".join(remote_detection["classes"])
            return self._rejected_result(
                self.roboflow_model_id,
                f"Phát hiện trái cây khác ({fruit_names}), không phải trái mít.",
            )
        if remote_detection["status"] == "jackfruit":
            return self._classify_detected_jackfruit(image, remote_detection["boxes"])

        vit_identity = self._classify_vit_fruit_identity(image)
        if vit_identity["status"] == "other_fruit":
            return self._rejected_result(
                self.fruit_identity_name,
                f"Phát hiện {vit_identity['class_name']}, không phải trái mít.",
            )
        if vit_identity["status"] == "jackfruit":
            return self._classify_vit_confirmed_jackfruit(image, vit_identity)

        candidates = []
        for subject_type, model_name in self._routing_models():
            raw = self._predict_raw(image, model_name)
            if self._is_subject_confident(raw):
                candidates.append((self._score_metrics(raw)[3], subject_type, raw))

        if not candidates:
            return self._rejected_result("auto", "Ảnh không phải mít hoặc chưa đủ rõ để nhận diện.")

        candidates.sort(key=lambda item: item[0], reverse=True)
        selected = candidates[0]
        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < SUBJECT_AMBIGUITY_THRESHOLD:
            selected = next((item for item in candidates if item[1] == "fruit"), selected)

        _, subject_type, result = selected
        if (
            subject_type == "fruit"
            and vit_identity["status"] == "uncertain"
            and vit_identity.get("jackfruit_rank", 101) > 20
        ):
            return self._rejected_result(
                self.fruit_identity_name,
                "Không có bằng chứng đây là trái mít; hệ thống không phân tích bệnh.",
            )
        return {
            **result,
            "is_jackfruit": True,
            "subject_type": subject_type,
            "status": "detected",
            "message": "Đã phát hiện đối tượng mít và phân tích bệnh.",
        }

    def _detect_fruit_with_roboflow(self, image: Image.Image) -> dict:
        if self.roboflow_client is None or time.monotonic() < self.roboflow_retry_after:
            return {"status": "unavailable", "boxes": [], "classes": []}
        try:
            response = self.roboflow_client.infer(image, model_id=self.roboflow_model_id)
            if isinstance(response, list):
                response = response[0] if response else {}
            predictions = response.get("predictions", []) if isinstance(response, dict) else []
        except Exception as exc:
            self.roboflow_retry_after = time.monotonic() + 30.0
            print(f"[ModelService] Roboflow unavailable, using local fallback: {type(exc).__name__}")
            return {"status": "unavailable", "boxes": [], "classes": []}

        image_width, image_height = image.size
        boxes = []
        for prediction in predictions:
            confidence = float(prediction.get("confidence", 0.0))
            if confidence < ROBOFLOW_FRUIT_THRESHOLD:
                continue

            x = float(prediction.get("x", 0.0))
            y = float(prediction.get("y", 0.0))
            width = float(prediction.get("width", 0.0))
            height = float(prediction.get("height", 0.0))
            class_name = str(prediction.get("class", "fruit")).strip()

            normalized_x = max(0.0, min(1.0, (x - width / 2.0) / image_width))
            normalized_y = max(0.0, min(1.0, (y - height / 2.0) / image_height))
            boxes.append({
                "x": round(normalized_x, 5),
                "y": round(normalized_y, 5),
                "width": round(max(0.0, min(1.0 - normalized_x, width / image_width)), 5),
                "height": round(max(0.0, min(1.0 - normalized_y, height / image_height)), 5),
                "class_name": class_name,
                "confidence": round(confidence, 4),
            })

        boxes.sort(key=lambda box: box["confidence"], reverse=True)
        jackfruit_boxes = [box for box in boxes if box["class_name"].strip().lower() == "jackfruit"]
        if jackfruit_boxes:
            return {"status": "jackfruit", "boxes": jackfruit_boxes, "classes": ["Jackfruit"]}
        if boxes:
            classes = sorted({box["class_name"] for box in boxes})
            return {"status": "other_fruit", "boxes": boxes, "classes": classes}
        return {"status": "no_fruit", "boxes": [], "classes": []}

    def _classify_vit_fruit_identity(self, image: Image.Image) -> dict:
        vit_model, vit_processor = self._get_fruit_identity_model()
        if vit_model is None or vit_processor is None:
            return {"status": "unavailable", "class_name": "unknown", "confidence": 0.0}
        try:
            inputs = vit_processor(images=image, return_tensors="pt")
            inputs = {name: tensor.to(self.device) for name, tensor in inputs.items()}
            with torch.no_grad():
                probabilities = torch.softmax(vit_model(**inputs).logits, dim=1)[0]

            values, indices = torch.topk(probabilities, k=min(5, len(probabilities)))
            scores = {
                str(vit_model.config.id2label[int(index)]).strip().lower(): float(value)
                for value, index in zip(values.tolist(), indices.tolist())
            }
            top_class = next(iter(scores), "unknown")
            top_confidence = scores.get(top_class, 0.0)
            label_by_index = {
                int(index): str(label).strip().lower()
                for index, label in vit_model.config.id2label.items()
            }
            jackfruit_index = next(
                (index for index, label in label_by_index.items() if label == "jackfruit"),
                None,
            )
            if jackfruit_index is None:
                jackfruit_confidence = 0.0
                jackfruit_rank = len(probabilities) + 1
            else:
                jackfruit_probability = probabilities[jackfruit_index]
                jackfruit_confidence = float(jackfruit_probability)
                jackfruit_rank = int((probabilities > jackfruit_probability).sum().item()) + 1
            second_confidence = list(scores.values())[1] if len(scores) > 1 else 0.0

            if (
                top_class == "jackfruit"
                and top_confidence >= FRUIT_IDENTITY_JACKFRUIT_MIN_CONFIDENCE
                and top_confidence - second_confidence >= FRUIT_IDENTITY_JACKFRUIT_MIN_MARGIN
            ):
                status = "jackfruit"
            elif top_class != "jackfruit" and top_confidence >= FRUIT_IDENTITY_OTHER_MIN_CONFIDENCE:
                status = "other_fruit"
            else:
                status = "uncertain"
            return {
                "status": status,
                "class_name": top_class,
                "confidence": round(top_confidence, 4),
                "jackfruit_confidence": round(jackfruit_confidence, 4),
                "jackfruit_rank": jackfruit_rank,
                "scores": scores,
            }
        except Exception as exc:
            print(f"[ModelService] ViT identity error: {exc}")
            return {"status": "unavailable", "class_name": "unknown", "confidence": 0.0}

    def _classify_vit_confirmed_jackfruit(self, image: Image.Image, identity: dict) -> dict:
        fruit_model = os.getenv("FRUIT_DISEASE_MODEL", "jackfruit_yolov26m_cls")
        target_model = fruit_model if fruit_model in self.available_candidates else "best_11"
        result = self._predict_raw(image, target_model)
        return {
            **result,
            "is_jackfruit": True,
            "subject_type": "fruit",
            "status": "detected",
            "message": "ViT đã xác nhận trái mít; model bệnh tiếp tục phân tích tình trạng trái.",
            "identity_model": self.fruit_identity_name,
            "identity_confidence": identity["confidence"],
        }

    def _classify_detected_jackfruit(self, image: Image.Image, boxes: List[dict]) -> dict:
        top_box = boxes[0]
        image_width, image_height = image.size
        padding_x, padding_y = image_width * 0.03, image_height * 0.03
        left = max(0, top_box["x"] * image_width - padding_x)
        top = max(0, top_box["y"] * image_height - padding_y)
        right = min(image_width, (top_box["x"] + top_box["width"]) * image_width + padding_x)
        bottom = min(image_height, (top_box["y"] + top_box["height"]) * image_height + padding_y)
        crop = image.crop((left, top, right, bottom))

        fruit_model = os.getenv("FRUIT_DISEASE_MODEL", "jackfruit_yolov26m_cls")
        target_model = fruit_model if fruit_model in self.available_candidates else "best_11"
        result = self._predict_raw(crop, target_model)
        return {
            **result,
            "boxes": boxes,
            "task": "detect",
            "is_jackfruit": True,
            "subject_type": "fruit",
            "status": "detected",
            "message": "Roboflow đã xác nhận trái mít; model bệnh phân tích trên vùng trái được phát hiện.",
            "identity_model": self.roboflow_model_id,
            "identity_confidence": top_box["confidence"],
        }

    def _guard_reason(self, image: Image.Image) -> Optional[str]:
        grayscale = image.resize((160, 120)).convert("L")
        stats = ImageStat.Stat(grayscale)
        if stats.stddev[0] < 8.0 or grayscale.entropy() < 3.0:
            return "Ảnh trống, quá tối hoặc không có đối tượng rõ ràng."
        detail_image = image.copy()
        detail_image.thumbnail((640, 640))
        detail_image = detail_image.convert("L")
        width, height = detail_image.size
        horizontal_difference = ImageChops.difference(
            detail_image.crop((1, 0, width, height)), detail_image.crop((0, 0, width - 1, height))
        )
        if ImageStat.Stat(horizontal_difference).mean[0] > 50.0:
            return "Ảnh bị nhiễu hoặc không đủ rõ để nhận diện."

        gen_guard = self._get_general_guard()
        if gen_guard is None:
            return None

        try:
            result = gen_guard(image, verbose=False, conf=GENERAL_OBJECT_THRESHOLD)[0]
            conflicts = []
            if result.boxes is not None:
                for cls_idx in result.boxes.cls.tolist():
                    name = result.names.get(int(cls_idx), "")
                    if name in CONFLICTING_OBJECTS:
                        conflicts.append(name)
            if not conflicts:
                return None

            img_guard = self._get_imagenet_guard()
            if img_guard is not None:
                tensor = self.efficientnet_transform(image).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    probability = torch.softmax(img_guard(tensor), dim=1)[0, 955].item()
                if probability >= JACKFRUIT_IMAGENET_THRESHOLD:
                    return None

            return "Phát hiện vật thể khác (%s), không phân tích bệnh." % ", ".join(sorted(set(conflicts)))
        except Exception as exc:
            print(f"[ModelService] Guard evaluation error: {exc}")
            return None

    def _predict_yolo(self, image: Image.Image, model_name: str) -> dict:
        model = self.get_model(model_name)
        if model is None:
            raise ValueError(f"Không thể khởi động model: {model_name}")
        results = model(image, verbose=False)
        result = results[0]

        probs = result.probs
        top1_idx = int(probs.top1)
        top1_conf = float(probs.top1conf)

        names = result.names
        predicted_class = names.get(top1_idx, CLASS_NAMES[top1_idx] if top1_idx < len(CLASS_NAMES) else "unknown")

        all_scores = {}
        for idx, conf in enumerate(probs.data.tolist()):
            class_name = names.get(idx, CLASS_NAMES[idx] if idx < len(CLASS_NAMES) else f"class_{idx}")
            all_scores[class_name] = round(conf, 4)

        return {
            "predicted_class": predicted_class,
            "confidence": round(top1_conf, 4),
            "all_scores": json.dumps(all_scores),
            "model_used": model_name,
            "boxes": [],
            "task": "classify",
        }

    def _predict_detection(self, image: Image.Image, model_name: str) -> dict:
        model = self.get_model(model_name)
        if model is None:
            raise ValueError(f"Không thể khởi động model: {model_name}")
        result = model(image, verbose=False)[0]
        width, height = image.size
        boxes = []
        if result.boxes is not None:
            for xyxy, conf, cls_idx in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist(), result.boxes.cls.tolist()):
                idx = int(cls_idx)
                boxes.append({
                    "x": round(xyxy[0] / width, 5), "y": round(xyxy[1] / height, 5),
                    "width": round((xyxy[2] - xyxy[0]) / width, 5),
                    "height": round((xyxy[3] - xyxy[1]) / height, 5),
                    "class_name": result.names.get(idx, f"class_{idx}"),
                    "confidence": round(float(conf), 4),
                })
        boxes.sort(key=lambda box: box["confidence"], reverse=True)
        top = boxes[0] if boxes else {"class_name": "none", "confidence": 0.0}
        return {
            "predicted_class": top["class_name"], "confidence": top["confidence"],
            "all_scores": json.dumps({}), "model_used": model_name, "boxes": boxes,
            "task": "detect",
        }

    def _predict_efficientnet(self, image: Image.Image, model_name: str) -> dict:
        model = self.get_model(model_name)
        if model is None:
            raise ValueError(f"Không thể khởi động model: {model_name}")
        tensor = self.efficientnet_transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0].detach().cpu()

        top1_idx = int(torch.argmax(probs).item())
        top1_conf = float(probs[top1_idx].item())
        names = self.class_names.get(model_name, self._normalize_class_names(None, len(probs)))
        predicted_class = names[top1_idx] if top1_idx < len(names) else f"class_{top1_idx}"

        all_scores = {
            names[idx] if idx < len(names) else f"class_{idx}": round(float(conf), 4)
            for idx, conf in enumerate(probs.tolist())
        }

        return {
            "predicted_class": predicted_class,
            "confidence": round(top1_conf, 4),
            "all_scores": json.dumps(all_scores),
            "model_used": model_name,
            "boxes": [],
            "task": "classify",
        }

    def get_available_models(self):
        return [{
            "name": "auto",
            "type": "jackfruit_router",
            "class_names": [],
        }] + [
            {
                "name": name,
                "type": self.model_types.get(name, "unknown"),
                "class_names": self.class_names.get(name, []),
            }
            for name in sorted(self.available_candidates.keys())
        ]


model_service = ModelService()
