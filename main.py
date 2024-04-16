from typing import Final
import telebot
import os
import re
import traceback 
import requests
import vertexai                                           
from vertexai.language_models import TextGenerationModel 
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models

TOKEN: Final = "6409677499:AAEv6YdJw_X8MCuIk0pHQpPYqKssui2p1Ww"
BOT_NAME: Final = "Travel Itinerary Chatbot"
BOT_USERNAME: Final = "@get_that_itinerary_bot"
TRIPADVISOR_API: Final = "1340A505AD4B4495BF6E2A74F2609F68"

# Telebot
bot = telebot.TeleBot(TOKEN, parse_mode=None)

# Dictionary to store user states and data
chat_data = {}

# Commands
@bot.message_handler(commands=['help'])
def help_command(message):
    chat_id = message.chat.id
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(chat_id,
        "Enter the start command and answer all questions. Gemini will help to plan your itinerary!"
    )

@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    bot.send_chat_action(message.chat.id, 'typing')

    try:
        chat_data[chat_id] = {"user_state": "waiting_place", "user_data": {}}
        
        # Initialise model once only
        model, chat, parameters, safety_settings = initialise_model()

        # Store model, parameters, and safety_settings in chat_data
        chat_data[chat_id]["model"] = model
        chat_data[chat_id]["chat"] = chat
        chat_data[chat_id]["parameters"] = parameters
        chat_data[chat_id]["safety_settings"] = safety_settings

        bot.send_message(chat_id, "Hello, let's plan a trip together! Where do you wish to go?")
    except Exception as e:
        print(e)
        bot.send_message(chat_id, "Oops, an error occurred. Please enter /start command again.")

# @bot.message_handler(func=lambda message: True) 
@bot.message_handler(func=lambda message: chat_data.get(message.chat.id, {}).get("user_state", "").startswith("waiting")) 
def get_user_response(message):
    chat_id = message.chat.id
    bot.send_chat_action(message.chat.id, 'typing')

    try:
        user_state = chat_data.get(chat_id, {}).get("user_state", "waiting")

        if user_state == "waiting_place":
            chat_data[chat_id]["user_data"]["Where do you wish to go?"] = message.text
            chat_data[chat_id]["user_state"] = "waiting_travel_period"
            bot.send_message(
                chat_id,
                'What is period of travel (please provides dates)?'
            )
        elif user_state == "waiting_travel_period":
            chat_data[chat_id]["user_data"]["What is period of travel (please provides dates)?"] = message.text
            chat_data[chat_id]["user_state"] = "waiting_origin"
            bot.send_message(
                chat_id,
                'Where are you travelling from?'
            )
        elif user_state == "waiting_origin":
            chat_data[chat_id]["user_data"]["Where are you travelling from?"] = message.text
            chat_data[chat_id]["user_state"] = "waiting_travel_duration"
            bot.send_message(
                chat_id,
                'How many days are you planning to stay?'
            )
        elif user_state == "waiting_travel_duration":
            chat_data[chat_id]["user_data"]["How many days are you planning to stay?"] = message.text
            chat_data[chat_id]["user_state"] = "waiting_budget"
            bot.send_message(
                chat_id,
                'What is your budget?'
            )
        elif user_state == "waiting_budget":
            chat_data[chat_id]["user_data"]["What is your budget?"] = message.text
            chat_data[chat_id]["user_state"] = "waiting_trip_type"
            bot.send_message(
                chat_id,
                'What is your desired type of trip? Eg: Relaxation, backpacker, solo travel, with family, with friends, etc.'
            )
        elif user_state == "waiting_trip_type":
            chat_data[chat_id]["user_data"]["What is your desired type of trip? Eg: Relaxation, backpacker, solo travel, with family, with friends, etc."] = message.text
            chat_data[chat_id]["user_state"] = "waiting_accommodation"
            bot.send_message(
                chat_id,
                'What type of accommodation do you prefer?'
            )
        elif user_state == "waiting_accommodation":
            chat_data[chat_id]["user_data"]["What type of accommodation do you prefer?"] = message.text
            chat_data[chat_id]["user_state"] = "waiting_activities"
            bot.send_message(
                chat_id,
                'Do you have any specific activities or places you want to visit? Eg: Scenery, theme parks, shopping, etc.'
            )
        elif user_state == "waiting_activities":
            chat_data[chat_id]["user_data"]["Do you have any specific activities or places you want to visit? Eg: Scenery, theme parks, shopping, etc."] = message.text
            chat_data[chat_id]["user_state"] = "waiting_preferences"
            bot.send_message(
                chat_id,
                'Any dietary restrictions or preferences?'
            )
        elif user_state == "waiting_preferences":
            chat_data[chat_id]["user_data"]["Any dietary restrictions or preferences?"] = message.text
            chat_data[chat_id]["user_state"] = "waiting_specifications"
            bot.send_message(
                chat_id,
                'Any other requirements or specifications? Eg: How many cities to explore, pace of travel, etc.'
            )
        elif user_state == "waiting_specifications":
            chat_data[chat_id]["user_data"]["Any other requirements or specifications? Eg: How many cities to explore, pace of travel, etc."] = message.text
            bot.send_message(
                chat_id,
                'Please wait a moment while I generate your intinerary...'
            )
            chat_data[chat_id]["user_state"] = "waiting"
            bot.send_chat_action(message.chat.id, 'typing')            
            prompt = construct_prompt(chat_data[chat_id]["user_data"])
            print("Prompt: ", prompt)
            model = chat_data[chat_id].get("model")
            parameters = chat_data[chat_id].get("parameters")
            safety_settings = chat_data[chat_id].get("safety_settings")
            chat = chat_data[chat_id].get("chat")
            llm_response = generate(model, chat, parameters, safety_settings, prompt)
            formatted_response = clean_response(llm_response)

            # Send LLM response to user
            bot.send_message(
                chat_id,
                formatted_response,
                parse_mode="MarkdownV2"
            )    
                  
            reviews_prompt = "What are the reviews talking about on Tripadvisor?"
            bot.send_chat_action(message.chat.id, 'typing')
            llm_response = generate(model, chat, parameters, safety_settings, reviews_prompt)
            formatted_response = clean_response(llm_response)

            # Send LLM response to user
            bot.send_message(
                chat_id,
                formatted_response,
                parse_mode="MarkdownV2"
            )
            
        else:
            print("User message: ", message.text)
            model = chat_data[chat_id].get("model")
            parameters = chat_data[chat_id].get("parameters")
            safety_settings = chat_data[chat_id].get("safety_settings")
            chat = chat_data[chat_id].get("chat")
            llm_response = generate(model, chat, parameters, safety_settings, message.text)
            formatted_response = clean_response(llm_response)
            # Send LLM response to user
            bot.send_message(
                chat_id,
                formatted_response,
                parse_mode="MarkdownV2"
            )
    except Exception as e:
        print(type(e))
        traceback.print_exc()
        bot.send_message(chat_id, "Oops, an error occurred. Please enter /start command again.")

