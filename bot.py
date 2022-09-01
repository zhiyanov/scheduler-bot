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
/book aнтон жиянов понедельник 18 15 -- бронирует слот для сдачи дз
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
    return

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
        response = response[:-1] + "\n"
    
    if response == "":
        if booked:
            response = "Все Ваши слоты свободны"
        else:
            response = "Все Ваши слоты заняты"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return

def book_checker(info):
    if len(info) != 5:
        return False
    
    name = info[0]
    surname = info[1]
    day = info[2]
    hour = info[3]
    minute = info[4]
    
    for i in range(3, len(info)):
        if not info[i].isnumeric():
            return False

    if not day in DAY_ORDER:
        return False

    return True

async def book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.chat.username
    
    info = update.message.text.split(" ")[1:]
    info = [item.lower() for item in info]
    if not book_checker(info)
        response = '''Неверный формат запроса\n'''
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return

    name = info[0]
    surname = info[1]
    day = info[2]
    hour = int(info[3])
    minute = int(info[4])

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
        response = f'Слот {day} {hour} {minute} отсутвует'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return 

    condition = condition.idxmax() if condition.any() else np.repeat(False, len(SCH_DB))

    SCH_DB.loc[condition, "students_name"] = name
    SCH_DB.loc[condition, "students_surname"] = surname
    SCH_DB.loc[condition, "students_username"] = username
    SCH_DB.loc[condition, "booked"] = 1
    SCH_DB.to_csv("./data/schedule.csv", sep=",", index=None)
    
    response = f'Слот забронирован, за 5 минут до сдачи можно написать @{SCH_DB.loc[condition]["assistants_username"]}'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return

def format_time(hour, minute):
    hour = min(int(hour), 23)
    minute = min(int(minute), 59)

    hour = max(hour, 0)
    minute = max(minute, 0)

    return hour, minute

def create_checker(info):
    if (len(info) != 3) and (len(info) != 6):
        return False

    day = info[0]
    if not day in DAY_ORDER:
        return False
    
    for i in range(1, len(info)):
        if not info[i].isnumeric():
            return False

    return True

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.chat.username

    info = update.message.text.split(" ")[1:]
    info = [item.lower() for item in info]
    if not create_checker(info):
        response = "Неверный формат запроса"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return
 
    if not (username in set(ASS_DB["username"])):
        response = "У Вас нет доступа к этой команде"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return

    name = ASS_DB.loc[ASS_DB["username"] == username]["name"]
    surname = ASS_DB.loc[ASS_DB["username"] == username]["surname"]
    
    day = info[0]
    start_hour, start_minute = format_time(int(info[1]), int(info[2]))
    
    slots = [(start_hour, start_minute)]
    if (len(info) == 6):
        end_hour, end_minute = format_time(int(info[3]), int(info[4]))
        _, duration = format_time(0, int(info[5]))
        
        start_minute += duration
        while (end_hour - start_hour) * 60 + end_minute - start_minute > 0:
            if (start_minute >= 60):
                start_hour += start_minute // 60
                start_minute = start_minute % 60

            slots.append((start_hour, start_minute))

    for slot in slots:
        append = pd.DataFrame(
            [
                day, DAY_ORDER[day],
                slot[0], slot[1],
                name, surname, username,
                None, None, None,
                0
            ],
            columns=[
                "day_name", "day_order",
                "hour", "minute", 
                "assistants_name", "assistants_surname", "assistants_username",
                "students_name", "students_surname", "students_username",
                "booked"
            ]
        )

        SCH_DB = pd.concat([SCH_DB, append], axis=0)
    SCH_DB.to_csv("./data/schedule.csv", sep=",", index=None)

    response = f'Слот(ы) забронирован(ы)'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return

def clear_checker(info):
    if (len(info) != 3) and (len(info) != 5):
        return False

    day = info[0]
    if not day in DAY_ORDER:
        return False
    
    for i in range(1, len(info)):
        if not info[i].isnumeric():
            return False

    return True

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.chat.username

    info = update.message.text.split(" ")[1:]
    info = [item.lower() for item in info]
    if not clear_checker(info):
        response = "Неверный формат запроса"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return

    if not (username in set(ASS_DB["username"])):
        response = "У Вас нет доступа к этой команде"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return

    name = ASS_DB.loc[ASS_DB["username"] == username]["name"]
    surname = ASS_DB.loc[ASS_DB["username"] == username]["surname"]
    
    day = info[0]
    start_hour, start_minute = format_time(int(info[1]), int(info[2]))
 
    if (len(info) != 5):
        end_hour, end_minute = start_hour, end_minute
    else:
        end_hour, end_minute = format_time(int(info[3]), int(info[4]))

    condition = (SCH_DB["day_name"] == day) & (SCH_DB["username"] == username) & \
            (SCH_DB["hour"] * 60 + SCH_DB["minute"] >= start_hour * 60 + start_minute) & \
            (SCH_DB["hour"] * 60 + SCH_DB["minute"] <= end_hour * 60 + end_minute)
    
    SCH_DB.loc[condition, "booked"] = 0
    SCH_DB.loc[condition, "students_name"] = None
    SCH_DB.loc[condition, "students_surname"] = None
    SCH_DB.loc[condition, "students_username"] = None
    SCH_DB.to_csv("./data/schedule.csv", sep=",", index=None)

    response = f'Слот(ы) освобожден(ы)'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.chat.username

    info = update.message.text.split(" ")[1:]
    info = [item.lower() for item in info]
    if not clear_checker(info):
        response = "Неверный формат запроса"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return

    if not (username in set(ASS_DB["username"])):
        response = "У Вас нет доступа к этой команде"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        return

    name = ASS_DB.loc[ASS_DB["username"] == username]["name"]
    surname = ASS_DB.loc[ASS_DB["username"] == username]["surname"]
    
    day = info[0]
    start_hour, start_minute = format_time(int(info[1]), int(info[2]))
 
    if (len(info) != 5):
        end_hour, end_minute = start_hour, end_minute
    else:
        end_hour, end_minute = format_time(int(info[3]), int(info[4]))

    condition = (SCH_DB["day_name"] == day) & (SCH_DB["username"] == username) & \
            (SCH_DB["hour"] * 60 + SCH_DB["minute"] >= start_hour * 60 + start_minute) & \
            (SCH_DB["hour"] * 60 + SCH_DB["minute"] <= end_hour * 60 + end_minute)

    
    SCH_DB = SCH_DB.loc[~condition]
    SCH_DB.to_csv("./data/schedule.csv", sep=",", index=None)

    response = f'Слот(ы) освобожден(ы)'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    return
    pass

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    schedule_handler = CommandHandler('schedule', schedule)
    book_handler = CommandHandler('book', book)

    application.add_handler(start_handler)
    application.add_handler(schedule_handler)
    application.add_handler(book_handler)
    
    application.run_polling()
