from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
# import joblib # Removed as XGB.joblib is no longer used
from PIL import Image
import uuid
import shutil
from werkzeug.utils import secure_filename
# from sklearn.ensemble import RandomForestClassifier # Removed as fallback hairfall model is no longer used
from utils import load_skin_model, predict_skin_type

app = Flask(__name__)
app.secret_key = "hairtracker_flask_secret_key"
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), exist_ok=True)

# Load models
skin_type_model = None
hair_type_model = None
# Fallback model for hairfall prediction (if needed, currently replaced by skin type but good to have)
# hairfall_model = None # Removed as hairfall prediction is no longer a feature

# def create_fallback_hairfall_model(): # Removed as hairfall prediction is no longer a feature
#     \"\"\"Create a simple RandomForest model as a fallback\"\"\"
#     print(\"Creating fallback hairfall prediction model...\")
#     # Simple RandomForest model
#     model = RandomForestClassifier(n_estimators=10, random_state=42)
#     
#     # Train on a small dummy dataset
#     # Features: [pressure_level, stress_level, hair_grease, dandruff]
#     X = [
#         [0, 0, 1, 1], [0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 1, 1],
#         [0, 0, 3, 2], [0, 1, 3, 2], [1, 2, 3, 2], [2, 1, 3, 2],
#         [2, 2, 4, 2], [3, 3, 5, 2]
#     ]
#     # Target: 0 for no hairfall, 1 for hairfall
#     y = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1]
#     
#     model.fit(X, y)
#     print(\"Fallback model created successfully\")
#     return model

try:
    print("Loading hair type model...")
    hair_type_model = load_model(r"C:\Users\kazzv\Downloads\Hair_Tracker_AI\Hair_Detector_Flask\models\hair_type_model.h5")
    print("Hair type model loaded successfully")
    
    print("Loading skin type model...")
    # Load skin type model directly instead of using helper function
    try:
        print("Loading skin type model directly...")
        skin_type_model = load_model(r"C:\Users\kazzv\Downloads\Hair_Tracker_AI\Hair_Detector_Flask\models\skin_type_model.h5")
        print("Skin type model loaded successfully")
    except Exception as e:
        print(f"Error loading skin type model: {e}")
        skin_type_model = None
        
except Exception as e:
    print(f"Error loading models: {e}")
    import traceback
    print(traceback.format_exc())

# Hair type classes
HAIR_TYPE_CLASSES = [
    'Curly Hair', 
    'Straight Hair', 
    'Wavy Hair'
]

# Direct Product Recommendations for Hair Type page
DIRECT_HAIR_PRODUCT_RECOMMENDATIONS = {
    "Straight Hair": {
        "name": "Dove Daily Moisture Shampoo",
        "description": "Nourishes and protects hair from daily wear and tear.",
        "image_filename": "dove daily moisture shampoo.jpg",
        "reason": "It's lightweight enough for straight hair, providing essential hydration without weighing it down, leaving your hair soft and manageable."
    },
    "Wavy Hair": {
        "name": "Dove Nourishing Oil Care Shampoo",
        "description": "Nourishes and smooths wavy hair with essential oils.",
        "image_filename": "Dove Nourishing Oil Care Shampoo.jpg",
        "reason": "Helps to nourish and smooth wavy hair, enhancing its natural texture and reducing frizz for beautifully defined waves."
    },
    "Curly Hair": {
        "name": "Dove Amplified Textures Hydrating Cleanser",
        "description": "Specifically designed for coils, curls, and waves.",
        "image_filename": "Dove Amplified Textures Hydrating Cleanser.jpg",
        "reason": "Provides intense moisture and slip, perfect for defining curls, reducing frizz, and keeping them bouncy and healthy-looking."
    },
    "Unknown": {
        "name": "Dove Nutritive Solutions Intensive Repair Shampoo",
        "description": "A great all-around choice that moisturizes for soft, smooth, manageable hair.",
        "image_filename": "Dove Nutritive Solutions Intensive Repair Shampoo.png",
        "reason": "Provides balanced hydration suitable for most hair types when a specific type isn't identified."
    }
}

