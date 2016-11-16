# coding: utf-8
import logging
import os

from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

application = Flask(__name__)
application.config.from_object('config')
application.secret_key = 'CodeFireUA'

if not application.config.get('DEBUG', False):
    if not os.path.exists(application.config.get('LOG_REPO')):
        try:
            os.mkdir(application.config.get('LOG_REPO'))
        except:
            print 'Can\'t make path: {path}'.format(path=application.config.get('LOG_REPO'))

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s: [%(levelname)s] : %(message)s',
        filename=application.config.get('LOG_PATH'),
        filemode='wa'
    )

if not os.path.exists(application.config.get('WEB_UPLOAD_DIR')):
    try:
        os.mkdir(application.config.get('WEB_UPLOAD_DIR'))
    except:
        print 'Can\'t make path: {path}'.format(path=application.config.get('WEB_UPLOAD_DIR'))

db = SQLAlchemy(application)
lm = LoginManager(application)
mail = Mail(application)

from app import context, views, views_actions, authorization, views_group_actions, views_student_actions, \
    views_account_actions, views_profile_actions
from app import profile
