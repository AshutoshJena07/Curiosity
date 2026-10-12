"""Layer 2 Sub-Module: Traffic & Road Safety Rule Violation Engine.

Provides automated intelligence for:
1. Two-Wheeler (Motorcycle/Scooter/Bicycle) Identification & Rider Association
2. Triple Riding / Multi-Passenger Overloading (Section 128, Motor Vehicles Act)
3. Protective Headgear / Helmet Detection vs Bare Head (Section 129, Motor Vehicles Act)
4. Distracted Driving / Mobile Phone Usage Detection (Section 184(c), Motor Vehicles Act)
5. Comprehensive Traffic Rule Violation & Penalty Summarization
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image
import numpy as np

from src.curiosity.layer_0_core.contracts import (
    DetectedObject,
    TrafficViolation
)

logger = logging.getLogger("curiosity.layer_2.traffic")


class TrafficRuleViolationEngine:
    """Evaluates two-wheeler surveillance images for helmet compliance and triple riding violations."""

    TWO_WHEELER_LABELS = {"motorcycle", "bicycle"}
    RIDER_LABELS = {"person"}

    @classmethod
    def analyze(
        cls,
        image: Optional[Image.Image],
        detected_objects: List[DetectedObject],
        prompt: str = ""
    ) -> Tuple[List[TrafficViolation], str]:
        """Analyzes visual objects for traffic and helmet safety violations."""
        if not detected_objects:
            return [], ""

        violations: List[TrafficViolation] = []
        low_p = (prompt or "").lower()
        is_traffic_query = any(k in low_p for k in ["helmet", "traffic", "challan", "bike", "rider", "motorcycle", "rule", "violation", "speed", "triple ride"])

        # Filter high-confidence two-wheelers and persons
        raw_vehicles = [o for o in detected_objects if o.label.lower() in cls.TWO_WHEELER_LABELS and o.confidence >= 0.45]
        # Robust foreground vehicle filter: ignore tiny background bikes (< 18% of largest vehicle area)
        if raw_vehicles:
            max_veh_area = max(((v.box[2] - v.box[0]) * (v.box[3] - v.box[1])) for v in raw_vehicles)
            vehicles = [v for v in raw_vehicles if ((v.box[2] - v.box[0]) * (v.box[3] - v.box[1])) >= 0.18 * max_veh_area]
        else: 
            vehicles = []

        raw_persons = [o for o in detected_objects if o.label.lower() in cls.RIDER_LABELS and o.confidence >= 0.18]
        phones = [o for o in detected_objects if o.label.lower() == "cell phone"]

        # 1. Non-Maximum Suppression (NMS) & Containment Deduplication on Persons
        # Prevents counting the same rider multiple times when YOLO detects torso + full body
        persons = cls._deduplicate_persons(raw_persons)

        # 2. Case A: Two-wheelers localized in the frame
        if vehicles:
            # Strictly assign each person to at most one vehicle based on spatial proximity and scale
            vehicle_rider_map = cls._assign_riders_to_vehicles(vehicles, persons, detected_objects)
            for v_idx, veh in enumerate(vehicles):
                veh_riders = vehicle_rider_map.get(v_idx, [])
                cls._evaluate_vehicle_riders(image, veh, veh_riders, phones, violations)

        # Case B: If no explicit vehicle detected by YOLO, only check riding cluster if traffic query is asked
        elif len(persons) >= 2 and is_traffic_query:
            riding_cluster = cls._detect_riding_cluster(persons)
            if riding_cluster:
                cluster_veh = DetectedObject(
                    label="motorcycle",
                    confidence=0.85,
                    box=cls._compute_enclosing_box(riding_cluster)
                )
                cls._evaluate_vehicle_riders(image, cluster_veh, riding_cluster, phones, violations)

        # Case C: Check solo persons ONLY if user explicitly asked for helmet or traffic check
        elif len(persons) == 1 and is_traffic_query and image is not None:
            p = persons[0]
            has_helmet, conf, desc = cls._inspect_helmet(image, p.box)
            if not has_helmet:
                violations.append(
                    TrafficViolation(
                        violation_type="No Helmet Violation",
                        rule_code="Section 129, Motor Vehicles Act, 1988",
                        severity="HIGH",
                        confidence=conf,
                        description="Rider localized without mandatory protective safety headgear.",
                        penalty="Rs. 1,000 fine + 3-month driving license disqualification",
                        bbox=p.box,
                        rider_count=1,
                        helmets_detected=0,
                        helmets_missing=1
                    )
                )

        summary = cls._generate_summary(violations, len(vehicles), len(persons))
        return violations, summary

    @classmethod
    def _deduplicate_persons(cls, persons: List[DetectedObject]) -> List[DetectedObject]:
        """Eliminates duplicate/nested bounding boxes for the same person using NMS and containment."""
        if len(persons) <= 1:
            return persons

        # Sort by confidence descending
        sorted_p = sorted(persons, key=lambda p: p.confidence, reverse=True)
        kept: List[DetectedObject] = []

        for p in sorted_p:
            b1 = p.box
            a1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
            duplicate = False

            for k in kept:
                b2 = k.box
                a2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))

                ix1 = max(b1[0], b2[0])
                iy1 = max(b1[1], b2[1])
                ix2 = min(b1[2], b2[2])
                iy2 = min(b1[3], b2[3])

                inter_w = max(0.0, ix2 - ix1)
                inter_h = max(0.0, iy2 - iy1)
                inter_area = inter_w * inter_h

                iou = inter_area / (a1 + a2 - inter_area) if (a1 + a2 - inter_area) > 0 else 0
                # Tandem riders sitting together have overlapping bounds; only deduplicate if identical box (IoU >= 0.55)
                if iou >= 0.55:
                    duplicate = True
                    break

            if not duplicate:
                kept.append(p)

        return kept

    @classmethod
    def _assign_riders_to_vehicles(
        cls,
        vehicles: List[DetectedObject],
        persons: List[DetectedObject],
        all_detected: Optional[List[DetectedObject]] = None
    ) -> Dict[int, List[DetectedObject]]:
        """Strictly assigns each distinct person to at most one vehicle based on spatial score and scale."""
        assignments: Dict[int, List[DetectedObject]] = {i: [] for i in range(len(vehicles))}
        if not vehicles:
            return assignments

        if persons:
            for p in persons:
                px1, py1, px2, py2 = p.box
                pw = px2 - px1
                ph = py2 - py1
                pcx = (px1 + px2) / 2.0

                best_v_idx = -1
                best_score = -1.0

                for vi, v in enumerate(vehicles):
                    vx1, vy1, vx2, vy2 = v.box
                    vw = vx2 - vx1
                    vh = vy2 - vy1

                    overlap_x = max(0.0, min(vx2, px2) - max(vx1, px1))
                    # Seated rider check: rider bottom (waist/legs) MUST descend into the vehicle's upper seat area
                    vert_contact = (py2 >= vy1 + (0.05 * vh)) and (py1 <= vy2 - (0.10 * vh))

                    # Strict horizontal overlap: rider must physically sit within vehicle width
                    if (overlap_x < 0.28 * pw and overlap_x < 0.22 * vw) or not vert_contact:
                        continue

                    # Scale consistency: rider height vs vehicle height
                    scale_ratio = ph / max(1.0, vh)
                    if scale_ratio < 0.40 or scale_ratio > 1.95:
                        continue

                    # Proximity score based on overlap and horizontal alignment
                    score = (overlap_x / max(1.0, pw)) - (abs(pcx - (vx1 + vx2) / 2.0) / max(1.0, vw) * 0.25)
                    if score > best_score:
                        best_score = score
                        best_v_idx = vi

                if best_v_idx >= 0 and best_score > 0.20:
                    assignments[best_v_idx].append(p)

        # Sort riders on each vehicle horizontally front-to-rear
        for vi in assignments:
            assignments[vi].sort(key=lambda x: x.box[0])

        return assignments

    @classmethod
    def _box_match(cls, b1: List[float], b2: List[float], tol: float = 8.0) -> bool:
        return all(abs(c1 - c2) <= tol for c1, c2 in zip(b1, b2))

    @classmethod
    def _detect_riding_cluster(cls, persons: List[DetectedObject]) -> List[DetectedObject]:
        """Detects if multiple persons are clustered together in a tandem motorcycle formation."""
        if len(persons) < 2:
            return []

        # Check vertical and horizontal tight proximity
        persons_sorted = sorted(persons, key=lambda p: p.box[0])
        cluster = []
        for i in range(len(persons_sorted) - 1):
            p1 = persons_sorted[i]
            p2 = persons_sorted[i + 1]

            # Overlapping or adjacent horizontal span
            dx = abs(p2.box[0] - p1.box[0])
            dy = abs(p2.box[1] - p1.box[1])

            avg_w = (p1.box[2] - p1.box[0] + p2.box[2] - p2.box[0]) / 2.0
            avg_h = (p1.box[3] - p1.box[1] + p2.box[3] - p2.box[1]) / 2.0

            if dx < avg_w * 1.3 and dy < avg_h * 0.45:
                if p1 not in cluster:
                    cluster.append(p1)
                if p2 not in cluster:
                    cluster.append(p2)

        return cluster if len(cluster) >= 2 else []

    @classmethod
    def _compute_enclosing_box(cls, objects: List[DetectedObject]) -> List[float]:
        x1 = min(o.box[0] for o in objects)
        y1 = min(o.box[1] for o in objects)
        x2 = max(o.box[2] for o in objects)
        y2 = max(o.box[3] for o in objects)
        return [x1, y1, x2, y2]

    @classmethod
    def _evaluate_vehicle_riders(
        cls,
        image: Optional[Image.Image],
        vehicle: DetectedObject,
        riders: List[DetectedObject],
        phones: List[DetectedObject],
        violations: List[TrafficViolation]
    ) -> None:
        """Evaluates helmet status, rider count, and phone distraction on a single two-wheeler."""
        num_riders = len(riders)
        if num_riders == 0:
            return

        # ── 1. HELMET COMPLIANCE CHECK FOR ALL RIDERS ───────────────────────
        helmets_detected = 0
        helmets_missing = 0
        missing_roles = []

        for idx, rider in enumerate(riders):
            role_label = "Driver / Main Rider" if idx == 0 else f"Pillion Rider {idx}"
            has_helmet, conf, desc = cls._inspect_helmet(image, rider.box)

            if has_helmet:
                helmets_detected += 1
            else:
                helmets_missing += 1
                missing_roles.append(role_label)

        # ── 2. TRIPLE RIDING / OVERLOADING VIOLATION CHECK ──────────────────
        if num_riders >= 3:
            severity = "CRITICAL" if num_riders >= 4 else "HIGH"
            v_title = "Triple Riding (Overloading)" if num_riders == 3 else f"Dangerous Overloading ({num_riders} Riders)"
            violations.append(
                TrafficViolation(
                    violation_type=v_title,
                    rule_code="Section 128, Motor Vehicles Act, 1988",
                    severity=severity,
                    confidence=0.95,
                    description=(
                        f"Unlawful passenger overloading: {num_riders} occupants detected riding on a single "
                        f"two-wheeler. Motor Vehicles Act permits a maximum of 2 occupants (1 driver + 1 pillion rider)."
                    ),
                    penalty="Rs. 1,000 fine + 3-month driving license disqualification (MV Act Sec 128/194C)",
                    vehicle_bbox=vehicle.box,
                    rider_count=num_riders,
                    helmets_detected=helmets_detected,
                    helmets_missing=helmets_missing
                )
            )

        if helmets_missing > 0:
            role_str = ", ".join(missing_roles)
            violations.append(
                TrafficViolation(
                    violation_type="No Helmet Violation",
                    rule_code="Section 129, Motor Vehicles Act, 1988",
                    severity="HIGH",
                    confidence=0.92,
                    description=(
                        f"Failure to wear protective headgear: {helmets_missing} of {num_riders} occupant(s) "
                        f"detected without safety helmet ({role_str})."
                    ),
                    penalty="Rs. 1,000 fine per bareheaded rider + 3-month driving license disqualification (MV Act Sec 129/194D)",
                    bbox=vehicle.box,
                    vehicle_bbox=vehicle.box,
                    rider_count=num_riders,
                    helmets_detected=helmets_detected,
                    helmets_missing=helmets_missing
                )
            )

        # ── 3. DISTRACTED DRIVING (MOBILE PHONE USAGE) CHECK ─────────────────
        for rider in riders:
            for phone in phones:
                # Check if phone is near rider's head/torso area
                p_x1, p_y1, p_x2, p_y2 = phone.box
                r_x1, r_y1, r_x2, r_y2 = rider.box

                if (p_x1 >= r_x1 - 30 and p_x2 <= r_x2 + 30 and p_y1 >= r_y1 and p_y2 <= r_y1 + (r_y2 - r_y1) * 0.75):
                    violations.append(
                        TrafficViolation(
                            violation_type="Mobile Phone Use While Riding",
                            rule_code="Section 184(c), Motor Vehicles Act, 1988",
                            severity="HIGH",
                            confidence=0.90,
                            description="Rider detected operating a handheld mobile device while riding.",
                            penalty="Rs. 1,000 to Rs. 5,000 fine + possible driving suspension",
                            bbox=phone.box,
                            vehicle_bbox=vehicle.box,
                            rider_count=num_riders
                        )
                    )

    @classmethod
    def _inspect_helmet(
        cls,
        image: Optional[Image.Image],
        person_bbox: List[float]
    ) -> Tuple[bool, float, str]:
        """Analyzes upper head region of person bounding box for helmet presence."""
        if image is None:
            # Fallback assumption without image: bareheaded
            return False, 0.85, "Visual head crop unavailable"

        try:
            x1, y1, x2, y2 = [int(max(0, c)) for c in person_bbox]
            p_w = max(10, x2 - x1)
            p_h = max(10, y2 - y1)

            # Crop upper ~28% head crown region
            head_y2 = min(image.height, int(y1 + p_h * 0.28))
            head_crop = image.crop((x1, y1, min(image.width, x2), head_y2))

            if head_crop.width < 8 or head_crop.height < 8:
                return False, 0.80, "Low resolution head region"

            arr = np.array(head_crop.convert("RGB"))

            # 1. Skin tone estimation in upper head crown
            # Typical skin tone in HSV: H in [0, 25], S in [40, 240], V in [60, 255]
            r = arr[:, :, 0].astype(float)
            g = arr[:, :, 1].astype(float)
            b = arr[:, :, 2].astype(float)

            # Approximate human skin tone condition in RGB:
            # R > 95, G > 40, B > 20, max - min > 15, |R - G| > 15, R > G, R > B
            skin_mask = (
                (r > 80) & (g > 35) & (b > 20) &
                ((r - g) > 10) & (r > b) &
                (np.abs(r - g) > 10)
            )
            skin_ratio = np.mean(skin_mask)

            # 2. Dark hair / bare head texture variance
            # Hair typically has very high gradient/texture variance and low brightness
            gray = np.mean(arr, axis=2)
            texture_variance = float(np.var(gray))
            mean_brightness = float(np.mean(gray))

            # 3. Smooth helmet shell signature:
            # Helmets display high specular uniformity (low localized texture variance < 1600).
            # Bare heads, natural hair strands, baseball caps, and dupattas exhibit high variance (> 1600) or visible skin.
            is_bare_head = (texture_variance > 1600) or (skin_ratio > 0.08) or (mean_brightness < 70 and texture_variance > 600)

            # Helmet detected if smooth molded shell profile with low texture variance
            has_helmet = not is_bare_head

            confidence = 0.92 if is_bare_head else 0.88
            desc = "Protective helmet shell detected on crown" if has_helmet else "Bare head / exposed hair detected without helmet"
            return has_helmet, confidence, desc

        except Exception as exc:
            logger.debug(f"[TrafficEngine] Helmet crop analysis exception: {exc}")
            return False, 0.75, "Heuristic inspection inconclusive"

    @classmethod
    def _generate_summary(
        cls,
        violations: List[TrafficViolation],
        vehicle_count: int,
        rider_count: int
    ) -> str:
        """Constructs an executive traffic compliance summary string."""
        if not violations:
            if vehicle_count > 0:
                return f"Two-wheeler traffic compliance verified: {rider_count} rider(s) with valid helmet headgear. No violations observed."
            return "No traffic or two-wheeler safety rule violations detected."

        titles = [f"- {v.violation_type} ({v.rule_code})" for v in violations]
        return f"CRITICAL: {len(violations)} Traffic Rule Violation(s) Detected:\n" + "\n".join(titles)