# Direct Product Recommendations for Skin Type page
DIRECT_SKIN_PRODUCT_RECOMMENDATIONS = {
    "Normal Skin": {
        "name": "Dove Beauty Bar",
        "description": "Classic moisturizing formula, 1/4 moisturizing cream.",
        "image_filename": "Dove Beauty Bar.jpg",
        "reason": "Gently cleanses and moisturizes, helping to maintain your normal skin's natural balance and softness."
    },
    "Oily Skin": {
        "name": "Dove Men+Care Oil Control Bar",
        "description": "Effectively washes away oil without overdrying skin.",
        "image_filename": "Dove Men+Care Oil Control Bar.png",
        "reason": "Helps to control excess oil and shine, leaving your skin feeling clean and refreshed without stripping essential moisture."
    },
    "Dry Skin": {
        "name": "Dove Sensitive Skin Beauty Bar",
        "description": "Hypoallergenic, fragrance-free, for sensitive and dry skin.",
        "image_filename": "dove sensisitive skin beauty bar.jpg",
        "reason": "Its extra mild and moisturizing formula is perfect for dry skin, helping to replenish moisture and soothe dryness."
    },
    "Combination Skin": {
        "name": "Dove Beauty Bar",
        "description": "Classic moisturizing formula, suitable for balancing skin.",
        "image_filename": "Dove Beauty Bar.jpg",
        "reason": "Gently cleanses all over while moisturizing, helping to balance different areas of combination skin."
    },
    "Sensitive Skin": {
        "name": "Dove Sensitive Skin Beauty Bar",
        "description": "Hypoallergenic, fragrance-free, and ultra-mild for sensitive skin.",
        "image_filename": "dove sensisitive skin beauty bar.jpg",
        "reason": "Provides the gentlest care for sensitive skin, cleansing effectively while minimizing the risk of irritation."
    },
    "Unknown": {
        "name": "Dove Original Beauty Bar",
        "description": "A gentle and classic choice for all skin types.",
        "image_filename": "dove_original_beauty_bar.png", # Placeholder
        "reason": "Its mild and moisturizing formula is a safe bet when the specific skin type isn't clear."
    }
}

# Persona Definitions
PERSONAS = {
    "Kiro": {
        "name": "Radiant Nurturer",
        "description": "You're all about soft shine and self-care. Your hair is your crown, and you take great care of it!",
        "regimen": "Dove Bio-Protein Moisture Shampoo and Conditioner",
        "fun_fact": "Your secret? A balanced routine that keeps her hair soft and glowing! 🌟",
        "shareable_text": "Radiant Nurturer 🥰 - Loving my shiny, healthy hair with Dove's Bio-Protein Moisture Shampoo! 💧✨ #HealthyHair #DoveCare"
    },
    "Elara": {
        "name": "The Hustler",
        "description": "You're a go-getter, tackling life with energy and ambition. Your hair's resilience matches your drive — you've got this!",
        "regimen": "Dove Nutritive Solutions Intensive Repair Shampoo and Conditioner",
        "fun_fact": "You know that resilience is key — her hair shines with strength, even on the busiest days. 💪💁‍♀️",
        "shareable_text": "The Hustler 💪 - Powered through my week with Dove's Intensive Repair range! 💆‍♀️✨ #HairCare #DoveCare #TheHustler"
    },
    "Liana": {
        "name": "The Carefree Spirit",
        "description": "You live life on your terms, embracing every adventure — and your hair reflects your vibrant, carefree spirit!",
        "regimen": "Dove Amplified Textures Hydrating Cleanser and Conditioner",
        "fun_fact": "Your hair? Always full of bounce and personality, just like her! 💫🌈",
        "shareable_text": "Carefree Spirit 🌈 - Letting my curls flow with Dove's Amplified Textures Hydrating Shampoo. 💁‍♀️✨ #CarefreeSpirit #DoveCare"
    },
    "Jude": {
        "name": "The Thoughtful Planner",
        "description": "You think things through and approach every detail with care — and your hair shows that you're dedicated to healthy habits!",
        "regimen": "Dove Nutritive Solutions Strengthening Shampoo and Conditioner",
        "fun_fact": "Your hair care is all about patience, consistency, and nurturing — the results speak for themselves! 🌱",
        "shareable_text": "The Thoughtful Planner 🌱 - Strengthening my hair every day with Dove's Nutritive Solutions range. 🧖‍♂️✨ #HealthyHair #DoveCare"
    }
}

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path, target_size=(150, 150)):
    img = Image.open(image_path)
    img = img.convert("RGB") # Convert image to RGB to remove alpha channel
    img = img.resize(target_size)
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

