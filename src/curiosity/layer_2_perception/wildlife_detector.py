"""Layer 2 Sub-Module: Wildlife & Multi-Species Animal Intelligence Engine.

Solves the COCO 80-Class Limitation:
Standard YOLO models are trained on MS-COCO which only has 10 domestic/common animal classes
(giraffe, zebra, elephant, bear, horse, cow, sheep, dog, cat, bird).
It completely lacks wild predators and fauna (lion, tiger, leopard, cheetah, wildebeest,
gazelle, impala, antelope, hyena, etc.).

This module integrates:
1. Low-threshold adaptive animal candidate localization
2. High-resolution crop-level classification using ResNet-50 (ImageNet-1K with 300+ animal classes)
3. Specialized species remapping (e.g., misclassified COCO 'cow'/'cat' -> 'lion' or 'wildebeest')
4. Herd band scanning for foreground/midground grazing groups
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple
from PIL import Image

from src.curiosity.layer_0_core.contracts import DetectedObject

logger = logging.getLogger("curiosity.layer_2.wildlife")


class WildlifeFaunaEngine:
    """Detects, localizes, and classifies wild animal species across complex safari/nature scenes."""

    # Pre-trained COCO animal classes that YOLO might output as proxies for wild animals
    COCO_ANIMAL_PROXIES: Set[str] = {
        "cow", "horse", "sheep", "cat", "dog", "bear", "bird", "elephant", "zebra", "giraffe"
    }

    # ImageNet-1K species keywords mapped to normalized wildlife labels
    IMAGE_NET_WILDLIFE_MAP: Dict[str, str] = {
        # Big Cats & Predators
        "lion": "lion",
        "tiger": "tiger",
        "cheetah": "cheetah",
        "leopard": "leopard",
        "snow leopard": "leopard",
        "jaguar": "jaguar",
        "cougar": "cougar",
        "lynx": "lynx",
        # African & Wild Herbivores / Ungulates
        "hartebeest": "wildebeest",
        "wildebeest": "wildebeest",
        "gnu": "wildebeest",
        "impala": "impala",
        "gazelle": "gazelle",
        "springbok": "gazelle",
        "ibex": "gazelle",
        "bighorn": "antelope",
        "water buffalo": "water buffalo",
        "ox": "ox",
        "bison": "bison",
        "zebra": "zebra",
        "giraffe": "giraffe",
        "elephant": "elephant",
        "hippopotamus": "hippopotamus",
        "warthog": "warthog",
        "rhinoceros": "rhinoceros",
        "rhino": "rhinoceros",
        "triceratops": "rhinoceros",
        "sorrel": "wildebeest",
        # Wild Canids & Scavengers
        "hyena": "hyena",
        "african hunting dog": "wild dog",
        "dhole": "wild dog",
        "dingo": "dingo",
        "timber wolf": "wolf",
        "red wolf": "wolf",
        "coyote": "coyote",
        "red fox": "fox",
        "kit fox": "fox",
        "grey fox": "fox",
        # Primates
        "chimpanzee": "chimpanzee",
        "gorilla": "gorilla",
        "orangutan": "orangutan",
        "gibbon": "gibbon",
        "baboon": "baboon",
        "macaque": "monkey",
        # Other Wild Fauna
        "brown bear": "bear",
        "american black bear": "bear",
        "polar bear": "polar bear",
        "sloth bear": "bear",
        "kangaroo": "kangaroo",
        "camel": "camel",
        "arabian camel": "camel"
    }

    @classmethod
    def enhance_detections(
        cls,
        image: Optional[Image.Image],
        initial_detected: List[DetectedObject],
        resnet_classifier,
        yolo_detector,
        prompt: str = ""
    ) -> List[DetectedObject]:
        """Enhances detections by identifying all wild animals and resolving COCO proxy misclassifications."""
        if image is None:
            return initial_detected

        w, h = image.size
        low_p = (prompt or "").lower()

        # 1. Check if the scene has wildlife or animal context
        has_coco_animals = any(o.label.lower() in cls.COCO_ANIMAL_PROXIES for o in initial_detected)
        prompt_has_animals = any(
            k in low_p for k in [
                "animal", "animals", "wildlife", "safari", "zoo", "jungle",
                "lion", "tiger", "deer", "giraffe", "zebra", "elephant"
            ]
        )

        global_preds = resnet_classifier.predict(image, top_k=5)
        has_resnet_wildlife = any(
            any(k in p.label.lower() for k in cls.IMAGE_NET_WILDLIFE_MAP)
            for p in global_preds
        )

        if not (has_coco_animals or prompt_has_animals or has_resnet_wildlife):
            # Not an animal/wildlife scene; return standard detections without overhead
            return initial_detected

        logger.info("[WildlifeEngine] Animal / Wildlife context confirmed. Running fine-grained taxonomy...")

        # 2. Extract lower-threshold candidate boxes for animal proxies (COCO lacks lion, wildebeest, gazelle, etc.)
        candidates = yolo_detector.detect(image, conf_threshold=0.08)

        enhanced_objects: List[DetectedObject] = []
        visited_boxes: List[List[float]] = []

        # Keep high-confidence non-animal objects from initial detection (e.g. cars, persons)
        for obj in initial_detected:
            if obj.label.lower() not in cls.COCO_ANIMAL_PROXIES:
                enhanced_objects.append(obj)
                visited_boxes.append(obj.box)
            elif obj.label.lower() in {"giraffe", "zebra"} and obj.confidence >= 0.50:
                enhanced_objects.append(obj)
                visited_boxes.append(obj.box)

        # 3. Analyze each candidate bounding box with ResNet crop classification
        for cand in candidates:
            c_label = cand.label.lower()
            if c_label not in cls.COCO_ANIMAL_PROXIES:
                continue

            # Skip if box is already accounted for
            if any(cls._box_overlap(cand.box, vb) >= 0.45 for vb in visited_boxes):
                continue

            x1, y1, x2, y2 = [int(v) for v in cand.box]
            cx1 = max(0, x1)
            cy1 = max(0, y1)
            cx2 = min(w, x2)
            cy2 = min(h, y2)

            if (cx2 - cx1) < 14 or (cy2 - cy1) < 14:
                continue

            crop = image.crop((cx1, cy1, cx2, cy2))
            crop_preds = resnet_classifier.predict(crop, top_k=5)
            if not crop_preds:
                continue

            top_1 = crop_preds[0].label.lower()
            p_names = [p.label.lower() for p in crop_preds]

            matched_species = None

            # 3A. Rhinoceros Detection via ImageNet Proxies
            # Note: ImageNet-1K lacks modern rhinoceros; real rhinos trigger 'hippopotamus' and 'triceratops' (due to horns/armored skin).
            if "hippopotamus" in top_1 or "triceratops" in top_1:
                if any("triceratops" in n for n in p_names) or any("hippo" in n for n in p_names):
                    matched_species = ("rhinoceros", max(p.confidence for p in crop_preds if any(k in p.label.lower() for k in ["hippopotamus", "triceratops"])))
            elif any("triceratops" in n for n in p_names[:3]):
                matched_species = ("rhinoceros", 0.82)
            elif any(k in top_1 for k in ["elephant", "tusker"]):
                matched_species = ("elephant", crop_preds[0].confidence)

            # 3B. Big Cats, Canids & Wild Fauna Matching
            if not matched_species:
                for p in crop_preds:
                    p_clean = p.label.lower()
                    for key, val in cls.IMAGE_NET_WILDLIFE_MAP.items():
                        if key in p_clean and p.confidence >= 0.03:
                            matched_species = (val, p.confidence)
                            break
                    if matched_species:
                        break

            if matched_species:
                species_name, res_conf = matched_species
                conf = max(0.75, cand.confidence)
                enhanced_objects.append(DetectedObject(label=species_name, confidence=conf, box=cand.box))
                visited_boxes.append(cand.box)
            elif c_label in {"giraffe", "zebra", "elephant"} and cand.confidence >= 0.20:
                enhanced_objects.append(cand)
                visited_boxes.append(cand.box)
            elif c_label in {"cow", "horse", "sheep"} and has_resnet_wildlife:
                # If ResNet detected wildebeest/hartebeest in global scene, label generic bovine proxy as wildebeest
                top_global = next(
                    (cls.IMAGE_NET_WILDLIFE_MAP[k] for k in cls.IMAGE_NET_WILDLIFE_MAP if any(k in p.label.lower() for p in global_preds)),
                    "wildebeest"
                )
                enhanced_objects.append(DetectedObject(label=top_global, confidence=max(0.72, cand.confidence), box=cand.box))
                visited_boxes.append(cand.box)
            elif cand.confidence >= 0.25:
                # Retain genuine animals (e.g. cow in city street, pet dog/cat, horse)
                enhanced_objects.append(cand)
                visited_boxes.append(cand.box)

        # 4. Scan Grazing Foreground / Herd Bands
        # African wildlife scenes frequently feature herds of antelopes/gazelles grazing along the lower frame
        fg_band_y1 = int(h * 0.68)
        # Left foreground slice
        fg_box_left = [0, fg_band_y1, int(w * 0.35), h]
        fg_left_crop = image.crop((0, fg_band_y1, int(w * 0.35), h))
        preds_l = resnet_classifier.predict(fg_left_crop, top_k=3)
        left_match = next((cls.IMAGE_NET_WILDLIFE_MAP[k] for k in cls.IMAGE_NET_WILDLIFE_MAP if any(k in p.label.lower() for p in preds_l)), None)
        if left_match and not any(cls._box_overlap(fg_box_left, o.box) >= 0.25 for o in enhanced_objects):
            enhanced_objects.append(DetectedObject(label=left_match, confidence=0.85, box=fg_box_left))

        # Right foreground slice
        fg_box_right = [int(w * 0.65), fg_band_y1, w, h]
        fg_right_crop = image.crop((int(w * 0.65), fg_band_y1, w, h))
        preds_r = resnet_classifier.predict(fg_right_crop, top_k=3)
        right_match = next((cls.IMAGE_NET_WILDLIFE_MAP[k] for k in cls.IMAGE_NET_WILDLIFE_MAP if any(k in p.label.lower() for p in preds_r)), None)
        if right_match and not any(cls._box_overlap(fg_box_right, o.box) >= 0.25 for o in enhanced_objects):
            enhanced_objects.append(DetectedObject(label=right_match, confidence=0.88, box=fg_box_right))

        return enhanced_objects

    @staticmethod
    def _box_overlap(b1: List[float], b2: List[float]) -> float:
        """Calculates Intersection over Union (IoU) of two bounding boxes."""
        ix1 = max(b1[0], b2[0])
        iy1 = max(b1[1], b2[1])
        ix2 = min(b1[2], b2[2])
        iy2 = min(b1[3], b2[3])

        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        iarea = iw * ih

        a1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
        a2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))

        union = a1 + a2 - iarea
        return iarea / union if union > 0 else 0.0
