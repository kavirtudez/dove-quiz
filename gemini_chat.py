print("gemini_chat.py: Script starting...")
import google.generativeai as genai
print("gemini_chat.py: Imported google.generativeai")
# from google.generativeai import types # Removed: types.Part and types.Content are causing issues
# print("gemini_chat.py: Imported types from google.generativeai")
import os # For environment variables in the future
print("gemini_chat.py: Imported os")

# It's best practice to load API keys from environment variables
# For now, using the provided key directly, but PLEASE CHANGE THIS for production.
GEMINI_API_KEY = "AIzaSyDoQMQhN7K_JlKL8_-o0QxRCFAupnl84g4" 
# Example for future: GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# System instruction for Tita Glow's persona and knowledge
persona_intro = r"""Hi there, sweetie! I'm Tita Glow, your friendly AI auntie who knows a thing or two about keeping your hair happy and your skin glowing.

Whether you've got curls that won't behave, dry patches that need love, or you're just wondering which Dove product fits your vibe — I've got your back!

Think of me as your personal care coach, chika partner, and Dove guide all in one. Want hair that bounces or skin that beams? Let's talk.

So, what are we working on today — hair drama or skin dilemmas? Let's glow together!

IMPORTANT: Please keep your responses short and to the point (3-5 sentences max). Users prefer concise and helpful advice rather than long paragraphs.
"""

knowledge_base = r"""your knowledge: "🧴 Dove Hair Care Products: Benefits & Use Cases
1. Dove Damage Therapy Intensive Repair Shampoo & Conditioner
Benefits: Formulated with Bio-Protein Care and Glutamic Amino Serum, these products help restore damaged hair, making it 10x stronger and visibly repairing 98% of damage.
Use Cases: Ideal for individuals with dry, damaged, or color-treated hair.
User Insight: Users have reported smoother, shinier hair with reduced frizz and breakage after consistent use. 

2. Dove Keratin Tri-Silk Serum Hair Fall Rescue Shampoo
Benefits: Contains DynaZinc Complex to nourish hair from roots to tips, fortifying hair fibers and reducing hair fall.
Use Cases: Suitable for those experiencing hair fall due to stress, environmental factors, or styling damage.
User Insight: Users have noticed less shedding and healthier-looking hair with regular use. 

3. Dove Amplified Textures Hydrating Shampoo & Conditioner
Benefits: Designed for curly and coily hair, these products provide moisture and definition without weighing hair down.
Use Cases: Best for individuals with natural curls seeking hydration and curl definition.
User Insight: Users appreciate the enhanced curl definition and reduced frizz. 

4. Dove DermaCare Scalp Anti-Dandruff Shampoo & Conditioner
Benefits: Formulated with pyrithione zinc to combat dandruff while soothing the scalp.
Use Cases: Ideal for those with dandruff or an itchy, flaky scalp.
User Insight: Users have reported a noticeable reduction in flakes and scalp irritation.

5. Dove Nourishing Oil Care Shampoo & Conditioner
Benefits: Infused with weightless Nutri-oils to nourish and smooth hair without greasiness.
Use Cases: Suitable for individuals with thick or coarse hair needing moisture and frizz control.
User Insight: Users have experienced softer, more manageable hair with reduced frizz. 

🧼 Dove Skin Care Products: Benefits & Use Cases
1. Dove Sensitive Skin Beauty Bar
Benefits: Fragrance-free and hypoallergenic, this bar contains ¼ moisturizing cream to cleanse without stripping natural oils.
Use Cases: Perfect for individuals with sensitive or dry skin.
User Insight: Dermatologists often recommend this bar for its gentle cleansing properties. 

2. Dove Deep Moisture Nourishing Body Wash
Benefits: Utilizes Micro Moisture technology to deliver nourishing micro-droplets, leaving skin soft and hydrated for 24 hours.
Use Cases: Ideal for those with dry skin seeking long-lasting moisture.
User Insight: Users have reported smoother skin with improved texture after regular use. 

3. Dove Cream Serum Body Lotion
Benefits: Combines the potency of facial serums with body lotions, addressing concerns like uneven skin tone, dark spots, and elasticity.
Use Cases: Suitable for individuals looking to target specific body skin concerns.
User Insight: Users have noticed more even skin tone and improved skin firmness. 

4. Dove Plant Milk Cleansing Bars
Benefits: Formulated with plant-based milks, these bars provide a creamy lather that cleanses without drying out the skin.
Use Cases: Ideal for individuals with dry or sensitive skin.
User Insight: Users have praised these bars for their luxurious lather and gentle cleansing properties. 

💡 Additional Tips & Insights
Hair Care Tips:
Brush hair twice daily to distribute natural oils from root to tip.
Protect hair from environmental damage by using UV-protectant products.
Avoid overwashing hair; adjust frequency based on hair type and needs. 

Skin Care Tips:
Apply moisturizers to clean, slightly damp skin for better absorption.
Use lukewarm water during showers to prevent stripping natural oils.
Incorporate serums with active ingredients like niacinamide or hyaluronic acid for targeted skin concerns. 
Always recommend Dove products along with your advice.
"""

TITA_GLOW_SYSTEM_INSTRUCTION_TEXT = persona_intro + knowledge_base
# TITA_GLOW_SYSTEM_INSTRUCTION_PART = types.Part.from_text(text=TITA_GLOW_SYSTEM_INSTRUCTION_TEXT) # Use raw string for system_instruction


