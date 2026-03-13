import math
import time

DATE = "%Y-%m-%d %H:%M:%S"
TIME = "%H:%M:%S"


# 获取当前时间
def current_time(time_stamp) -> str:
    date = time.strftime(DATE, time.localtime(time_stamp))
    return date


'''没啥用'''
