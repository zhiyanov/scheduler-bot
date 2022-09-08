import pandas as pd


DAY_ORDER = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "четверг": 3,
    "пятница": 4,
    "суббота": 5,
    "воскресение": 6
}

ORDER_DAY = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресение"
}

def read_db():
    sch_db = pd.read_csv("./data/schedule.csv")
    stu_db = pd.read_csv("./data/students.csv", dtype={
        "username": "str",
        "id": "str"
    })
    ass_db = pd.read_csv("./data/assistants.csv", dtype={
        "username": "str",
        "id": "str"
    })
    return sch_db, stu_db, ass_db

def write_db(sch_db, stu_db, ass_db):
    stu_db.to_csv("./data/students.csv", sep=",", index=None)
    ass_db.to_csv("./data/assistants.csv", sep=",", index=None)
    sch_db.to_csv("./data/schedule.csv", sep=",", index=None)

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

def free_checker(info):
    if (len(info) != 3) and (len(info) != 5):
        return False

    day = info[0]
    if not day in DAY_ORDER:
        return False

    for i in range(1, len(info)):
        if not info[i].isnumeric():
            return False

    return True