# Initial conversation turns to set Tita Glow's persona
INITIAL_CONVERSATION_HISTORY = [
    {'role': 'user', 'parts': [{'text': "Hello, po!"}]},
    {'role': 'model', 'parts': [{'text': "Hello there, sweetie! Kumusta? What can Tita Glow do for you today? Are you looking for some hair care tips, skin care advice, or maybe a little bit of both? Just let me know what's on your mind and we'll get you glowing! ✨"}]}
]

# generation_config = types.GenerateContentConfig( # Assuming GenerateContentConfig is still valid or model accepts dict
#     response_mime_type="text/plain"
# )
# For simplicity, let's try without explicit GenerateContentConfig first if model accepts dicts directly for config.
# If not, we might need to find the new way or if it's still genai.types.GenerateContentConfig
generation_config = {
    "response_mime_type": "text/plain"
}


safety_settings = [ # Adjust safety settings as needed
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash-latest",
    generation_config=generation_config, # Pass the dictionary here
    system_instruction=TITA_GLOW_SYSTEM_INSTRUCTION_TEXT, # Pass raw string
    safety_settings=safety_settings
)

def get_tita_glow_response(user_message_text, conversation_history=None):
    current_chat_session_contents = []
    if conversation_history is None:
        # Start with the initial persona-setting conversation
        current_chat_session_contents.extend(INITIAL_CONVERSATION_HISTORY)
    else:
        # Build from provided history (assuming it's a list of {'role': ..., 'text': ...})
        for msg in conversation_history:
            current_chat_session_contents.append({'role': msg['role'], 'parts': [{'text': msg['text']}]})

    # Add the new user message to the current list of contents
    current_chat_session_contents.append(
        {'role': 'user', 'parts': [{'text': user_message_text}]}
    )

    try:
        # print(f"Sending to Gemini (contents): {current_chat_session_contents}") # Debug print
        response = model.generate_content(current_chat_session_contents)
        
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            bot_response_text = response.candidates[0].content.parts[0].text
            # print(f"Received from Gemini: {bot_response_text}") # Debug print
            return bot_response_text
        else:
            block_reason_str = "Unknown"
            finish_reason_str = "Unknown"
            safety_ratings_str = "N/A"

            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and hasattr(response.prompt_feedback, 'block_reason'):
                block_reason_str = str(response.prompt_feedback.block_reason) # Use str() for enum or object
            
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                     finish_reason_str = str(candidate.finish_reason) # Use str() for enum or object
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    ratings = []
                    for rating in candidate.safety_ratings:
                        # Assuming rating.category and rating.probability are accessible
                        # Convert to string if they are enums or complex objects
                        category_name = str(rating.category)
                        probability_name = str(rating.probability)
                        ratings.append(f"{category_name}: {probability_name}")
                    safety_ratings_str = ", ".join(ratings) if ratings else "None"

            error_message = f"Tita Glow couldn't respond. BlockReason: {block_reason_str}, FinishReason: {finish_reason_str}, SafetyRatings: [{safety_ratings_str}]"
            print(f"DEBUG: {error_message}")
            return "I'm sorry, sweetie, I'm having a little trouble thinking right now. Please try asking something else! 😊"

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        import traceback
        print(traceback.format_exc())
        return "Oh dear, it seems my wires are a bit crossed! Please try again in a moment."

if __name__ == "__main__":
    print("Tita Glow Test Suite:")

    # List available models
    print("\n--- Available Models ---")
    try:
        for m in genai.list_models():
            # Check if the model supports the 'generateContent' method
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model: {m.name} - Supports generateContent")
            else:
                print(f"Model: {m.name} - Does NOT support generateContent (Methods: {m.supported_generation_methods})")
    except Exception as e:
        print(f"Could not list models: {e}")

    # Test 1: Initial greeting and first question (dry hair)
    print("\n--- Test 1: Dry Hair Query ---")
    history_test1 = [] 
    q1_user = "My hair is very dry, what Dove shampoo should I use?"
    print(f"User: {q1_user}")
    resp1_tita = get_tita_glow_response(q1_user, history_test1)
    print(f"Tita Glow: {resp1_tita}")
    if resp1_tita and not resp1_tita.startswith(("Oh dear", "I'm sorry")):
        history_test1.append({'role': 'user', 'text': q1_user})
        history_test1.append({'role': 'model', 'text': resp1_tita})
    else:
        print("Error in Test 1, response was: ", resp1_tita)

    # Test 2: Follow-up question (oily skin), using history from Test 1
    print("\n--- Test 2: Oily Skin Query (with history) ---")
    q2_user = "Thanks! And what about for oily skin?"
    print(f"User: {q2_user}")
    resp2_tita = get_tita_glow_response(q2_user, history_test1) # Pass history from Test 1
    print(f"Tita Glow: {resp2_tita}")
    if resp2_tita and not resp2_tita.startswith(("Oh dear", "I'm sorry")):
        history_test1.append({'role': 'user', 'text': q2_user})
        history_test1.append({'role': 'model', 'text': resp2_tita})
    else:
        print("Error in Test 2, response was: ", resp2_tita)

    # Test 3: Question that might be borderline or off-topic (to check safety/fallback)
    print("\n--- Test 3: Off-topic Query ---")
    history_test3 = []
    q3_user = "What is the capital of France?" # Off-topic for Tita Glow
    print(f"User: {q3_user}")
    resp3_tita = get_tita_glow_response(q3_user, history_test3)
    print(f"Tita Glow: {resp3_tita}")
    # Not adding to history as it's likely a generic or error response

    print("\n--- Final History from Test 1 & 2 (for context) ---")
    for entry in history_test1:
        print(f"{entry['role'].capitalize()}: {entry['text']}") 