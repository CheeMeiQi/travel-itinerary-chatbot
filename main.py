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
import vertexai                                           
from vertexai.language_models import TextGenerationModel 

TOKEN: Final = "6409677499:AAEv6YdJw_X8MCuIk0pHQpPYqKssui2p1Ww"
BOT_NAME: Final = "Travel Itinerary Chatbot"
BOT_USERNAME: Final = "@get_that_itinerary_bot"


# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Thanks for chatting with me! Should we plan a trip together?"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Type where you want to go and what you want to do. I can plan to plan your itinerary!"
    )


async def start_LLM_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["llm_active"] = True
    await update.message.reply_text(
        "This is to call the LLM model. Please type in what you want to ask the chatbot."
    )
    
# Helper function to get LLM state from context
def get_llm_state(context):
    return context.chat_data.get("llm_active", False)

# Responses
def handle_response(text: str, context) -> str:
    processed: str = text.lower()

    if get_llm_state(context):
        llm_response = generate(text)
        return llm_response
    else:
        if "hello" in processed:
            return "Hey there! Where would you like to go?"

    return "I do not understand what you wrote..."


# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text  

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if "group" in message_type:
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, "").strip()
            response: str = handle_response(new_text, context)
        else:
            return
    else:
        response: str = handle_response(text, context)

    print("Bot: ", response)
    await update.message.reply_text(response)


# Logging errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")


def generate(prompt: str) -> str:
     # Initialize Vertex AI access.
    vertexai.init(project="travelitinerarychatbot", location="us-central1")  
    parameters = {                                                 
        "candidate_count": 1,                                      
        "max_output_tokens": 1024,                                
        "temperature": 0.5,                                        
        "top_p": 0.8,                                              
        "top_k": 40,                                               
    }                                                             
    model = TextGenerationModel.from_pretrained("text-bison@002")  
    response = model.predict(prompt, **parameters)      
    print(f"Response from Model: {response.text}")                              
    return response.text 

if __name__ == "__main__":
    print("Starting bot...")
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("llm", start_LLM_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    # Polls the bot
    print("Polling...")
    app.run_polling(poll_interval=3)
