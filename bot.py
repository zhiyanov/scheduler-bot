import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

import re
import pandas as pd
from datetime import datetime

import warnings

from TOKEN import TOKEN
from ADMIN import ADMIN
from utils import *

DESCRIPTION = \
'''Как пользоваться этим ботом:
/start -- описание этого бота;
/menu -- основная команда для студентов, вызывает меню.

Остaльные команды предназначены для ассистентов:
/create понедельник 18:15 --  создает временой слот в понедельник в 18 часов 15 минут;
/create понедельник 18:15 19:20 13 --  создает набор временых слотов в понедельник, начиная с 18 часов 15 минут до 19 часов 20 минут, с шагом в 13 минут;
/free понедельник 18:15 -- удаляет временной слот в понедельник в 18 часов 15 минут;
/free понедельник 18:15 19:20 -- удаляет временные слоты в понедельник, начиная с 18 часов 15 минут до 19 часов 20 минут;
Дни недели, часы, минуты и временные интервалы являются аргументами, их можно менять.

За 15 минут до забронированного слота студенту и ассистенту придет напоминание о запланированной встрече.

В 23:50 текущего вечера происходит отмена бронирования слотов текущего дня.
'''

# States
ROUTE = 0


warnings.filterwarnings("ignore")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


SCH_DB = pd.read_csv("./data/schedule.csv")
STU_DB = pd.read_csv("./data/students.csv", dtype={
    "username": "str",
    "id": "str"
})
ASS_DB = pd.read_csv("./data/assistants.csv", dtype={
    "username": "str",
    "id": "str"
})

async def read(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()

    user = update.message.from_user
    username = user.username

    if not (username == ADMIN):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="вас нет в базе")
        return ROUTE
    
    
    SCH_DB, STU_DB, ASS_DB = read_db()
    response = "данные сохранены"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return ROUTE

