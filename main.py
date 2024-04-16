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
  "temperature": 0.3, # entropy
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}

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


def markdown_to_html(text):
    # Replace bold (**text**) with <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    
    # Replace italic (*text*) with <i>text</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    
    # Replace underline (__text__) with <u>text</u>
    text = re.sub(r'__(.*?)__', r'<u>\1</u>', text)
    
    # Replace strikethrough (~~text~~) with <s>text</s>
    text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)
    
    # Replace spoiler tags with <span class="tg-spoiler">text</span>
    text = re.sub(r'\|\|(.*?)\|\|', r'<span class="tg-spoiler">\1</span>', text)
    
    # Replace tg-emoji tags with the emoji as content
    text = re.sub(r'<tg-emoji emoji-id="(.*?)">.*?</tg-emoji>', lambda m: chr(int(m.group(1))), text)
    
    # Replace inline URLs with <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    # Replace inline mentions of a user with <a href="tg://user?id=user_id">text</a>
    text = re.sub(r'\[([^\]]+)\]\(tg://user\?id=(\d+)\)', r'<a href="tg://user?id=\2">\1</a>', text)
    
    # Replace pre-formatted fixed-width code block with <pre><code>...</code></pre>
    text = re.sub(r'```(?:.*)\n(.*?)\n```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)
    
    # Replace block quotation with <blockquote>...</blockquote>
    text = re.sub(r'^> (.*)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)
    
    return text

# To send sentences one at a time with a delay
def send_gemini_responses(chat_id, gemini_text_respone, delay=0.5):
	print("gemini response:", gemini_text_respone)
	# Split response into message chunks when '||' or '>>' is seen
	messages = re.split(r'\|\||\>\>', gemini_text_respone) 
	# Send each message separately
	print("messages:")
	for message in messages:
		# print("markdown message: ", message)
		print("html message: ",markdown_to_html(message))
		if message.strip():  # If the stripped message is not empty
			bot.send_message(chat_id, markdown_to_html(message), parse_mode="HTML")
			time.sleep(delay)

def split_into_word_chunks_with_formatting(text, max_length):
    # Split the text into words including any Markdown or HTML characters
    words = re.findall(r'(\S+\s*)', text)
    
    # Initialize variables
    chunks = []
    current_chunk = ""

    # Iterate through each word
    for word in words:
        # If adding the current word to the current chunk would exceed the max length
        if len(current_chunk) + len(word) > max_length:
            # Append the current chunk to the list of chunks
            chunks.append(current_chunk)
            # Start a new chunk with the current word
            current_chunk = word
        else:
            # Add the current word to the current chunk
            current_chunk += word

    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


'''
Defining message handlers 
'''
chat_data = {} # Dictionary to store user states and data

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
	else:
		print("No response")
		bot.send_message(message.chat.id, "There was a mistake.. Please restart the chat by using the `/start` command.")

# '/generate' command
@bot.message_handler(commands=['generate'])
def generate_full_itinerary(message):
	bot.send_chat_action(message.chat.id, 'typing')
	chat_data[message.chat.id] = {"user_state": "generate_itinerary"}
	print("User state: ", chat_data[message.chat.id]["user_state"])
	
	# prompt gemini ai to generate full itinerary
	with open ("itinerary_generation_prompt.txt", "r") as f:
		itinerary_generation_prompt = f.read()
	
	try:
		chat.send_message(itinerary_generation_prompt)
		# Reply to user
		gemini_response = chat.history[-1]
		print(gemini_response.parts[0])
		if gemini_response:
			send_gemini_responses(message.chat.id, gemini_response.parts[0].text)
	except Exception as e:
		print(e)
		bot.send_message(message.chat.id, "Please enter `/start` to start the Travel Bot!")

# '/tripadvisor' command
@bot.message_handler(commands=['tripadvisor'])
def tripadvisor_command(message):
	try: 
		bot.send_chat_action(message.chat.id, 'typing')
		chat_data[message.chat.id] = {"user_state": "tripadvisor"}
		print("chat id: ", message.chat.id)
		print("User state 3: ", chat_data[message.chat.id]["user_state"])
		bot.send_message(message.chat.id,
			"Enter the location you want to search on TripAdvisor."
		)
		# Update user state to indicate that we're waiting for location input
		
	except Exception as e:
		print(e)
		traceback.print_exc()
		bot.send_message(message.chat.id, "Oops, an error occurred. Please enter `/tripadvisor` command again.")

@bot.message_handler(commands=['usefullinks'])
def useful_links(message):
	useful_links = '''
	🌍 **Useful Links for Travellers:**

	1. **Flight Booking:**
		- [Skyscanner](https://www.skyscanner.com/)
		- [Google Flights](https://www.google.com/flights)
		- [Trip](https://www.trip.com/)

	2. **Accommodation Booking:**
		- [Booking.com](https://www.booking.com/)
		- [Airbnb](https://www.airbnb.com/)
		- [Agoda](https://www.agoda.com/)
		- [Hotels.com](https://www.hotels.com/)

	3. **Travel Activities:**
		- [Klook](https://www.klook.com/)
		- [TripAdvisor](https://www.tripadvisor.com/)
		- [Lonely Planet](https://www.lonelyplanet.com/)

	4. **Transportation:**
		- [Rome2rio](https://www.rome2rio.com/) (for planning multi-modal trips)
		- [Uber](https://www.uber.com/) or [Lyft](https://www.lyft.com/) or [Grab](https://www.grab.com/) (for local transportation)

	5. **Currency Conversion:**
		- [XE Currency Converter](https://www.xe.com/currencyconverter/)

	6. **Language Translation:**
		- [Google Translate](https://translate.google.com/)

	7. **Maps and Navigation:**
		- [Google Maps](https://www.google.com/maps)
		- [Maps.me](https://maps.me/) (offline maps)

	8. **Local Events and Activities:**
		- [Eventbrite](https://www.eventbrite.com/)
		- [Meetup](https://www.meetup.com/)

	9. **Travel Insurance:**
		- [World Nomads](https://www.worldnomads.com/)
		- [FWD Travel Insurance](https://www.fwd.com.sg/travel-insurance/)
		- [NTUC Income Travel Insurance](https://www.income.com.sg/travel-insurance)
		- [Great Eastern Travel Insurance](https://www.greateasternlife.com/sg/en/personal-insurance/our-products/travel-insurance/travelsmart-premier.html)
		- [Chubb Travel Insurance](https://www.chubbtravelinsurance.com.sg/)

	10. **Visa Information:**
		- [Passport Index - Visa Checker](https://www.passportindex.org/travel-visa-checker/)

	11. **Emergency Assistance:**
		- [Embassy or Consulate Website](https://www.usembassy.gov/) (for locating nearest embassy or consulate)
		- [Foreign Representatives to Singapore](https://www.mfa.gov.sg/Overseas-Missions/Foreign-Representatives-To-Singapore)

	Explore these resources to make your travel planning easier and more enjoyable! ✈️🌴

	'''
	bot.send_message(message.chat.id, markdown_to_html(useful_links), parse_mode="HTML", disable_web_page_preview=True)

# '/help' command
@bot.message_handler(commands=['help'])
def help(message):
	help_message = "🌍 Welcome to your trusty TravelBot! 🧳\n\
	I'm here to assist you in creating your Travel Itinerary! 🗺️\n\nYou can control me by using these commands:\n\
	`/start` - Create a new Travel Itinerary\n\
	`/generate` - Generate Full Itinerary (After creating a Travel Itinerary)\n\
	`/tripadvisor` - Get reviews and ratings for locations from TripAdvisor\n\
	`/usefullinks` - Useful Links for Travellers"
	bot.send_message(message.chat.id, help_message)

@bot.message_handler(func=lambda message: chat_data.get(message.chat.id, {}).get("user_state") == "generate_itinerary")
# @bot.message_handler(func=lambda message: True)
def handle_user_request(message):
	bot.send_chat_action(message.chat.id, 'typing')
	print("User state 2: ", chat_data[message.chat.id]["user_state"])
	try:
		# pass user's text message to gemini
		chat.send_message(message.text)

		# Reply to user
		gemini_response = chat.history[-1]
		if gemini_response:
			# print(gemini_response.parts[0].text)
			print(gemini_response.parts[0])
			# send gemini response to user
			send_gemini_responses(message.chat.id, gemini_response.parts[0].text)
	except Exception as e:
		print(e)
		bot.send_message(message.chat.id, "Please enter `/start` to start the Travel Bot!")
		

@bot.message_handler(func=lambda message: chat_data.get(message.chat.id, {}).get("user_state") == "tripadvisor")
def get_tripadvisor_location(message):
	bot.send_chat_action(message.chat.id, 'typing')
	chat_id = message.chat.id
	location = message.text
	print("User state 4: ", chat_data[chat_id]["user_state"])

	try:
		# Get location ID
		url_locationID = "https://api.content.tripadvisor.com/api/v1/location/search?language=en"
		headers_locationID = {"accept": "application/json"}
		params_locationID = {"key": TRIPADVISOR_API, "searchQuery": location}
		response_locationID = requests.get(url_locationID, headers=headers_locationID, params=params_locationID)
		response_locationID_json = response_locationID.json()	
		if response_locationID.status_code == 200:	
			print("Location response: ", response_locationID_json)
			location_item = 0
			location_ID = response_locationID_json["data"][location_item]["location_id"] # get first location item from tripadvisor api
			
			url_details = f"https://api.content.tripadvisor.com/api/v1/location/{location_ID}/details?key={TRIPADVISOR_API}&language=en&currency=SGD"
			print(url_details)
			headers_details = {"accept": "application/json"}
			response_details = requests.get(url_details, headers=headers_details)
			print("response_details.status_code: ",response_details.status_code)
			
			# if response_details is invalid, get the next location item
			while response_details.status_code != 200:
				location_item += 1
				location_ID = response_locationID_json["data"][location_item]["location_id"]
				print(f"location_item: {location_item}, location_ID: {location_ID}\n")

				url_details = f"https://api.content.tripadvisor.com/api/v1/location/{location_ID}/details?key={TRIPADVISOR_API}&language=en&currency=SGD"
				print(url_details)
				headers_details = {"accept": "application/json"}
				response_details = requests.get(url_details, headers=headers_details)
				print("response_details.status_code: ",response_details.status_code)

			response_details_json = response_details.json()
			details_message = ""

			if response_details.status_code == 200:				
				print("Details response: ", response_details_json)

				# Check if ranking data exists
				ranking_data = response_details_json.get("ranking_data")
				if ranking_data:
					ranking = ranking_data.get("ranking_string")
					if ranking:
						details_message += f"**{ranking}**\n"

				# Check if overall rating exists
				overall_rating = response_details_json.get("rating")
				if overall_rating:
					details_message += f"Overall Rating: {overall_rating}\n\n"

				# Check if review rating count exists
				review_rating_count = response_details_json.get("review_rating_count")
				if review_rating_count:
					terrible_rating_count = review_rating_count.get("1")
					poor_rating_count = review_rating_count.get("2")
					average_rating_count = review_rating_count.get("3")
					verygood_rating_count = review_rating_count.get("4")
					excellent_rating_count = review_rating_count.get("5")

					details_message += f"**Rating Count**\n"
					details_message += f"- Terrible: {terrible_rating_count}\n"
					details_message += f"- Poor: {poor_rating_count}\n"
					details_message += f"- Average: {average_rating_count}\n"
					details_message += f"- Very Good: {verygood_rating_count}\n"
					details_message += f"- Excellent: {excellent_rating_count}\n"

				# Check if web URL exists
				web_url = response_details_json.get("web_url")
				if web_url:
					details_message += f"\nYou can find out more at: {web_url}!\n"

				formatted_details = markdown_to_html(details_message)
				bot.send_message(
					chat_id, 
					formatted_details, 
					parse_mode="HTML"
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
					reviews_message += f"**{title}**\n- Rating: {rating}\n- Reviews: {text}\n*You can find out more at*: {review_url}\n\n"
				# for cases with long review messages
				chunks = split_into_word_chunks_with_formatting(reviews_message, max_length= 4096)
				for chunk in chunks:
					bot.send_message(
						chat_id,
						markdown_to_html(chunk),
						parse_mode="HTML"
					)
				user_message_prompt = "✈️ Feel free to enter another location you want to search on TripAdvisor! 🗺️\nFor other Itinerary-related functionalities, you may refer to our command palette by entering `/help`. 🚀💡"
				bot.send_message(
					chat_id,
					user_message_prompt,
					parse_mode="HTML"
				)
			else:
				error = response_details_json["error"]["message"]
				bot.send_message(
					chat_id,
					error,
				)
		else:
			bot.send_message(
				chat_id,
				"Location not found. Please try again!"
			)

	except Exception as e:
		print(type(e))
		traceback.print_exc()
		bot.send_message(chat_id, "Oops, an error occurred. Please enter `/tripadvisor` command to try again.")

if __name__ == "__main__":
	print("Starting Travel Bot..")
	bot.infinity_polling()
