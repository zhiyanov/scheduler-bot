import time
import datetime
import telegram
import pandas as pd
import asyncio

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
    now = datetime.datetime.now()
    wd = now.weekday()
    day = ORDER_DAY[wd]
    hour, minute = map(int, str(now.time()).split(":")[:2])
    hour += 3
    
    SCH_DB = pd.read_csv("./data/schedule.csv")
    STU_DB = pd.read_csv("./data/students.csv")
    ASS_DB = pd.read_csv("./data/assistants.csv")
    
    distance = (SCH_DB["hour"] - hour) * 60 + (SCH_DB["minute"] - minute)
    condition = (SCH_DB["booked"] == 1) & \
        (SCH_DB["day"] == day) & \
        ((distance == 5) | (distance == 10))

    result_db = SCH_DB.loc[condition]
    for i, slot in result_db.iterrows():
        assistant = slot["assistant"]
        assistant_id = str(int(ASS_DB.loc[ASS_DB["username"] == assistant]["id"]))
        student = slot["student"]
        student_id = str(int(STU_DB.loc[STU_DB["username"] == student]["id"]))
        
        text = f"сегодня в {slot['hour']}:{slot['minute']} у вас назначена встреча с "
        if len(ASS_DB.loc[ASS_DB["username"] == assistant]) > 0:
            print(text + f"@{slot['student']}")
            print(assistant_id)
            asyncio.run(send(bot, assistant_id, text + f"@{slot['student']}"))

        if len(STU_DB.loc[STU_DB["username"] == student]) > 0:
            print(text + f"@{slot['student']}")
            print(student_id)
            # asyncio.run(send(bot, student_id, text + f"@{slot['assistant']}"))
    
    time.sleep(30)




