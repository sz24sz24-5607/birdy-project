"""
TensorFlow Lite Bird Classifier mit iNaturalist Modell
"""
import time
import logging
import numpy as np
from pathlib import Path
from PIL import Image
from django.conf import settings

logger = logging.getLogger('birdy')

from ai_edge_litert.interpreter import Interpreter


class BirdClassifier:
    """TensorFlow Lite Vogel-Klassifikator"""
    
    def __init__(self):
        self.model_path = settings.BIRDY_SETTINGS['ML_MODEL_PATH']
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.is_initialized = False
        self.labels = {}
        
    def initialize(self):
        """Initialisiere TensorFlow Lite Modell"""
            
        try:
            if not Path(self.model_path).exists():
                logger.warning(f"Model file not found: {self.model_path}")
                logger.info("Please download a bird classification model")
                logger.info("Example: https://tfhub.dev/google/aiy/vision/classifier/birds_V1/1")
                return False
            
            self.interpreter = Interpreter(model_path=str(self.model_path))
            self.interpreter.allocate_tensors()
            
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            logger.info(f"Model loaded: {self.model_path}")
            logger.info(f"Input: {self.input_details[0]['shape']} {self.input_details[0]['dtype']}")
            logger.info(f"Output: {self.output_details[0]['shape']}")
            
            self._load_labels()
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_labels(self):
        """Lade Label-Mapping"""
        labels_path = self.model_path.parent / 'labels.txt'
        
        if labels_path.exists():
            try:
                with open(labels_path, 'r', encoding='utf-8') as f:
                    for idx, line in enumerate(f):
                        line = line.strip()
                        if line:
                            self.labels[idx] = line
                logger.info(f"Loaded {len(self.labels)} labels")
            except Exception as e:
                logger.error(f"Failed to load labels: {e}")
        else:
            logger.warning(f"Labels file not found: {labels_path}")
            num_classes = self.output_details[0]['shape'][1]
            self.labels = {i: f"Bird_Species_{i}" for i in range(num_classes)}
    
    def preprocess_image(self, image_path):
        """Bereite Bild für Inferenz vor"""
        try:
            input_shape = self.input_details[0]['shape']
            input_dtype = self.input_details[0]['dtype']
            
            height, width = input_shape[1], input_shape[2]
            
            # Lade und resize
            image = Image.open(image_path).convert('RGB')
            image = image.resize((width, height), Image.LANCZOS)
            
            # Zu numpy
            input_data = np.array(image)
            
            # WICHTIG: Prüfe erwarteten Dtype
            if input_dtype == np.uint8:
                # Modell erwartet UINT8 (0-255)
                input_data = input_data.astype(np.uint8)
            elif input_dtype == np.float32:
                # Modell erwartet FLOAT32 (0-1)
                input_data = input_data.astype(np.float32) / 255.0
            else:
                logger.warning(f"Unknown input dtype: {input_dtype}, using float32")
                input_data = input_data.astype(np.float32) / 255.0
            
            # Add batch dimension
            input_data = np.expand_dims(input_data, axis=0)
            
            return input_data
            
        except Exception as e:
            logger.error(f"Failed to preprocess image: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def classify(self, image_path, top_k=5):
        """Klassifiziere Vogel im Bild"""
        if not self.is_initialized:
            logger.warning("Classifier not initialized")
            return None
        
        try:
            start_time = time.time()
            
            input_data = self.preprocess_image(image_path)
            if input_data is None:
                return None
            
            # Inferenz
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()
            
            # Predictions
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            predictions = output_data[0]
            
            # Top-K
            top_indices = np.argsort(predictions)[-top_k:][::-1]

            # Normalisiere Confidence auf 0-1 wenn Werte > 1
            # (manche Modelle geben 0-100 zurück, wir brauchen 0-1)
            max_pred = float(np.max(predictions))
            scale_factor = 100.0 if max_pred > 1.0 else 1.0

            results = {
                'top_prediction': {
                    'class_id': int(top_indices[0]),
                    'label': self.labels.get(int(top_indices[0]), 'Unknown'),
                    'confidence': float(predictions[top_indices[0]]) / scale_factor
                },
                'top_k_predictions': [
                    {
                        'class_id': int(idx),
                        'label': self.labels.get(int(idx), 'Unknown'),
                        'confidence': float(predictions[idx]) / scale_factor
                    }
                    for idx in top_indices
                ],
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
            
            logger.info(
                f"Classification: {results['top_prediction']['label']} "
                f"({results['top_prediction']['confidence']:.3f}) "
                f"in {results['processing_time_ms']}ms"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def is_confident_detection(self, classification_result):
        """Prüfe ob Klassifikation confident genug ist"""
        if not classification_result:
            return False
        
        threshold = settings.BIRDY_SETTINGS['MIN_CONFIDENCE_THRESHOLD']
        confidence = classification_result['top_prediction']['confidence']
        
        return confidence >= threshold


_classifier_instance = None

def get_classifier():
    """Hole Singleton Instance des Classifiers"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = BirdClassifier()
        _classifier_instance.initialize()
    return _classifier_instance