async def dump(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    username = user.username

    if not (username == ADMIN):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="вас нет в базе")
        return ROUTE
    
    write_db(SCH_DB, STU_DB, ASS_DB)
    response = "данные сохранены"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return ROUTE

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()

    user = update.message.from_user
    username = user.username

    if not ((username in set(ASS_DB["username"])) or (username in set(STU_DB["username"]))):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="вас нет в базе")
        return ROUTE

    chat_id = str(int(update.message.chat.id))

    if username in set(STU_DB["username"]):
        STU_DB.loc[STU_DB["username"] == username, "id"] = chat_id
    if username in set(ASS_DB["username"]):
        ASS_DB.loc[ASS_DB["username"] == username, "id"] = chat_id
    
    response = DESCRIPTION
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return ROUTE

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()
    
    user = update.message.from_user
    username = user.username

    if not ((username in set(ASS_DB["username"])) or (username in set(STU_DB["username"]))):
        await query.edit_message_text(
            text="вac нет в базе"
        )
        return ROUTE

    chat_id = str(int(update.message.chat.id))

    if username in set(STU_DB["username"]):
        STU_DB.loc[STU_DB["username"] == username, "id"] = chat_id
    if username in set(ASS_DB["username"]):
        ASS_DB.loc[ASS_DB["username"] == username, "id"] = chat_id

    keyboard = [
        [InlineKeyboardButton("расписание", callback_data="SCHEDULE")],
        [InlineKeyboardButton("забронировать слот", callback_data="BOOK")],
        [InlineKeyboardButton("освободить слот", callback_data="CLEAR")]        
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
        [InlineKeyboardButton("свобдные", callback_data="SCHEDULE_FREE"),
        InlineKeyboardButton("занятые", callback_data="SCHEDULE_BOOKED")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="какие слоты вас интересуют?",
        reply_markup=reply_markup
    )
    return ROUTE

async def schedule_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()

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
        response = format_minute(response)
        response = response[:-2] + "\n"
    if response == "":
       response = "ничего не найдено\n"
    response = response[:-1]

    await query.edit_message_text(
        text=response
    )
    return ROUTE

async def book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()
    
    query = update.callback_query
    
    username = query["message"]["chat"]["username"]
    if username not in set(STU_DB["username"]):
        await query.edit_message_text(
            text="вac нет в базе студентов"
        )
        return ROUTE
    
    condition = (SCH_DB["booked"] == 1) & (SCH_DB["student"] == username)
    if len(SCH_DB.loc[condition]) > 0:
        await query.edit_message_text(
            text="у вас уже есть забронированный слот"
        )
        return ROUTE

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
        context = str(text[:-2])
        text = format_minute(text)
        text = text[:-2]
        
        keyboard.append( 
            [InlineKeyboardButton(text, callback_data="BOOK_" + context)],
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="cписок свободных слотов",
        reply_markup=reply_markup
    )
    return ROUTE

async def book_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()

    query = update.callback_query

    username = query["message"]["chat"]["username"]
    if not (username in set(STU_DB["username"])):
        await query.edit_message_text(
            text="вас нет в базе студентов"
        )
        return ROUTE
    
    condition = (SCH_DB["booked"] == 1) & (SCH_DB["student"] == username)
    if len(SCH_DB.loc[condition]) > 0:
        await query.edit_message_text(
            text="у вас уже есть забронированный слот"
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

    time = str(SCH_DB.loc[condition, "day"].values[0]) + \
        ", " + str(SCH_DB.loc[condition, "hour"].values[0]) + \
        ":" + str(SCH_DB.loc[condition, "minute"].values[0]) + ", " 
    time = format_minute(time)
    time = time[:-2]
    
    SCH_DB.loc[condition, "student"] = username
    SCH_DB.loc[condition, "booked"] = 1
    
    write_db(SCH_DB, STU_DB, ASS_DB)
    response = f'cлот [{time}] забронирован'
    await query.edit_message_text(
        text=response
    )
    return ROUTE

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()
    
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
        context = str(text[:-2])
        text = format_minute(text)
        text = text[:-2]
        
        keyboard.append( 
            [InlineKeyboardButton(text, callback_data="CLEAR_" + context)],
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="cписок занятых слотов", reply_markup=reply_markup
    )
    return ROUTE

async def clear_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()

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
    
    time = str(SCH_DB.loc[condition, "day"].values[0]) + \
        ", " + str(SCH_DB.loc[condition, "hour"].values[0]) + \
        ":" + str(SCH_DB.loc[condition, "minute"].values[0]) + ", "
    time = format_minute(time)
    time = time[:-2]
    
    SCH_DB.loc[condition, "student"] = None
    SCH_DB.loc[condition, "booked"] = 0

    write_db(SCH_DB, STU_DB, ASS_DB)
    response = f'cлот [{time}] освобожден, об этом можно написать @{othername}'
    await query.edit_message_text(
        text=response
    )
    return ROUTE

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()

    username = update.message.chat.username

    info = re.split(" |\:", update.message.text)[1:]
    info = [item.lower() for item in info]
    if not create_checker(info):
        response = "неверный формат команды"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return ROUTE

    if not (username in set(ASS_DB["username"])):
        response = "у вас нет доступа к этой команде"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return ROUTE

    day = info[0]
    start_hour, start_minute = format_time(int(info[1]), int(info[2]))

    slots = [(start_hour, start_minute)]
    if (len(info) == 6):
        end_hour, end_minute = format_time(int(info[3]), int(info[4]))
        _, duration = format_time(0, int(info[5]))
        duration = min(15, duration)

        start_minute += duration
        while (end_hour - start_hour) * 60 + end_minute - start_minute >= 0:
            if (start_minute >= 60):
                start_hour += start_minute // 60
                start_minute = start_minute % 60

            slots.append((start_hour, start_minute))
            start_minute += duration

    result = pd.DataFrame(SCH_DB)
    for slot in slots:
        append = pd.DataFrame(
            data = {
                "day": [day],
                "order": [DAY_ORDER[day]],
                "hour": [slot[0]],
                "minute": [slot[1]],
                "assistant": [username],
                "student": [None],
                "booked": [0]
            }, columns = [
                "day", "order",
                "hour", "minute",
                "assistant", "student",
                "booked"
            ]
        )
        result = pd.concat([result, append], axis=0)

    SCH_DB = result

    write_db(SCH_DB, STU_DB, ASS_DB)
    response = f'cлот(ы) созданы(ы)'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return ROUTE

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    SCH_DB, STU_DB, ASS_DB = read_db()

    username = update.message.chat.username

    info = re.split(" |\:", update.message.text)[1:]
    info = [item.lower() for item in info]
    if not free_checker(info):
        response = "неверный формат запроса"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return ROUTE

    if not (username in set(ASS_DB["username"])):
        response = "вас нет в базе ассистентов"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return ROUTE

    day = info[0]
    start_hour, start_minute = format_time(int(info[1]), int(info[2]))

    if (len(info) != 5):
        end_hour, end_minute = start_hour, end_minute
    else:
        end_hour, end_minute = format_time(int(info[3]), int(info[4]))

    condition = (SCH_DB["day"] == day) & (SCH_DB["assistant"] == username) & \
        (SCH_DB["hour"] * 60 + SCH_DB["minute"] >= start_hour * 60 + start_minute) & \
        (SCH_DB["hour"] * 60 + SCH_DB["minute"] <= end_hour * 60 + end_minute)

    SCH_DB = SCH_DB.loc[~condition]

    write_db(SCH_DB, STU_DB, ASS_DB)
    response = f'cлот(ы) удален(ы)'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return ROUTE

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("menu", menu)],
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
        fallbacks=[CommandHandler("menu", menu)],
    )
    application.add_handler(conv_handler)

    start_handler = CommandHandler("start", start)
    create_handler = CommandHandler("create", create)
    free_handler = CommandHandler("free", free)
    dump_handler = CommandHandler("dump", dump)
    read_handler = CommandHandler("read", read)
    application.add_handler(start_handler)
    application.add_handler(create_handler)
    application.add_handler(free_handler)
    application.add_handler(dump_handler)
    application.add_handler(read_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
