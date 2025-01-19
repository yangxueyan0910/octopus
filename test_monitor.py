import os
import sys

BASE_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))




if __name__ == '__main__':

    from utils.monitor_person import MonitorPerson
    thread = MonitorPerson(BASE_DIR)
    thread.start()
