# coding: utf-8
import json
import traceback

from flask import request
from flask_login import login_required

from app import application, db
from app.models import Account, Student, Group
from app.notification import showNotify
from app.authorization import get_service


@application.route('/accounts/<int:id>/student/add', methods=['POST'])
@login_required
def ajax_account_add_action(id):
    data = request.json

    try:
        account = Account.query.get(id)

        student = Student()
        student.name = data['name']
        student.phone = data['phone']
        student.group = Group.query.get(data['group_id'])

        account.student = student

        if student.group and student.group.event_id:
            service = get_service('calendar', 'v3')
            # student.group.trainer.accounts
            calendar_id = Account.query.filter_by(trainer=student.group.trainer,
                                                  main=True).first().email if student.group else 'primary'

            event = service.events().get(calendarId=calendar_id, eventId=student.group.event_id).execute()

            if 'attendees' not in event:
                event.update({'attendees': []})

            event['attendees'].append({'email': account.email})
            service.events().update(calendarId=calendar_id, eventId=student.group.event_id, body=event,
                                    sendNotifications=True).execute()

        db.session.commit()

        showNotify('Успешно!', 'Студент \"{}\" добавлен!'.format(account.student.name), type='success')
    except:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'Возникли проблемы при создании аккаунта {}.'.format(student.name)
        }])

    return json.dumps([{'exec': 'document.location.href = \'/students\''}])


@application.route('/accounts/<int:id>/student/bind', methods=['POST'])
@login_required
def ajax_account_bind_action(id):
    data = request.json

    try:
        account = Account.query.get(id)

        account.student = Student.query.get(data['student_id'])

        db.session.commit()

        showNotify('Успешно!', 'Студент \"{}\" добавлен!'.format(account.student.name), type='success')
    except:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'Возникли проблемы при создании аккаунта {}.'.format(account.email)
        }])

    return json.dumps([{'exec': 'document.location.href = \'/students\''}])
