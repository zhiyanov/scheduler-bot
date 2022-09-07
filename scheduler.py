import time
import telegram
import pandas as pd
import asyncio

from datetime import datetime

from TOKEN import TOKEN
from utils import DAY_ORDER, ORDER_DAY

async def send(bot, cid, text):
    time.sleep(20)
    await bot.send_message(
        chat_id=cid,
        text=text
    )

bot = telegram.Bot(token=TOKEN)
while True:
    now = datetime.now()
    wd = now.weekday()
    day = ORDER_DAY[wd]
    hour, minute = map(int, str(now.time()).split(":")[:2])
    hour += 3
    
    SCH_DB = pd.read_csv("./data/schedule.csv")
    STU_DB = pd.read_csv("./data/students.csv", dtype={
        "username": "str",
        "id": "str"
    })
    ASS_DB = pd.read_csv("./data/assistants.csv", dtype={
        "username": "str",
        "id": "str"
    })
    
    distance = (SCH_DB["hour"] - hour) * 60 + (SCH_DB["minute"] - minute)
    condition = (SCH_DB["booked"] == 1) & \
        (SCH_DB["day"] == day) & \
        (distance == 15)
    result_db = SCH_DB.loc[condition]
    print(result_db)
    
    if len(result_db):
        append = SCH_DB.loc[condition]
        append["log"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        archive = pd.read_csv("./data/archive.csv", sep=",")
        archive = archive.append(append, ignore_index=True)
        archive.to_csv("./data/archive.csv", sep=",", index=None)

    for i, slot in result_db.iterrows():
        assistant = slot["assistant"]
        assistant_id = ASS_DB.loc[ASS_DB["username"] == assistant, "id"].values[0]
        student = slot["student"]
        student_id = STU_DB.loc[STU_DB["username"] == student, "id"].values[0]

        text = f"сегодня в {slot['hour']}:{slot['minute']} у вас назначена встреча с "
        if (len(ASS_DB.loc[ASS_DB["username"] == assistant]) > 0) and (assistant_id):
            asyncio.run(send(bot, assistant_id, text + f"@{slot['student']}"))
            print(assistant_id)

        if (len(STU_DB.loc[STU_DB["username"] == student]) > 0) and (student_id):
            asyncio.run(send(bot, student_id, text + f"@{slot['assistant']}"))
            print(student_id)
    
    time.sleep(50)
