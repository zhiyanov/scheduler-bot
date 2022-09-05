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
    STU_DB = pd.read_csv("./data/students.csv")
    ASS_DB = pd.read_csv("./data/assistants.csv") 
    
    user = update.message.from_user
    username = user.username

    if not ((username in set(ASS_DB["username"])) or (username in set(STU_DB["username"]))):
        await query.edit_message_text(
            text="вac нет в базе"
        )
        return ROUTE

    chat_id = str(update.message.chat.id)

    if username in set(STU_DB["username"]):
        STU_DB.loc[STU_DB["username"] == username, "id"] = chat_id
        STU_DB.to_csv("./data/students.csv", sep=",", index=None)
    if username in set(ASS_DB["username"]):
        ASS_DB.loc[ASS_DB["username"] == username, "id"] = chat_id
        ASS_DB.to_csv("./data/assistants.csv", sep=",", index=None)

    keyboard = [
        [InlineKeyboardButton("расписание", callback_data="SCHEDULE"),
        InlineKeyboardButton("бронирование", callback_data="BOOK"),
        InlineKeyboardButton("освобождение", callback_data="CLEAR")]        
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "что будем делать?",
        reply_markup=reply_markup
    )
    return ROUTE

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("свободен", callback_data="SCHEDULE_FREE"),
        InlineKeyboardButton("занят", callback_data="SCHEDULE_BOOKED")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="какие слоты вас интересуют?",
        reply_markup=reply_markup
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
       response = "ничего не найдено\n"
    response = response[:-1]

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
        text="cписок свободных слотов",
        reply_markup=reply_markup
    )
    return ROUTE

async def book_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB = pd.read_csv("./data/schedule.csv")
    STU_DB = pd.read_csv("./data/students.csv")
    ASS_DB = pd.read_csv("./data/assistants.csv") 

    query = update.callback_query
    username = query["message"]["chat"]["username"]
    if not (username in set(STU_DB["username"])):
        await query.edit_message_text(
            text="вас нет в базе"
        )
        return ROUTE

    day, time = query["data"].lstrip("BOOK_").split(", ")
    hour, minute = map(int, time.split(":"))

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
    SCH_DB = pd.read_csv("./data/schedule.csv")
    STU_DB = pd.read_csv("./data/students.csv")
    ASS_DB = pd.read_csv("./data/assistants.csv") 
    
    query = update.callback_query 
    username = query["message"]["chat"]["username"]
    if username in set(ASS_DB["username"]):
        user = "assistant"
        other = "student" 
    elif username in set(STU_DB["username"]):
        user = "student"
        other = "assistant"
    else:
        await query.edit_message_text(
            text="вac нет в базе"
        )
        return ROUTE

    condition = (SCH_DB["booked"] == 1) & \
        (SCH_DB[user] == username)

    response_db = SCH_DB.loc[condition]
    if not len(response_db):
        await query.edit_message_text(
            text="у вас нет занятых слотов"
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
        f"{other}"
    ]].drop_duplicates()
    
    columns = response_db.columns.to_list()
    keyboard = []
    for i, row in response_db.iterrows():
        text = ""
        for column in columns:
           text += row[column] + ", "
        text = text[:-2]
        keyboard.append( 
            [InlineKeyboardButton(text, callback_data="CLEAR_" + text)],
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="cписок занятых слотов", reply_markup=reply_markup
    )
    return ROUTE

async def clear_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB = pd.read_csv("./data/schedule.csv")
    STU_DB = pd.read_csv("./data/students.csv")
    ASS_DB = pd.read_csv("./data/assistants.csv") 

    query = update.callback_query 
    username = query["message"]["chat"]["username"]
    if username in set(ASS_DB["username"]):
        user = "assistant"
        other = "student" 
    elif username in set(STU_DB["username"]):
        user = "student"
        other = "assistant"
    else:
        await query.edit_message_text(
            text="вac нет в базе"
        )
        return ROUTE

    day, time, othername = query["data"].lstrip("CLEAR_").split(", ")
    hour, minute = map(int, time.split(":"))

    condition = (SCH_DB["booked"] == 1) & \
        (SCH_DB["day"] == day) & \
        (SCH_DB["hour"] == hour) & \
        (SCH_DB["minute"] == minute) & \
        (SCH_DB[f"{other}"] == othername)

    if not len(SCH_DB.loc[condition]):
        await query.edit_message_text(
            text="этот слот уже успели освободить"
        )
        return ROUTE

    SCH_DB.loc[condition, "student"] = None
    SCH_DB.loc[condition, "booked"] = 0
    SCH_DB.to_csv("./data/schedule.csv", sep=",", index=None)

    response = f'cлот освобожден, об этом можно написать @{othername}'
    await query.edit_message_text(
        text=response
    )
    return ROUTE

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROUTE: [
                CallbackQueryHandler(schedule, pattern="^" + "SCHEDULE" + "$"),
                CallbackQueryHandler(schedule_slot, pattern="SCHEDULE_"),
                CallbackQueryHandler(book, pattern="^" + "BOOK" + "$"),
                CallbackQueryHandler(book_slot, pattern="BOOK_*"),
                CallbackQueryHandler(clear, pattern="^" + "CLEAR" + "$"),
                CallbackQueryHandler(clear_slot, pattern="CLEAR_*")
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
