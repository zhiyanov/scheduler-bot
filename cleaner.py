import time
import datetime
import telegram
import pandas as pd
import asyncio

from TOKEN import TOKEN
from utils import DAY_ORDER, ORDER_DAY

CLEAN_HOUR = 22
CLEAN_MINUTE = 59


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
    
    distance = (CLEAN_HOUR - hour) * 60 + (CLEAN_MINUTE - minute)
    if distance > 0:
        time.sleep(3600)
        continue

    condition = (SCH_DB["booked"] == 1) & \
        (SCH_DB["day"] == day)
    
    SCH_DB.loc[condition, "student"] = None
    SCH_DB.loc[condition, "booked"] = 0
    SCH_DB.to_csv("./data/schedule.csv", sep=",", index=None)
    
    time.sleep(3600)
