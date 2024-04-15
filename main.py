import telebot
from secret_tokens import TELEBOT_API_KEY, GOOGLE_AI_API_KEY, TRIPADVISOR_API
import google.generativeai as genai

import re
import time
import traceback 
import requests

# Telbot
bot = telebot.TeleBot(TELEBOT_API_KEY, parse_mode=None) # You can set parse_mode by default. HTML or MARKDOWN

# Gemini Api
genai.configure(api_key=GOOGLE_AI_API_KEY)

# Set up the model
generation_config = {
  "temperature": 0.3,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}

# safety_settings = [
#   {
#     "category": "HARM_CATEGORY_HARASSMENT",
#     "threshold": "BLOCK_MEDIUM_AND_ABOVE"
#   },
#   {
#     "category": "HARM_CATEGORY_HATE_SPEECH",
#     "threshold": "BLOCK_MEDIUM_AND_ABOVE"
#   },
#   {
#     "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
#     "threshold": "BLOCK_MEDIUM_AND_ABOVE"
#   },
#   {
#     "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
#     "threshold": "BLOCK_MEDIUM_AND_ABOVE"
#   },
# ]


# model = genai.GenerativeModel(model_name='gemini-pro',
# 							  generation_config=generation_config,
# 							  safety_settings=safety_settings)

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_NONE"
  },
]

model = genai.GenerativeModel(model_name='gemini-pro',
							  generation_config=generation_config,
							  safety_settings=safety_settings)

chat_data = {} # Dictionary to store user states and data

def clean_response(text):
    # First, replace literal '\n' with actual newline characters
	text = text.replace('\\n', '\n')

	# Replace '*' with '-'
	text = re.sub(r'(?<!\*)\*(?!\*)', '-', text)

    # Escape Markdown special characters in the text
	text = telebot.formatting.escape_markdown(text)

	# Replace '\*\*' with '**'
    # text = text.replace('\\*\\*', '**')
	text = text.replace('\\*\\*', '**')

	# # Replace '\>\>' with '>>'
	# text = text.replace('\\>\\>', '>>')

	# Replace '\|\>' with '||'
	text = text.replace('\\|\\|', '||')

	return text

# To send sentences one at a time with a delay
def send_gemini_responses(chat_id, gemini_text_respone, delay=1):
	# print("gemini response:", gemini_text_respone)
	# Split the text by the string '||'
	messages = clean_response(gemini_text_respone).split('||')
	# Send each message separately
	print("messages:")
	for message in messages:
		print(message)
		if message.strip():  # If the stripped message is not empty
			bot.send_message(chat_id, message, parse_mode="MarkdownV2")
			time.sleep(delay)

# for responses to /generate
def send_itinerary_response(chat_id, gemini_text_respone, delay=1):
	# Split the text by the character '>>'
	print("clean_response")
	print(clean_response(gemini_text_respone))
	# messages = clean_response(gemini_text_respone).split('\>\>')
	messages = clean_response(gemini_text_respone).split('||')
	# Send each message separately
	print("messages:")
	for message in messages:
		print(message)
		if message.strip():  # If the stripped message is not empty
			bot.send_message(chat_id, message, parse_mode="MarkdownV2")
			time.sleep(delay)

'''
Defining message handlers 
'''

# '/start' command
@bot.message_handler(commands=['start'])
def start(message):
	bot.send_chat_action(message.chat.id, 'typing')
	# Start new Gemini Conversation for the user
	global chat 
	chat = model.start_chat(history=[])
	chat_data[message.chat.id] = {"user_state": "generate_itinerary"}
	
	# Feed behavioural prompt to Gemini
	with open ("initial_prompt.txt", "r") as f:
		behavior_prompt = f.read()
	chat.send_message(behavior_prompt)
	# Reply to user
	gemini_response = chat.history[-1]
	print(gemini_response.parts[0])
	if gemini_response:
		# bot.send_message(message.chat.id, gemini_response.parts[0].text)
		send_gemini_responses(message.chat.id, gemini_response.parts[0].text)
		# to custom output
		global generated_response
		generated_response = False
	else:
		print("No response")
		#TODO: Loging: No reply from gemini ai, ayo i this logic cannot
		bot.send_message(message.chat.id, "There was a mistake.. Please restart the chat by using the `/start` command.")

# '/generate' command
@bot.message_handler(commands=['generate'])
def generate_full_itinerary(message):
	bot.send_chat_action(message.chat.id, 'typing')
	chat_data[message.chat.id] = {"user_state": "generate_itinerary"}
	
	# prompt gemini ai to generate full itinerary
	with open ("itinerary_generation_prompt.txt", "r") as f:
		itinerary_generation_prompt = f.read()
	
	try:
		chat.send_message(itinerary_generation_prompt)
		# Reply to user
		gemini_response = chat.history[-1]
		print(gemini_response.parts[0])
		if gemini_response:
			send_itinerary_response(message.chat.id, gemini_response.parts[0].text)
			global generated_response
			generated_response = True
	except Exception as e:
		print(e)
		bot.send_message(message.chat.id, "Please enter `/start` to start the Travel Bot!")

# '/generate' command
@bot.message_handler(commands=['help'])
def help(message):
	help_message = 'I can help you create your Travel Itinerary.\n\nYou can control me by using these commands:\n\
		`/start` - Create a new Travel Itinerary\n\
		`/generate` - Generate Full Itinerary (After a Travel Itinerary is created)\n\
		`/tripadvisor` - Get review and ratings for locations from TripAdvisor'
	bot.send_message(message.chat.id, help_message)

@bot.message_handler(func=lambda message: chat_data.get(message.chat.id, {}).get("user_state") == "generate_itinerary")
def handle_user_request(message):
	bot.send_chat_action(message.chat.id, 'typing')

	try:
		# pass user's text message to gemini
		chat.send_message(message.text)

		# Reply to user
		gemini_response = chat.history[-1]
		if gemini_response:
			# print(gemini_response.parts[0].text)
			print(gemini_response.parts[0])
			if not generated_response:
				# bot.send_message(message.chat.id, gemini_response.parts[0].text)
				send_gemini_responses(message.chat.id, gemini_response.parts[0].text)
			else:
				send_itinerary_response(message.chat.id, gemini_response.parts[0].text)
	except Exception as e:
		print(e)
		bot.send_message(message.chat.id, "Please enter `/start` to start the Travel Bot!")
		

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

if __name__ == "__main__":
	print("Starting Travel Bot..")
	bot.infinity_polling()
