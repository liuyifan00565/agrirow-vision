import logging
import os
import time

from service import time_service as current_time


# -----日志管理-----
def set_log(text_browser):
    class Handler(logging.Handler):
        def __init__(self, text_browser):
            super().__init__()
            self.text_browser = text_browser

        def emit(self, record):
            log_message = self.format(record)

            self.text_browser.append(log_message)

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s]%(message)s')
    handler = Handler(text_browser)
    logging.getLogger().addHandler(handler)


def info_msg(msg, status=0):
    if status == 0:
        logging.info(msg)
        log_folder('run', msg)
    else:
        logging.warning(msg)
        log_folder('error', msg)


# --------日志管理end---------

def log_folder(folder, msg):
    # 可拓展直接遍历两个文件夹
    #  folder in ['run', 'error']:
    if not os.path.exists(f'res/logs/{folder}'):
        os.makedirs(f'res/logs/{folder}')

    # 运行日志文件夹
    date_str = time.strftime('%Y-%m-%d', time.localtime())
    if not os.path.exists(f'res/logs/{folder}/{date_str}'):
        os.makedirs(f'res/logs/{folder}/{date_str}')

    # 运行日志文件
    global write_file_path
    write_file_path = f'res/logs/{folder}/{date_str}/{date_str}_{time.strftime("%H-%M-%S", time.localtime())}.txt'
    with open(write_file_path, 'a', encoding='utf-8') as f:
        # f.writelines("运行时间:")
        f.writelines(str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())) + msg)
        f.writelines("\r\r")

    # 存位置的run.txt和error.txt
    log_file_add = f'res/logs/{folder}/run.txt' if folder == 'run' else f'res/logs/{folder}/error.txt'
    with open(log_file_add, 'a') as f:
        # 文件为空第一行直接写，不为空加个换行
        if (os.path.getsize(log_file_add) == 0):
            log_run_add = write_file_path
            f.write(log_run_add)
        else:
            log_run_add = "\n" + write_file_path  # '\n'第一次用\n时会导致run.txt第一行空缺
            f.write(log_run_add)