def save_uploaded_file(file, target_filename=None):
    if file and allowed_file(file.filename):
        # Save as PNG, with a specific filename if provided
        filename = target_filename if target_filename else "latest_uploaded_image.png"
        file_path_in_static = os.path.join('uploads', filename)
        file_path_in_static = file_path_in_static.replace("\\", "/")  # Ensure forward slashes for Flask
        absolute_file_path = os.path.join(app.root_path, 'static', 'uploads', filename)
        try:
            img = Image.open(file.stream)
            img = img.convert("RGB")
            img.save(absolute_file_path, format="PNG")
            print(f"File saved to: {absolute_file_path}")
            if os.path.exists(absolute_file_path):
                print(f"Confirmed: File exists at {absolute_file_path}")
                return file_path_in_static, True
            else:
                print(f"Error: File NOT found at {absolute_file_path} after save attempt.")
                return None, False
        except Exception as e:
            print(f"Error saving file: {e}")
            import traceback
            print(traceback.format_exc())
            return None, False
    elif file:
        print(f"Error: File type not allowed for {file.filename}")
        return None, False
    return None, False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/detect_hair_type', methods=['GET', 'POST'])
def detect_hair_type():
    result = None
    image_path = None
    product_recommendation = None

    if request.method == 'POST':
        if 'image' not in request.files or request.files['image'].filename == '':
            flash('Please upload an image of your hair first!', 'error')
            return redirect(request.url)
        
        file = request.files['image']
        # image_path, success = save_uploaded_file(file) # save_uploaded_file now returns path relative to static
        
        # Re-validate filename just in case, though save_uploaded_file also checks allowed_file
        if file.filename == '': # This check is redundant if the one above is kept, but good for safety
            flash('No selected file. Please upload an image.', 'error')
            return redirect(request.url)

        image_path_relative_to_static, success = save_uploaded_file(file)

        if not success or not image_path_relative_to_static:
            flash('Error saving uploaded file or invalid file type. Please upload a JPG, JPEG, or PNG file.', 'error')
            return redirect(request.url)
        
        image_path = image_path_relative_to_static # For rendering in template

        try:
            # Construct absolute path for model processing
            full_image_path_for_processing = os.path.join(app.root_path, 'static', image_path)
            img_array = preprocess_image(full_image_path_for_processing)

            if hair_type_model is None:
                flash('Hair type model is not available. Please try again later.', 'error')
                print("Error: Hair type model is None during detection.")
                return redirect(request.url)

            prediction = hair_type_model.predict(img_array)
            result = HAIR_TYPE_CLASSES[np.argmax(prediction)]
            product_recommendation = DIRECT_HAIR_PRODUCT_RECOMMENDATIONS.get(result, DIRECT_HAIR_PRODUCT_RECOMMENDATIONS.get("Unknown"))
            print(f"Hair type detection successful. Result: {result}, Image Path: {image_path}")

        except Exception as e:
            flash(f'Error processing image: {str(e)}', 'error')
            print(f"Error during hair type detection: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return redirect(request.url)

    print(f"Rendering hair_type.html with Image Path: {image_path}, Result: {result}")
    return render_template('hair_type.html', result=result, image_path=image_path, product_recommendation=product_recommendation)

@app.route('/detect_skin_type', methods=['GET', 'POST'])
def detect_skin_type():
    result = None
    # probabilities = None # Removed as per instruction
    image_path = None
    product_recommendation = None

    if request.method == 'POST':
        if 'image' not in request.files or request.files['image'].filename == '':
            flash('Please upload an image of your face first!', 'error')
            return redirect(request.url)
        
        file = request.files['image']
        # image_path, success = save_uploaded_file(file) # save_uploaded_file now returns path relative to static

        if file.filename == '': # Redundant if above check kept
            flash('No selected file. Please upload an image.', 'error')
            return redirect(request.url)

        image_path_relative_to_static, success = save_uploaded_file(file)
        
        if not success or not image_path_relative_to_static:
            flash('Error saving uploaded file or invalid file type. Please upload a JPG, JPEG, or PNG file.', 'error')
            return redirect(request.url)
        
        image_path = image_path_relative_to_static # For rendering

        try:
            if skin_type_model is None:
                flash('Skin type model is not available. Please try again later.', 'error')
                print("Error: Skin type model is None during detection.")
                return redirect(request.url)
            
            full_image_path_for_processing = os.path.join(app.root_path, 'static', image_path)
            img_array = preprocess_image(full_image_path_for_processing)
            
            prediction_result = predict_skin_type(img_array, skin_type_model) # predict_skin_type returns a dict
            result = prediction_result.get("skin_type")
            # probabilities = prediction_result.get("probabilities") # Probabilities not sent to template

            if result == "Error" or not result: # Handle error case from predict_skin_type
                flash('Could not determine skin type from the image. Please try another image.', 'error')
                print(f"Skin type detection returned an error or no result for image: {image_path}")
                return redirect(request.url)

            product_recommendation = DIRECT_SKIN_PRODUCT_RECOMMENDATIONS.get(result, DIRECT_SKIN_PRODUCT_RECOMMENDATIONS.get("Unknown"))
            print(f"Skin type detection successful. Result: {result}, Image Path: {image_path}")
            
        except Exception as e:
            flash(f'Error processing image for skin type: {str(e)}', 'error')
            print(f"Error during skin type detection: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return redirect(request.url)

    print(f"Rendering skin_type.html with Image Path: {image_path}, Result: {result}")
    # return render_template('skin_type.html', result=result, probabilities=probabilities, image_path=image_path, product_recommendation=product_recommendation)
    return render_template('skin_type.html', result=result, image_path=image_path, product_recommendation=product_recommendation) # No probabilities

QUIZ_QUESTIONS = {
    1: {
        "type": "welcome",
        "text": "Welcome to Dove's Hair & Skin Health Quiz! 🌸 Let's uncover your personalized care regimen, discover your Dream Strands, and glowing skin! Ready to see which Dove products are made just for you?",
        "button_text": "Start Quiz"
    },
    2: {
        "type": "multiple_choice",
        "text": "Let's start with your hair! How would you describe its current condition?",
        "name": "hair_condition",
        "options": {
            "A": "Dry and Frizzy 🌀",
            "B": "Oily and Heavy 🧴",
            "C": "Fine and Flat 🛏",
            "D": "Thick but Damaged ⚡"
        }
    },
    3: {
        "type": "slider",
        "text": "How much daily pressure and strain do you feel?",
        "name": "stress_level",
        "options": { 
            0: "No pressure", 
            1: "A little pressure", 
            2: "Moderate pressure", 
            3: "A lot of pressure"
        }
    },
    4: {
        "type": "multiple_choice",
        "text": "How greasy does your hair get within a day or two after washing?",
        "name": "hair_grease",
        "options": {
            1: "Not greasy at all",
            2: "Slightly greasy",
            3: "Moderately greasy",
            4: "Very greasy"
        }
    },
    5: {
        "type": "multiple_choice",
        "text": "Do you experience dandruff on your scalp?",
        "name": "dandruff",
        "options": {
            "A": "Yes, frequently",
            "B": "Sometimes, but not too often",
            "C": "No, never"
        }
    },
    6: { 
        "type": "multiple_choice",
        "text": "Have you noticed more hair shedding or thinning recently?",
        "name": "hair_fall",
        "options": {
            "A": "No, my hair seems fine",
            "B": "Slightly, but not too noticeable",
            "C": "Yes, it's becoming more noticeable",
            "D": "A lot, I'm seeing significant hair loss"
        }
    },
    7: {
        "type": "image_upload",
        "text": "Let's take a closer look at your hair. Could you upload a photo for us to identify your hair type?",
        "name": "hair_image",
        "upload_for": "hair_type"
    },
    8: {
        "type": "multiple_choice",
        "text": "How does your skin feel at the end of a long day?",
        "name": "skin_feel",
        "options": {
            "A": "Tight and dry 💧",
            "B": "Oily in some spots, dry in others 🥴",
            "C": "Balanced, glowing skin ✨",
            "D": "Sensitive and irritated 🌿"
        }
    },
    9: {
        "type": "multiple_choice",
        "text": "How sensitive is your skin to changes in the environment or products?",
        "name": "skin_sensitivity",
        "options": {
            "A": "Very sensitive 🥵",
            "B": "Moderately sensitive 😌",
            "C": "Not sensitive at all 💪"
        }
    },
    10: { 
        "type": "multiple_choice",
        "text": "How would you describe your skin after cleansing?",
        "name": "skin_after_cleanse",
        "options": {
            "A": "Feels dry and tight",
            "B": "Feels oily",
            "C": "Feels balanced and smooth",
            "D": "Feels irritated or red"
        }
    },
    11: {
        "type": "image_upload",
        "text": "Could you upload a photo for us to identify your skin type?",
        "name": "skin_image",
        "upload_for": "skin_type"
    }
}

def assign_persona(answers):
    """Assigns a persona based on quiz answers."""
    
    stress_level_ans = answers.get("stress_level") # Will be like "0", "1", "2", "3"
    stress_level = int(stress_level_ans) if stress_level_ans and stress_level_ans.isdigit() else 0

    hair_fall_ans = answers.get("hair_fall")
    hair_fall_concern = hair_fall_ans in ["C", "D"] # True if "Yes, noticeable" or "A lot"

    hair_grease_ans = answers.get("hair_grease") 
    low_grease = hair_grease_ans in ["1", "2"]

    dandruff_ans = answers.get("dandruff")
    dandruff_never = (dandruff_ans == "C")
    
    hair_condition_ans = answers.get("hair_condition") # "A", "B", "C", "D"
    
    classified_hair_type = answers.get('classified_hair_type')

    if stress_level <= 1 and not hair_fall_concern and dandruff_never and low_grease:
        if hair_condition_ans == "A": 
            return PERSONAS["Kiro"]

    if stress_level >= 2:
        if hair_condition_ans == "D": 
             return PERSONAS["Elara"]
        if hair_fall_concern : 
            return PERSONAS["Elara"]

    if classified_hair_type in ["Curly Hair", "Wavy Hair"] and not hair_fall_concern:
         if hair_condition_ans == "C" or not hair_condition_ans in ["A", "D"]:
            return PERSONAS["Liana"]

    if dandruff_ans in ["A", "B"]:
        return PERSONAS["Jude"]
    if hair_fall_concern and not (stress_level >=2 and hair_condition_ans == "D"):
            return PERSONAS["Jude"]
    
    if classified_hair_type == "Straight Hair" and stress_level <=1 and not hair_fall_concern and dandruff_never :
        return PERSONAS["Kiro"]
    if stress_level > 1 and not (hair_condition_ans == "D" or hair_fall_concern): 
        return PERSONAS["Elara"] 
    if dandruff_ans in ["A", "B"]:
        return PERSONAS["Jude"] 
    
    if hair_condition_ans == "A" and stress_level <=1 : return PERSONAS["Kiro"]
    if hair_condition_ans == "D": return PERSONAS["Elara"]
    if hair_condition_ans == "C" and classified_hair_type in ["Curly Hair", "Wavy Hair"]: return PERSONAS["Liana"]

    return PERSONAS["Kiro"]

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.args.get('retake') == 'true':
        session.pop('quiz_step', None)
        session.pop('quiz_answers', None)
        session.modified = True

    if 'quiz_step' not in session:
        session['quiz_step'] = 1
        session['quiz_answers'] = {}
        session.modified = True 

    current_step = session['quiz_step']

    if request.method == 'POST':
        question_config = QUIZ_QUESTIONS.get(current_step)
        if question_config:
            if question_config["type"] == "image_upload":
                if 'image' not in request.files:
                    flash('No image selected for upload.', 'error')
                    return redirect(url_for('quiz'))
                file = request.files['image']
                if file.filename == '':
                    flash('No image selected for upload.', 'error')
                    return redirect(url_for('quiz'))
                # Save as hair_image.png or skin_image.png
                if question_config["upload_for"] == "hair_type":
                    image_path, success = save_uploaded_file(file, target_filename="hair_image.png")
                elif question_config["upload_for"] == "skin_type":
                    image_path, success = save_uploaded_file(file, target_filename="skin_image.png")
                else:
                    image_path, success = save_uploaded_file(file)
                if not success:
                    flash('Invalid file type. Please upload a JPG, JPEG, or PNG file.', 'error')
                    return redirect(url_for('quiz'))
                session['quiz_answers'][question_config["name"]] = image_path
                session.modified = True
                try:
                    full_image_path = os.path.join(app.root_path, 'static', image_path)
                    if question_config["upload_for"] == "hair_type":
                        img_array_hair = preprocess_image(full_image_path)
                        prediction = hair_type_model.predict(img_array_hair)
                        hair_type_result = HAIR_TYPE_CLASSES[np.argmax(prediction)]
                        session['quiz_answers']['classified_hair_type'] = hair_type_result
                        flash(f'Hair type identified: {hair_type_result}', 'info')
                    elif question_config["upload_for"] == "skin_type":
                        img_array_skin = preprocess_image(full_image_path)
                        prediction_result = predict_skin_type(img_array_skin, skin_type_model)
                        session['quiz_answers']['classified_skin_type'] = prediction_result["skin_type"]
                        session['quiz_answers']['skin_probabilities'] = prediction_result["probabilities"]
                        flash(f'Skin type identified: {prediction_result["skin_type"]}', 'info')
                except Exception as e:
                    flash(f'Error processing uploaded image: {str(e)}', 'error')

            elif question_config["type"] != "welcome": 
                answer = request.form.get(question_config["name"])
                if answer:
                    session['quiz_answers'][question_config["name"]] = answer
                    session.modified = True
                elif question_config["type"] != "slider": 
                    flash('Please answer the question to proceed.', 'error')
                    return redirect(url_for('quiz'))
        
        # Updated step navigation logic. QUIZ_QUESTIONS now has a max step of 11.
        max_question_step = 0
        if QUIZ_QUESTIONS: # Ensure QUIZ_QUESTIONS is not empty
            max_question_step = max(QUIZ_QUESTIONS.keys())

        if current_step < max_question_step:
            session['quiz_step'] += 1
        else: # This is hit after the last question (e.g., step 11 if max_question_step is 11)
            session['quiz_step'] = 100 # Go to results
        
        session.modified = True
        if session['quiz_step'] == 100:
            return redirect(url_for('quiz_results'))
        return redirect(url_for('quiz'))

    # Calculate total steps for progress bar.
    progress_total_steps = len(QUIZ_QUESTIONS)
    
    question_to_display = QUIZ_QUESTIONS.get(current_step, QUIZ_QUESTIONS.get(1)) # Default to first if out of bounds

    return render_template('quiz.html', question_data=question_to_display, current_step=current_step, total_steps=progress_total_steps, quiz_answers=session['quiz_answers'])

@app.route('/quiz_results')
def quiz_results():
    if 'quiz_answers' not in session:
        flash("No quiz data found. Please start the quiz.", "warning")
        return redirect(url_for('quiz'))

    answers = session.get('quiz_answers', {})
    persona = assign_persona(answers)

    hair_type = answers.get('classified_hair_type', answers.get('hair_type_preference', 'unknown').capitalize() + " Hair")
    hair_condition = answers.get("hair_condition")
    stress_level = int(answers.get("stress_level", 0))
    hair_grease = int(answers.get("hair_grease", 1))
    dandruff = answers.get("dandruff")
    hair_fall = answers.get("hair_fall")

    hair_fall_risk = {
        "A": "Low", "B": "Moderate", "C": "High", "D": "Very High"
    }.get(hair_fall, "Unknown")

    hair_products = {"shampoo": None, "conditioner": None, "extra_care": None}
    scenario_message = None

    # STRAIGHT HAIR
    if hair_type == "Straight Hair":
        if hair_condition == "A" and stress_level <= 1 and hair_grease <= 2 and dandruff in ["A", "B"]:
            scenario_message = ("Your hair is feeling a bit dry and frizzy, but don't worry — we've got you covered! With low stress and no excess grease, it's time to nourish your hair with the right products for hydration and smoothness.\n\nYour hair will shine with smoothness and vitality! Let Dove's Intense Repair range nurture your hair back to its full potential.")
            hair_products["shampoo"] = {"name": "Dove Nutritive Solutions Intense Repair Shampoo", "desc": "This shampoo deeply nourishes dry, frizzy hair, restoring smoothness and making your hair soft and shiny."}
            hair_products["conditioner"] = {"name": "Dove Nutritive Solutions Intense Repair Conditioner", "desc": "This conditioner strengthens and repairs your hair, helping to reduce frizz and keep your strands healthy."}
        elif hair_condition == "B" and stress_level == 3 and hair_grease == 4 and dandruff == "C":
            scenario_message = ("Your hair's a little oily and heavy, and stress is taking a toll. But don't worry, we'll help balance your hair's moisture while making it feel lighter and more manageable.\n\nWith Dove's Daily Moisture range, you'll keep your hair hydrated and perfectly balanced without the greasy feeling!")
            hair_products["shampoo"] = {"name": "Dove Hair Therapy Daily Moisture Shampoo", "desc": "This shampoo balances oil and moisture without stripping your hair, leaving it clean and manageable."}
            hair_products["conditioner"] = {"name": "Dove Hair Therapy Daily Moisture Conditioner", "desc": "Lightweight, yet hydrating, this conditioner will keep your hair feeling fresh and nourished without weighing it down."}
        elif hair_condition == "C" and stress_level == 2 and hair_grease == 2 and dandruff in ["A", "B"]:
            scenario_message = ("Your fine hair could use a bit more volume, and the slight grease and dandruff are affecting your overall hair health. Let's add some fullness while keeping your scalp clean.\n\nGet ready for more bounce and volume! Dove's Volume & Fullness range will add texture and keep your scalp dandruff-free.")
            hair_products["shampoo"] = {"name": "Dove Volume & Fullness Shampoo", "desc": "This shampoo adds volume to fine hair and keeps it light and bouncy, while gently cleansing."}
            hair_products["conditioner"] = {"name": "Dove Volume & Fullness Conditioner", "desc": "Adds volume to your fine hair, keeping it airy and fresh without weighing it down."}
        elif hair_condition == "D" and stress_level == 3 and hair_grease == 4 and dandruff == "C":
            scenario_message = ("Your thick hair is feeling greasy and stressed, but don't worry! Let's give it the extra care it needs to repair and nourish while managing that excess oil.\n\nYour thick hair deserves this extra care. Dove's Damage Therapy range will help restore moisture, reduce frizz, and make your hair feel healthier.")
            hair_products["shampoo"] = {"name": "Dove Damage Therapy Shampoo", "desc": "This shampoo helps nourish and repair thick, damaged hair while controlling excess grease."}
            hair_products["conditioner"] = {"name": "Dove Damage Therapy Conditioner", "desc": "Moisturizes and strengthens thick hair, reducing breakage and leaving it soft and manageable."}

    # CURLY HAIR
    elif hair_type == "Curly Hair":
        if hair_condition == "A" and stress_level <= 1 and hair_grease == 3 and dandruff == "C":
            scenario_message = ("Your curls are craving some hydration! With low stress and moderate grease, we'll keep those curls moisturized and frizz-free.\n\nYour curls will love this! Dove's Amplified Textures range will keep them bouncy and frizz-free.")
            hair_products["shampoo"] = {"name": "Dove Amplified Textures Hydrating Cleanser", "desc": "This cleanser hydrates and defines your curls while reducing frizz."}
            hair_products["conditioner"] = {"name": "Dove Amplified Textures Hydrating Conditioner", "desc": "Perfect for curl definition and frizz control, this conditioner gives your curls the moisture they need."}
        elif hair_condition == "B" and stress_level == 3 and hair_grease == 4 and dandruff in ["A", "B"]:
            scenario_message = ("Looks like you're dealing with oily, heavy curls and dandruff. Let's clean up that scalp and keep your curls nourished without the grease.\n\nDove's DermaCare Scalp range is the perfect solution for your curly hair with dandruff concerns.")
            hair_products["shampoo"] = {"name": "Dove DermaCare Scalp Anti-Dandruff Shampoo", "desc": "Say goodbye to dandruff while keeping your scalp healthy and your curls hydrated."}
            hair_products["conditioner"] = {"name": "Dove DermaCare Scalp Anti-Dandruff Conditioner", "desc": "This conditioner nourishes your curls without the heavy feeling and tackles dandruff effectively."}
        elif hair_condition == "C" and stress_level == 2 and hair_grease == 1 and dandruff == "C":
            scenario_message = ("Your fine curls are looking for more volume and texture, and we can make it happen! Let's hydrate and bring those curls to life!\n\nLet your curls thrive with Dove's Amplified Textures range! You'll get bounce and fullness with every wash.")
            hair_products["shampoo"] = {"name": "Dove Amplified Textures Hydrating Cleanser", "desc": "Provides moisture while boosting the volume of fine curls."}
            hair_products["conditioner"] = {"name": "Dove Amplified Textures Hydrating Conditioner", "desc": "This conditioner will define your curls and keep them lightweight without weighing them down."}
        elif hair_condition == "D" and stress_level == 3 and hair_grease == 4 and dandruff == "C":
            scenario_message = ("It looks like your thick curls need some extra nourishment to restore their shine and manage the greasiness.\n\nDove's Nourishing Oil Care range will restore moisture, reduce frizz, and smooth your thick curls.")
            hair_products["shampoo"] = {"name": "Dove Nourishing Oil Care Shampoo", "desc": "Helps manage thick, greasy curls and nourishes them with essential oils."}
            hair_products["conditioner"] = {"name": "Dove Nourishing Oil Care Conditioner", "desc": "This conditioner hydrates your curls while controlling frizz and oil."}

    # WAVY HAIR
    elif hair_type == "Wavy Hair":
        if hair_condition == "A" and stress_level <= 1 and hair_grease == 2 and dandruff == "C":
            scenario_message = ("Your wavy hair is in need of hydration and a little extra care. Let's restore the moisture and smoothness while keeping it healthy.\n\nSay goodbye to dry waves! Dove's Intensive Repair range will hydrate and repair your hair for smoother waves.")
            hair_products["shampoo"] = {"name": "Dove Nutritive Solutions Intensive Repair Shampoo", "desc": "Helps repair damaged hair and add hydration without the frizz."}
            hair_products["conditioner"] = {"name": "Dove Nutritive Solutions Intensive Repair Conditioner", "desc": "Deeply nourishes your hair and keeps your waves smooth and healthy."}
        elif hair_condition == "B" and stress_level == 2 and hair_grease == 4 and dandruff in ["A", "B"]:
            scenario_message = ("Looks like your waves need a good cleanse while tackling that dandruff. Let's get your scalp and hair back on track!\n\nGet your waves back on track with Dove's DermaCare Scalp range. It will tackle dandruff and keep your scalp healthy.")
            hair_products["shampoo"] = {"name": "Dove DermaCare Scalp Anti-Dandruff Shampoo", "desc": "Fights dandruff and controls excess oil for your wavy hair."}
            hair_products["conditioner"] = {"name": "Dove DermaCare Scalp Anti-Dandruff Conditioner", "desc": "Adds moisture to your hair without weighing it down, while soothing your scalp."}
        elif hair_condition == "C" and stress_level == 3 and hair_grease == 3 and dandruff == "C":
            scenario_message = ("Your fine waves need some volume and moisture! Let's give them that fullness they deserve.\n\nGet ready for full, bouncy waves! Dove's Volume & Fullness range will give your hair the volume it needs to shine.")
            hair_products["shampoo"] = {"name": "Dove Volume & Fullness Shampoo", "desc": "Adds volume to fine waves and smoothness without the greasy feeling."}
            hair_products["conditioner"] = {"name": "Dove Volume & Fullness Conditioner", "desc": "Provides lightweight moisture to prevent your waves from going limp."}
        elif hair_condition == "D" and stress_level == 3 and hair_grease == 4 and dandruff == "C":
            scenario_message = ("Your thick waves are in need of some extra TLC. Let's restore moisture and manage the greasiness.\n\nDove's Damage Therapy range will provide the nourishment your thick waves need to feel soft, smooth, and healthy again.")
            hair_products["shampoo"] = {"name": "Dove Damage Therapy Shampoo", "desc": "Restores and nourishes your thick waves while managing the greasiness."}
            hair_products["conditioner"] = {"name": "Dove Damage Therapy Conditioner", "desc": "Deep hydration to keep your waves smooth and reduce damage."}

    # Fallback if no specific scenario matched
    if not hair_products["shampoo"] and not hair_products["conditioner"]:
        hair_products["shampoo"] = {"name": "Dove Daily Moisture Shampoo", "desc": "A great all-around choice that moisturizes for soft, smooth, manageable hair."}
        hair_products["conditioner"] = {"name": "Dove Daily Moisture Conditioner", "desc": "Helps to smooth and nourish hair, leaving it soft and manageable every day."}
        scenario_message = None # No specific fallback message as per user request

    # Skin product recommendations (structure remains the same, only cleanser for now)
    skin_products = {"cleanser": None, "moisturizer": None}
    skin_type_detected = answers.get('classified_skin_type', 'Unknown')
    skin_feel = answers.get("skin_feel")
    skin_after_cleanse = answers.get("skin_after_cleanse")
    skin_message = None # This is the description for the skin product

    if skin_type_detected == 'Oily':
        skin_products["cleanser"] = "Dove Men+Care Oil Control Bar"
        skin_message = "Controls excess oil while maintaining moisture for smooth skin."
    elif skin_type_detected == 'Dry':
        skin_products["cleanser"] = "Dove Sensitive Skin Beauty Bar"
        skin_message = "Ideal for dry skin, moisturizing and cleansing without irritation."
    elif skin_type_detected == 'Combination':
        skin_products["cleanser"] = "Dove Beauty Bar"
        skin_message = "Balances moisture while gently cleansing combination skin."
    elif skin_type_detected == 'Sensitive' or skin_feel == 'D' or skin_after_cleanse == 'D':
        skin_products["cleanser"] = "Dove Sensitive Skin Beauty Bar"
        skin_message = "Hypoallergenic and mild, perfect for sensitive skin care."
    else: # Default/Normal skin
        skin_products["cleanser"] = "Dove Beauty Bar"
        skin_message = "Gentle and moisturizing, perfect for everyday use."

    # Override based on skin_after_cleanse if needed (optional, current logic does this)
    if skin_after_cleanse == 'A': # Feels dry and tight
        skin_products["cleanser"] = "Dove Sensitive Skin Beauty Bar"
        skin_message = "Ideal for dry skin, moisturizing and cleansing without irritation."
    elif skin_after_cleanse == 'B': # Feels oily
        skin_products["cleanser"] = "Dove Men+Care Oil Control Bar"
        skin_message = "Controls excess oil while maintaining moisture for smooth skin."

    return render_template('quiz_results.html', 
                           answers=answers, 
                           persona=persona, 
                           hair_products=hair_products,
                           skin_products=skin_products,
                           hair_type_detected=hair_type,
                           skin_type_detected=skin_type_detected,
                           scenario_message=scenario_message,
                           hair_fall_risk=hair_fall_risk,
                           skin_message=skin_message,
                           classified_hair_type_prob=answers.get('classified_hair_type_prob'),
                           classified_skin_type_prob=answers.get('classified_skin_type_prob')
                        )

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

if __name__ == '__main__':
    app.run(debug=True) 