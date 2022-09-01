import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

import pandas as pd
import numpy as np
import datetime

from TOKEN import TOKEN 


DESCRIPTION = '''
Этот бот предназначен для бронирования временных слотов.
Доступны следующие команды:
/schedule -- возвращает список доступных слотов
/book aнтон,жиянов,понедельник,18:15 -- бронирует слот для сдачи дз
'''

SCH_DB = pd.read_csv("./data/schedule.csv")
STU_DB = pd.read_csv("./data/students.csv")
ASS_DB = pd.read_csv("./data/assistants.csv")

DAY_ORDER = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "четверг": 3,
    "пятница": 4,
    "суббота": 5,
    "воскресение": 6
}


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=DESCRIPTION
    )

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time = datetime.datetime.today()
    hour = time.hour + 3
    minute = time.minute
    weekday = time.weekday()
    
    username = update.message.chat.username
    arg = update.message.text.split(" ")[-1]

    if arg == "free":
        booked = 0
    else:
        booked = 1

    if username in set(ASS_DB["username"]):
        assistant = 1
        condition = (SCH_DB["booked"] == booked) & \
                (SCH_DB["assistants_username"] == username)
    else:
        assistant = 0
        condition = (SCH_DB["booked"] == booked)
        
        if booked:
            condition = condition & \
                    (SCH_DB["students_username"] == username)
        else: 
            condition = condition & \
                    ((SCH_DB["day_order"] != weekday) | \
                    ((SCH_DB["hour"] - hour) * 60 + SCH_DB["minute"] -  minute > 120))

    response_db = SCH_DB.loc[condition]
    response_db = response_db.sort_values(by=[
        "day_order",
        "hour",
        "minute"
    ])
    
    if assistant:
        response_db = response_db[[
            "day_name",
            "hour",
            "minute",
            "students_name",
            "students_surname",
            "students_username"
        ]].drop_duplicates()
        response_db["students_username"] = "@" + response_db["students_username"]
    else:
        response_db = response_db[[
            "day_name",
            "hour",
            "minute",
            "assistants_name",
            "assistants_surname",
            "assistants_username"
        ]].drop_duplicates()
        response_db["assistants_username"] = "@" + response_db["assistants_username"]

    if not booked:
        response_db = response_db[[
            "day_name",
            "hour",
            "minute"
        ]].drop_duplicates()

    response = ""
    columns = response_db.columns
    for i, row in response_db.iterrows():
        for column in columns:
            response += str(row[column]) + " "
        response[-1] = "\n"
    
    if response == "":
        response = "Ваши слоты не заняты"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return

    time = datetime.datetime.today()
    hour = time.hour + 3
    minute = time.minute
    weekday = time.weekday()
    
    condition = (SCH_DB["booked"] == 0) & \
            ((SCH_DB["day_order"] != weekday) | \
            ((SCH_DB["hour"] - hour) * 60 + SCH_DB["minute"] -  minute > 120))
    response_db = SCH_DB.loc[condition]
    response_db = response_db.sort_values(by=[
        "day_order",
        "hour",
        "minute"
    ])

    response_db = response_db[[
        "day_name",
        "hour",
        "minute"
    ]].drop_duplicates()

    response = ""
    for i, row in response_db.iterrows():
        response += f'{row["day_name"]} {row["hour"]}:{row["minute"]}'
    
    if response == "":
        response = "Все слоты забронированы"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

async def book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.chat.username
    info = update.message.text.split(" ")[-1].split(",")
    if len(info) != 4:
        response = '''Недостаточно информации для бронирования\n'''
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return 

    info = [item.lower() for item in info]
    name = info[0]
    surname = info[1]
    day = info[2]
    hour, minute = [int(item) for item in info[3].split(":")]

    condition = (STU_DB["surname"] == surname) & \
            (STU_DB["name"] == name)
    if not len(STU_DB.loc[condition]):
        response = f'Студент {name},{surname} отсутсвует в базе'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return 

    condition = (SCH_DB["booked"] == 0) & \
            (SCH_DB["day_name"] == day) & \
            (SCH_DB["hour"] == hour) & \
            (SCH_DB["minute"] == minute)
    
    if not len(SCH_DB.loc[condition]):
        response = f'Слот {day},{hour}:{minute} отсутвует'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return 

    condition = condition.idxmax() if condition.any() else np.repeat(False, len(SCH_DB))

    SCH_DB.loc[condition, "students_name"] = name
    SCH_DB.loc[condition, "students_surname"] = surname
    SCH_DB.loc[condition, "students_username"] = username
    SCH_DB.loc[condition, "booked"] = 1
    
    response = f'Слот забронирован, за 5 минут до сдачи можно написать @{SCH_DB.loc[condition]["assistants_username"]}'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    schedule_handler = CommandHandler('schedule', schedule)
    book_handler = CommandHandler('book', book)

    application.add_handler(start_handler)
    application.add_handler(schedule_handler)
    application.add_handler(book_handler)
    
    application.run_polling()
