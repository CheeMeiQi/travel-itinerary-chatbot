import telebot
from secret_tokens import TELEBOT_API_KEY, GOOGLE_AI_API_KEY
import google.generativeai as genai

import re
import time

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

	# Replace '\>\>' with '>>'
	text = text.replace('\\>\\>', '>>')
	return text

# To send sentences one at a time with a delay
def send_gemini_responses(chat_id, gemini_text_respone, delay=1):
	# print("gemini response:", gemini_text_respone)
	# Split the text by the character '\n'
	messages = clean_response(gemini_text_respone).split('\n')
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
	messages = clean_response(gemini_text_respone).split('>>')
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
		`/generate` - Generate Full Itinerary (After a Travel Itinerary is created)'
	bot.send_message(message.chat.id, help_message)

@bot.message_handler(func=lambda m: True)
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
		

if __name__ == "__main__":
	print("Starting Travel Bot..")
	bot.infinity_polling()


