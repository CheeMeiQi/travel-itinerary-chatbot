from typing import Final
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import os
import asyncio
import vertexai                                           
from vertexai.language_models import TextGenerationModel 
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models

TOKEN: Final = "6409677499:AAEv6YdJw_X8MCuIk0pHQpPYqKssui2p1Ww"
BOT_NAME: Final = "Travel Itinerary Chatbot"
BOT_USERNAME: Final = "@get_that_itinerary_bot"


# Commands

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter the start command and type where you want to go and what you want to do. I will help to plan your itinerary!"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["llm_active"] = True
    context.chat_data["user_data"] = {}
    context.chat_data["user_state"] = "waiting_place"
    
    # Initialise model once only
    model, chat, parameters, safety_settings = initialise_model()

     # Store model, parameters, and safety_settings in context
    context.chat_data["llm_model"] = model
    context.chat_data["llm_parameters"] = parameters
    context.chat_data["llm_safety_settings"] = safety_settings
    context.chat_data["llm_chat_history"] = chat

    await update.message.reply_text(
        "Hello, let's plan a trip together! Where do you wish to go?"
    )
    
    # # Ask the list of questions and store the user data
    # await askQuestions(update, context)

    # # Construct prompt using collected data
    # prompt = construct_prompt(context.chat_data["user_data"])

    # # Send prompt to LLM to plan itinerary
    # llm_response = generate(model, chat, parameters, safety_settings, prompt)
    # print("Gemini: ", llm_response)

    # # Send LLM response to user
    # await update.message.reply_text(llm_response)


async def askQuestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
        
    # Initialize user data dictionary to store responses
    context.chat_data["user_data"] = {}
    
    # List of questions
    questions = [
        "What is period of travel (please provides dates)?",
        "How many days are you planning to stay?",
        "What is your budget?",
        "What is your desired type of trip? Eg: Relaxation, backpacker, solo travel, with family, with friends, etc.",
        "What type of accommodation do you prefer?",
        "Do you have any specific activities or places you want to visit? Eg: Scenery, theme parks, shopping, etc",
        "Any dietary restrictions or preferences?",
        "Any other requirements or specifications? Eg: How many cities to explore, pace of travel, etc"
    ]
    
    # Iterate through questions and ask one by one
    for question in questions:
        await update.message.reply_text(question)
        
        # Wait for user response
        response = await get_user_response(update, context)
        print("User response: ", response)
        
        # Store user response in chat data
        context.chat_data["user_data"][question] = response
    
    await update.message.reply_text("Thank you for providing the information. I will now generate your itinerary.")    
    
# latest_update_id = -1
async def get_user_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    
    user_state = context.chat_data.get("user_state")

    if user_state == "waiting_place":
        context.chat_data["user_data"]["Where do you wish to go?"] = update.message.text
        context.chat_data["user_state"] = "waiting_travel_period"  # Update state
        await update.message.reply_text(
            'What is period of travel (please provides dates)?'
        )
    elif user_state == "waiting_travel_period":
        context.chat_data["user_data"]["What is period of travel (please provides dates)?"] = update.message.text
        context.chat_data["user_state"] = "waiting_travel_duration"  # Update state
        await update.message.reply_text(
            'How many days are you planning to stay?'
        )
    elif user_state == "waiting_travel_duration":
        context.chat_data["user_data"]["How many days are you planning to stay?"] = update.message.text
        context.chat_data["user_state"] = "waiting_budget"  # Update state
        await update.message.reply_text(
            'What is your budget?'
        )
    elif user_state == "waiting_budget":
        context.chat_data["user_data"]["What is your budget?"] = update.message.text

        prompt = construct_prompt(context.chat_data["user_data"])
        print("Prompt: ", prompt)
        model = context.chat_data.get("llm_model")
        parameters = context.chat_data.get("llm_parameters")
        safety_settings = context.chat_data.get("llm_safety_settings") 
        chat = context.chat_data.get("llm_chat_history")    
        llm_response = generate(model, chat, parameters, safety_settings, prompt)
        print("Gemini: ", llm_response)

        # Send LLM response to user
        await update.message.reply_text(llm_response)
        
        


def construct_prompt(user_data: dict) -> str:
    # Construct prompt using collected user data
    prompt = f'''Travel Itinerary:
            \nDestination: {user_data['Where do you wish to go?']}
            \nTravel Period: {user_data['What is period of travel (please provides dates)?']}
            \nStay Duration: {user_data['How many days are you planning to stay?']} days
            \nBudget: {user_data['What is your budget?']}'''
    return prompt

        
# Helper function to get LLM state from context
def get_llm_state(context):
    return context.chat_data.get("llm_active", False)

# Responses
# def handle_response(text: str, context) -> str:
#     processed: str = text.lower()

#     if get_llm_state(context): 
#         # Get model, parameters, and safety_settings from context
#         model = context.chat_data.get("llm_model")
#         parameters = context.chat_data.get("llm_parameters")
#         safety_settings = context.chat_data.get("llm_safety_settings") 
#         chat = context.chat_data.get("llm_chat_history")    
#         llm_response = generate(model, chat, parameters, safety_settings, text)
#         return llm_response        

#     else:
#         if "hello" in processed:
#             return "Hey there! Where would you like to go?"

#     return "I do not understand what you wrote..."


# # Handle messages
# async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     message_type: str = update.message.chat.type
#     text: str = update.message.text  

#     print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

#     if "group" in message_type:
#         if BOT_USERNAME in text:
#             new_text: str = text.replace(BOT_USERNAME, "").strip()
#             # response: str = handle_response(new_text, context)
#         else:
#             return
#     else:
#         # response: str = handle_response(text, context)

#     # print("Bot: ", response)
#     # await update.message.reply_text(response)


# Logging errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

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
    # model = TextGenerationModel.from_pretrained("text-bison@002") 
    model = GenerativeModel("gemini-1.0-pro-001")
    chat = model.start_chat(history=[])
    return model, chat, parameters, safety_settings 
    


def generate(model, chat, parameters, safety_settings, prompt: str) -> str:
    
    # response = model.predict(prompt, **parameters)     
    # response = model.generate_content(prompt, generation_config=parameters, safety_settings=safety_settings)   
    chat.send_message(prompt, generation_config=parameters, safety_settings=safety_settings)    
    response = chat.history[-1].parts[0]
    print(f"Response from Model: {response.text}")                              
    return response.text 

if __name__ == "__main__":
    print("Starting bot...")
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, get_user_response))

    # Errors
    app.add_error_handler(error)

    # Polls the bot
    print("Polling...")
    app.run_polling(poll_interval=3)