@bot.message_handler(commands=['tripadvisor'])
def tripadvisor_command(message):
    try: 
        chat_id = message.chat.id
        bot.send_chat_action(message.chat.id, 'typing')
        bot.send_message(chat_id,
            "Enter the location you want to search on TripAdvisor."
        )
        # Update user state to indicate that we're waiting for location input
        chat_data[chat_id] = {"user_state": "tripadvisor"}
    except Exception as e:
        print(e)
        bot.send_message(chat_id, "Oops, an error occurred. Please enter /tripadvisor command again.")

@bot.message_handler(func=lambda message: chat_data.get(message.chat.id, {}).get("user_state") == "tripadvisor")
def get_tripadvisor_location(message):
    chat_id = message.chat.id
    location = message.text
    bot.send_chat_action(message.chat.id, 'typing')

    try:
        # Get location ID
        url_locationID = "https://api.content.tripadvisor.com/api/v1/location/search?language=en"
        headers_locationID = {"accept": "application/json"}
        params_locationID = {"key": TRIPADVISOR_API, "searchQuery": location}
        response_locationID = requests.get(url_locationID, headers=headers_locationID, params=params_locationID)
        response_locationID_json = response_locationID.json()
        location_ID = response_locationID_json["data"][0]["location_id"]
        print("Location response: ", response_locationID_json)

        details_message = ""
        url_details = f"https://api.content.tripadvisor.com/api/v1/location/{location_ID}/details?key={TRIPADVISOR_API}&language=en&currency=SGD"
        headers_details = {"accept": "application/json"}
        response_details = requests.get(url_details, headers=headers_details)
        response_details_json = response_details.json()

        ranking = response_details_json["ranking_data"]["ranking_string"]
        web_url = response_details_json["web_url"]
        overall_rating = response_details_json["rating"]
        terrible_rating_count = response_details_json["review_rating_count"]["1"]
        poor_rating_count = response_details_json["review_rating_count"]["2"]
        average_rating_count = response_details_json["review_rating_count"]["3"]
        verygood_rating_count = response_details_json["review_rating_count"]["4"]
        excellent_rating_count = response_details_json["review_rating_count"]["5"]

        details_message += f"**{ranking}**\nLink: {web_url}\nOverall Rating: {overall_rating}\n**Rating Count**\nTerrible: {terrible_rating_count}\nPoor: {poor_rating_count}\nAverage: {average_rating_count}\nVery Good: {verygood_rating_count}\nExcellent: {excellent_rating_count}\n"
        
        formatted_details = clean_response(details_message)
        bot.send_message(
            chat_id,
            formatted_details,
            parse_mode="MarkdownV2"
        )
        
        reviews_message = ""    
        url = f"https://api.content.tripadvisor.com/api/v1/location/{location_ID}/reviews?key={TRIPADVISOR_API}&language=en"
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers)
        print("Response: ", response.text)
        response_json = response.json()
        for review_data in response_json["data"]:
            title = review_data["title"]
            rating = review_data["rating"]
            text = review_data["text"]
            review_url = review_data["url"]
            
            # Append the review details to the message string, separating each review with 2 lines
            reviews_message += f"**{title}**\nRating: {rating}\nReviews: {text}\nLink: {review_url}\n\n"
        formatted_reviews = clean_response(reviews_message)
        bot.send_message(
            chat_id,
            formatted_reviews,
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        print(type(e))
        traceback.print_exc()
        bot.send_message(chat_id, "Oops, an error occurred. Please enter /tripadvisor command again.")

        
def construct_prompt(user_data: dict) -> str:
    # Construct prompt using collected user data
    prompt = f'''Plan a Travel Itinerary according to these requirements:
            \nDestination: {user_data['Where do you wish to go?']}
            \nTravelling from: {user_data['Where are you travelling from?']}
            \nTravel Period: {user_data['What is period of travel (please provides dates)?']}
            \nStay Duration: {user_data['How many days are you planning to stay?']} days
            \nBudget: {user_data['What is your budget?']}
            \nTravel Type: {user_data['What is your desired type of trip? Eg: Relaxation, backpacker, solo travel, with family, with friends, etc.']}
            \nAccommodation Preference: {user_data['What type of accommodation do you prefer?']}
            \nActivities/Places to Visit: {user_data['Do you have any specific activities or places you want to visit? Eg: Scenery, theme parks, shopping, etc.']}
            \nDietary Restrictions/Preferences: {user_data['Any dietary restrictions or preferences?']}
            \nAdditional Requirements: {user_data['Any other requirements or specifications? Eg: How many cities to explore, pace of travel, etc.']}
            \nWith these requirements, generate a full itinerary with all necessary details.
            \nFor each place you suggested, help me find review and ratings on Tripadvisor. Do not provide URL links.
            \nHelp me find available flights for the travel period on Google flights.
            \nHelp me find available accommodations to book based on the accommodation preferences around the places to visit.'''
    return prompt

def clean_response(message):
    # First, replace literal '\n' with actual newline characters
    message = message.replace('\\n', '\n')

    # Replace '*' with '-'
    message = re.sub(r'(?<!\*)\*(?!\*)', '-', message)

    # Escape Markdown special characters in the text
    message = telebot.formatting.escape_markdown(message)

    # Replace double asterisks with single asterisk
    message = message.replace(r'\*\*', '*')
  
    return message


def initialise_model():
    # Initialize Vertex AI access.
    vertexai.init(project="travelitinerarychatbot", location="us-central1")  
    parameters = {                                                 
        "max_output_tokens": 2048,
        "temperature": 0.9,
        "top_p": 1,                                              
    }   
    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }                                                          
    model = GenerativeModel("gemini-1.0-pro-001")
    chat = model.start_chat(history=[])
    return model, chat, parameters, safety_settings 
    

def generate(model, chat, parameters, safety_settings, prompt: str) -> str:
    chat.send_message(prompt, generation_config=parameters, safety_settings=safety_settings)    
    response = chat.history[-1].parts[0]
    print(f"Response from Model: {response.text}")                              
    return response.text 

if __name__ == "__main__":
    print("Starting bot...")
    bot.polling(none_stop=True)
