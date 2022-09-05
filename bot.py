#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""Simple inline keyboard bot with multiple CallbackQueryHandlers.

This Bot uses the Application class to handle the bot.
First, a few callback functions are defined as callback query handler. Then, those functions are
passed to the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot that uses inline keyboard that has multiple CallbackQueryHandlers arranged in a
ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line to stop the bot.
"""
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

import pandas as pd
from TOKEN import TOKEN

# States
ROUTE = 0

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    # Get user that sent /start and log his name
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    # Build InlineKeyboard where each button has a displayed text
    # and a string as callback_data
    # The keyboard is a list of button rows, where each row is in turn
    # a list (hence `[[...]]`).
    keyboard = [
        [InlineKeyboardButton("расписание", callback_data="SCHEDULE"),
        InlineKeyboardButton("бронирование", callback_data="BOOK"),
        InlineKeyboardButton("освобождение", callback_data="CLEAR")]
        
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    await update.message.reply_text("что будем делать, начальник?", reply_markup=reply_markup)
    # Tell ConversationHandler that we're in state `FIRST` now
    return ROUTE


async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons"""
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("свободен", callback_data="SCHEDULE_FREE"),
        InlineKeyboardButton("занят", callback_data="SCHEDULE_BOOKED")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="какие слоты вас интересуют?", reply_markup=reply_markup
    )
    return ROUTE


async def schedule_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB = pd.read_csv("./data/schedule.csv")
    STU_DB = pd.read_csv("./data/students.csv")
    ASS_DB = pd.read_csv("./data/assistants.csv") 

    query = update.callback_query
    query_type = query["data"].lstrip("SCHEDULE_")
    if query_type == "FREE":
        booked = 0
    else:
        booked = 1
    
    username = query["message"]["chat"]["username"]
    if username in set(ASS_DB["username"]):
        user = "assistant"
        other = "student"
    else:
        user = "student"
        other = "assistant"

    condition = (SCH_DB["booked"] == booked)
    if booked:
        condition = condition & \
            (SCH_DB[f"{user}"] == username)
    response_db = SCH_DB.loc[condition]

    response_db["time"] = response_db["hour"].astype("str") + ":" + response_db["minute"].astype("str")
    response_db = response_db.sort_values(by=[
        "order",
        "hour",
        "minute"
    ])[[
        "day",
        "time",
        f"{other}"
    ]].drop_duplicates()
    response_db[f"{other}"] = "@" + response_db[f"{other}"]

    if not booked:
        response_db = response_db[[
            "day",
            "time"
        ]].drop_duplicates()
    
    response = ""
    columns = response_db.columns
    for i, row in response_db.iterrows():
        for column in columns:
            response += str(row[column]) + ", "
        response = response[:-2] + "\n"
    if response == "":
       response = "ничего не найдено"

    await query.edit_message_text(
        text=response
    )
    return ROUTE


async def book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB = pd.read_csv("./data/schedule.csv")
    STU_DB = pd.read_csv("./data/students.csv")
    ASS_DB = pd.read_csv("./data/assistants.csv") 
    
    query = update.callback_query

    condition = (SCH_DB["booked"] == 0)
    response_db = SCH_DB.loc[condition]
    if not len(response_db):
        await query.edit_message_text(
            text="все слоты заняты"
        )
        return ROUTE
    
    response_db["time"] = response_db["hour"].astype("str") + ":" + response_db["minute"].astype("str")
    response_db = response_db.sort_values(by=[
        "order",
        "hour",
        "minute"
    ])[[
        "day",
        "time",
    ]].drop_duplicates()
    
    columns = response_db.columns.to_list()
    keyboard = []
    for i, row in response_db.iterrows():
        text = ""
        for column in columns:
           text += row[column] + ", "
        text = text[:-2]
        keyboard.append( 
            [InlineKeyboardButton(text, callback_data="BOOK_" + text)],
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="cписок свободных слотов", reply_markup=reply_markup
    )
    # Transfer to conversation state `SECOND`
    return ROUTE

async def book_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB = pd.read_csv("./data/schedule.csv")
    STU_DB = pd.read_csv("./data/students.csv")
    ASS_DB = pd.read_csv("./data/assistants.csv") 

    query = update.callback_query
    username = query["message"]["chat"]["username"]
    if not (username in set(STU_DB["username"])):
        await query.edit_message_text(
            text="вы не найдены в базе студентов"
        )
        return ROUTE

    day, time = query["data"].lstrip("BOOK_").split(", ")
    hour, minute = map(int(), time.split(":"))

    condition = (SCH_DB["booked"] == 0) & \
        (SCH_DB["day"] == day) & \
        (SCH_DB["hour"] == hour) & \
        (SCH_DB["minute"] == minute)

    if not len(SCH_DB.loc[condition]):
        await query.edit_message_text(
            text="этот слот уже успели забронировать"
        )
        return ROUTE

    condition = condition.idxmax() if condition.any() else np.repeat(False, len(SCH_DB))

    SCH_DB.loc[condition, "student"] = username
    SCH_DB.loc[condition, "booked"] = 1
    SCH_DB.to_csv("./data/schedule.csv", sep=",", index=None)

    response = f'cлот забронирован, за 5 минут до сдачи можно написать @{SCH_DB.loc[condition]["assistant"]}'
    await query.edit_message_text(
        text=response
    )
    return ROUTE

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Nah, I've had enough ...", callback_data="CLEAR_1,18,15")],
        [InlineKeyboardButton("Nah, I've had enough ...", callback_data="CLEAR_1,18,30")],
        [InlineKeyboardButton("Nah, I've had enough ...", callback_data="CLEAR_1,18,45")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="cписок занятых слотов", reply_markup=reply_markup
    )
    # Transfer to conversation state `SECOND`
    return ROUTE

async def clear_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""
    query = update.callback_query
    print("QUERY", query)
    print("CONTEXT", context)
    await query.edit_message_text(
        text="слот освобожден"
    )
    # Transfer to conversation state `SECOND`
    return ROUTE

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Setup conversation handler with the states FIRST and SECOND
    # Use the pattern parameter to pass CallbackQueries with specific
    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROUTE: [
                CallbackQueryHandler(schedule, pattern="^" + "SCHEDULE" + "$"),
                CallbackQueryHandler(schedule_slot, pattern="SCHEDULE_"),
                CallbackQueryHandler(book, pattern="^" + "BOOK" + "$"),
                CallbackQueryHandler(book_slot, pattern="BOOK_*"),
                CallbackQueryHandler(book, pattern="^" + "CLEAR" + "$"),
                CallbackQueryHandler(book_slot, pattern="CLEAR_*")
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Add ConversationHandler to application that will be used for handling updates
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
