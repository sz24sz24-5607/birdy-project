"""
Bird Size & Position Detector - SSD MobileNet V2 COCO
Prüft ob ein Vogel ausreichend gross und im Futterbereich sichtbar ist.
"""
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger('birdy')

# COCO class index für "bird" (0-indexed, SSD MobileNet V2 COCO labels)
BIRD_CLASS_ID = 15


class BirdSizeDetector:
    """
    Lightweight Object Detector für Bird Coverage Estimation.

    Nutzt SSD MobileNet V2 COCO (TFLite) um Bird Bounding-Boxes zu detektieren.
    Filtert Frames wo:
    - kein Vogel detektiert wurde
    - die Vogel-Bounding-Box zu klein ist (< MIN_BIRD_COVERAGE)
    - die Bbox-Mitte ausserhalb des konfigurierten ROI liegt

    Outputs des Modells (TFLite_Detection_PostProcess):
      [0] detection_boxes  [1, 20, 4] : [ymin, xmin, ymax, xmax] normalisiert
      [1] detection_classes [1, 20]   : COCO class IDs (0-indexed float32)
      [2] detection_scores  [1, 20]   : confidence 0-1
      [3] num_detections    [1]       : Anzahl valider Detektionen
    """

    def __init__(self):
        self.interpreter = None
        self.input_size = (300, 300)  # SSD MobileNet V2
        self.is_initialized = False

    def initialize(self, model_path=None):
        """Lade TFLite Modell"""
        from django.conf import settings as django_settings

        if model_path is None:
            model_path = django_settings.BIRDY_SETTINGS.get(
                'BIRD_DETECTOR_MODEL_PATH',
                Path(__file__).parent / 'bird_detector.tflite'
            )

        model_path = Path(model_path)
        if not model_path.exists():
            logger.warning(f"Bird detector model not found: {model_path}")
            return False

        try:
            from ai_edge_litert.interpreter import Interpreter

            self.interpreter = Interpreter(model_path=str(model_path))
            self.interpreter.allocate_tensors()

            # Input-Grösse aus Modell lesen
            input_details = self.interpreter.get_input_details()
            shape = input_details[0]['shape']  # [1, H, W, 3]
            self.input_size = (int(shape[2]), int(shape[1]))  # (W, H)

            self.is_initialized = True
            logger.info(f"Bird detector initialized: {model_path.name}, input={self.input_size}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize bird detector: {e}")
            return False

    def detect_bird(self, image_path, min_score=None):
        """
        Detektiere Vogel im Frame und gib beste Detektion zurück.

        Args:
            image_path: Pfad zum Frame (JPEG)
            min_score: Minimale Detection Confidence (aus Settings wenn None)

        Returns:
            dict mit keys 'bbox', 'coverage', 'score', 'center_x', 'center_y'
            oder None wenn kein Vogel detektiert
        """
        if not self.is_initialized:
            return None

        from django.conf import settings as django_settings
        from PIL import Image

        if min_score is None:
            min_score = django_settings.BIRDY_SETTINGS.get('BIRD_DETECTOR_MIN_SCORE', 0.3)

        try:
            img = Image.open(image_path).convert('RGB').resize(self.input_size)
            input_data = np.expand_dims(np.array(img, dtype=np.uint8), axis=0)

            input_details = self.interpreter.get_input_details()
            output_details = self.interpreter.get_output_details()

            self.interpreter.set_tensor(input_details[0]['index'], input_data)
            self.interpreter.invoke()

            boxes = self.interpreter.get_tensor(output_details[0]['index'])[0]    # [20, 4]
            classes = self.interpreter.get_tensor(output_details[1]['index'])[0]  # [20]
            scores = self.interpreter.get_tensor(output_details[2]['index'])[0]   # [20]
            num_det = int(self.interpreter.get_tensor(output_details[3]['index'])[0])

            best = None
            for i in range(min(num_det, len(scores))):
                if scores[i] < min_score:
                    break  # sortiert absteigend nach Score
                if int(classes[i]) != BIRD_CLASS_ID:
                    continue

                ymin, xmin, ymax, xmax = boxes[i]
                coverage = float((ymax - ymin) * (xmax - xmin))

                if best is None or scores[i] > best['score']:
                    best = {
                        'bbox': (float(ymin), float(xmin), float(ymax), float(xmax)),
                        'coverage': coverage,
                        'score': float(scores[i]),
                        'center_x': float((xmin + xmax) / 2),
                        'center_y': float((ymin + ymax) / 2),
                    }

            return best

        except Exception as e:
            logger.error(f"Bird detector inference error: {e}")
            return None

    def is_valid_bird_frame(self, image_path):
        """
        Prüft ob Frame einen ausreichend grossen Vogel im ROI zeigt.

        Returns:
            bool: True = Frame akzeptieren, False = verwerfen
            Wenn Detector nicht initialisiert: True (fail open)
        """
        if not self.is_initialized:
            return True  # fail open: Species Classifier entscheidet

        from django.conf import settings as django_settings
        s = django_settings.BIRDY_SETTINGS

        min_coverage = s.get('MIN_BIRD_COVERAGE', 0.05)
        roi = (
            s.get('BIRD_ROI_X_MIN', 0.05),
            s.get('BIRD_ROI_X_MAX', 0.95),
            s.get('BIRD_ROI_Y_MIN', 0.05),
            s.get('BIRD_ROI_Y_MAX', 0.95),
        )

        detection = self.detect_bird(image_path)

        if detection is None:
            return False  # kein Vogel detektiert

        coverage = detection['coverage']
        cx = detection['center_x']
        cy = detection['center_y']

        if coverage < min_coverage:
            logger.debug(
                f"Bird detector: coverage {coverage:.1%} < {min_coverage:.1%} "
                f"(score={detection['score']:.2f})"
            )
            return False

        roi_x_min, roi_x_max, roi_y_min, roi_y_max = roi
        in_roi = (roi_x_min <= cx <= roi_x_max) and (roi_y_min <= cy <= roi_y_max)

        if not in_roi:
            logger.debug(
                f"Bird detector: center ({cx:.2f},{cy:.2f}) outside ROI "
                f"x=[{roi_x_min},{roi_x_max}] y=[{roi_y_min},{roi_y_max}]"
            )
            return False

        logger.debug(
            f"Bird detector: OK coverage={coverage:.1%} "
            f"center=({cx:.2f},{cy:.2f}) score={detection['score']:.2f}"
        )
        return True


# Singleton
_detector_instance = None


def get_bird_detector(auto_init=True):
    """Hole Singleton-Instanz des Bird Detectors"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = BirdSizeDetector()
        if auto_init:
            _detector_instance.initialize()
    return _detector_instance
