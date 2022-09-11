from datetime import datetime
import os

now = datetime.now()
appendix = now.strftime("%m_%d_%H_%M")
for fin in os.listdir("./data"):
    fon = fin.split(".")[0] + "_" + appendix + ".csv"
    fi = open(f"./data/{fin}", "r")
    fo = open(f"./archive/{fon}", "w")
    for line in fi:
        fo.write(line.rstrip("\n") + "\n")
    fi.close()
    fo.close()
