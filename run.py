#!env/bin/python
import sys

import locale

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

reload(sys)

sys.setdefaultencoding('utf-8')

# RUN APPLICATION
from app import application

if __name__ == '__main__':
    print('Staring server at: http://127.0.0.1:5000/')
    application.run(threaded=True)
