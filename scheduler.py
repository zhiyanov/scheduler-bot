import time
import telegram
import pandas as pd
import asyncio
import warnings

from utils import *
from datetime import datetime

from TOKEN import TOKEN

 
warnings.filterwarnings("ignore")

async def send(bot, cids, texts):
    messages = []
    for cid, text in zip(cids, texts):
        messages.append(
            bot.send_message(
                chat_id=cid, text=text
            )
        )
    await asyncio.gather(*messages)

bot = telegram.Bot(token=TOKEN)
while True:
    now = datetime.now()
    wd = now.weekday()
    day = ORDER_DAY[wd]
    hour, minute = map(int, str(now.time()).split(":")[:2])
    hour += 3
    
    SCH_DB, STU_DB, ASS_DB = read_db()
    
    distance = (SCH_DB["hour"] - hour) * 60 + (SCH_DB["minute"] - minute)
    condition = (SCH_DB["booked"] == 1) & \
        (SCH_DB["day"] == day) & \
        (distance == 15)
    result_db = SCH_DB.loc[condition]
    
    if len(result_db):
        append = SCH_DB.loc[condition]
        append["log"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        archive = pd.read_csv("./data/archive.csv", sep=",")
        archive = archive.append(append, ignore_index=True)
        archive.to_csv("./data/archive.csv", sep=",", index=None)
    
    cids, texts = [], []
    for i, slot in result_db.iterrows():
        assistant = slot["assistant"]
        assistant_id = ASS_DB.loc[ASS_DB["username"] == assistant, "id"].values[0]
        student = slot["student"]
        student_id = STU_DB.loc[STU_DB["username"] == student, "id"].values[0]
        
        stime = format_minute(f"{slot['hour']}:{slot['minute']}, ")[:-2]
        text = f"сегодня в {stime} у вас назначена встреча с "
        if (len(STU_DB.loc[STU_DB["username"] == student]) > 0) and (student_id):
            cids.append(student_id)
            texts.append(text + f"@{slot['assistant']}")
            print(text + f"@{slot['assistant']}")

        if (len(ASS_DB.loc[ASS_DB["username"] == assistant]) > 0) and (assistant_id):
            cids.append(assistant_id)
            texts.append(text + f"@{slot['student']}")
            print(text + f"@{slot['student']}")

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(send(bot, cids, texts))
    except:
        loop.close()

    time.sleep(50)
