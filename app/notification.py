# coding: utf-8
from datetime import datetime

from flask import session


def showNotify(title, text, type='primary', icon=None):
    '''Show notify pop-up by session.

    :param title: title of pop-up
    :param text: message in pop-up
    :param type: type of pop-up (info, success, warning, error)
    :param icon: icon of pop-up (font-awesome name without fa-)
    '''
    if not session.has_key('notify'):
        session['notify'] = []

    notify = {
        'title': '\"' + title + '\"',
        'text': '\"' + text + '\"'
    }

    if icon:
        notify.update({'icon': '\"fa fa-' + icon + '\"'})

    if type == 'primary':
        notify.update({
            'type': '\"custom\"',
            'addclass': '\"notification-primary\"'
        })
    elif type == 'dark':
        notify.update({
            'type': '\"custom\"',
            'addclass': '\"notification-dark\"'
        })
    else:
        notify.update({'type': '\"' + type + '\"'})

    session['notify'].append(notify)


def welcome():
    notice = {
        'style': 'info' if 5 <= datetime.now().hour <= 18 else 'dark',
        'icon': 'sun-o' if 5 <= datetime.now().hour <= 18 else 'moon-o'
    }

    message = ''

    if 5 <= datetime.now().hour < 12:
        notice.update({
            'title': 'Доброе утро!',
            'text': 'Хорошего дня!'
        })
    elif 12 <= datetime.now().hour < 17:
        notice.update({
            'title': 'Добрый день!',
            'text': 'Хорошего дня!'
        })
    elif 16 <= datetime.now().hour < 23:
        notice.update({
            'title': 'Добрый вечер!',
            'text': 'Утро вечера мудреней...'
        })
    else:
        notice.update({
            'title': 'Добрый ночи!',
            'text': 'Ложитесь спать ;)'
        })

    showNotify(notice['title'], notice['text'], type=notice['style'], icon=notice['icon'])


def goodbye():
    style = 'info' if 9 <= datetime.now().hour <= 18 else 'dark'
    icon = 'sun-o' if 9 <= datetime.now().hour <= 18 else 'moon-o'

    showNotify('До свидания!', 'До скорых встреч!', type=style, icon=icon)
