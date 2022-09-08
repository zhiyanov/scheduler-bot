import time
import datetime
import telegram
import pandas as pd
import asyncio

from TOKEN import TOKEN
from utils import *

CLEAN_HOUR = 23
CLEAN_MINUTE = 50


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
    
    SCH_DB, STU_DB, ASS_DB = read_db() 
    
    distance = (CLEAN_HOUR - hour) * 60 + (CLEAN_MINUTE - minute)
    if distance > 0:
        time.sleep(60)
        continue

    condition = (SCH_DB["booked"] == 1) & \
        (SCH_DB["day"] == day)
    
    SCH_DB.loc[condition, "student"] = None
    SCH_DB.loc[condition, "booked"] = 0
    write_db(SCH_DB, STU_DB, ASS_DB)
 
    time.sleep(60)
