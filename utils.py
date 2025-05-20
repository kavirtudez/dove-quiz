import os
import numpy as np
from tensorflow.keras.models import load_model

def load_skin_model():
    """
    Load the trained skin type classification model.
    
    Returns:
        tensorflow.keras.models.Model: The loaded Keras model.
    """
    # Update to use absolute path
    model_path = r"C:\Users\kazzv\Downloads\Hair_Tracker_AI\Hair_Detector_Flask\models\skin_type_model.h5"
    try:
        print(f"Loading skin type model from: {model_path}")
        print(f"File exists: {os.path.exists(model_path)}")
        model = load_model(model_path)
        print("Skin type model loaded successfully")
        return model
    except Exception as e:
        print(f"Error loading skin type model: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def predict_skin_type(image, model):
    """
    Make predictions on skin type using the trained model.
    
    Parameters:
        image (numpy.ndarray): Input image as a NumPy array.
        model (tensorflow.keras.models.Model): Trained Keras model.
        
    Returns:
        dict: Contains prediction results with skin type and probabilities.
    """
    try:
        # Ensure the image is in the right format for prediction
        if len(image.shape) == 3:  # Single image
            image = np.expand_dims(image, axis=0)
            
        # Predict skin type
        y_probs = model.predict(image, verbose=0)
        
        # Map probabilities to skin types (English translations)
        skin_types = ["Oily Skin", "Dry Skin", "Combination Skin", "Normal Skin", "Sensitive Skin"]
        
        # Calculate probabilities as percentages
        probabilities = {skin_type: round(float(prob) * 100, 2) for skin_type, prob in zip(skin_types, y_probs[0])}
        
        # Get the most likely skin type
        predicted_skin_type = skin_types[np.argmax(y_probs[0])]
        
        return {
            "skin_type": predicted_skin_type,
            "probabilities": probabilities
        }
    except Exception as e:
        print(f"Error predicting skin type: {e}")
        import traceback
        print(traceback.format_exc())
        return {"skin_type": "Error", "probabilities": {}} 