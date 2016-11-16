# coding: utf-8
import json
import traceback

from flask import request
from flask_login import login_required

from app import application, db
from app.models import Student, Group, Account
from app.notification import showNotify
from app.authorization import get_service


# @application.route('/students/add', methods=['POST'])
# @login_required
# def ajax_students_add_action():
#     data = request.json
#
#     try:
#         student = Student()
#         student.name = data['name']
#         student.phone = data['phone']
#         student.group = Group.query.get(data['group_id'])
#
#         if student.group:
#             service = get_service('calendar', 'v3')
#
#             calendar_id = Account.query.filter_by(trainer=student.group.trainer,
#                                                   main=True).first().email if student.group.trainer else 'primary'
#
#             # Get group event
#             event = service.events().get(calendarId=calendar_id, eventId=student.group.event_id).execute()
#
#             # Add student to group event
#             if 'attendees' not in event:
#                 event['attendees'] = []
#
#             event['attendees'].append({'email': main_email})
#
#             service.events().update(calendarId=calendar_id, eventId=student.group.event_id, body=event,
#                                     sendNotifications=True).execute()
#
#
#         db.session.add(student)
#         db.session.commit()
#
#         showNotify('Успешно!', 'Студент \"{}\" добавлен!'.format(student.name), type='success')
#     except:
#         traceback.print_exc()
#         return json.dumps([{
#             'status': 'danger',
#             'title': 'Внимание!',
#             'text': 'Возникли проблемы при создании студента {}.'.format(student.name)
#         }])
#
#     return json.dumps([{'exec': 'document.location.href = \'/students\''}])


@application.route('/students/<int:id>/edit', methods=['POST'])
@login_required
def ajax_students_edit_action(id):
    data = request.json

    try:
        student = Student.query.get(id)

        student.name = data['name']
        student.phone = data['phone']

        selected_group = Group.query.get(data['group_id'])

        if student.group != selected_group:
            main_email = Account.query.filter_by(student=student, main=True).first().email

            service = get_service('calendar', 'v3')

            # Remove from previous group
            if student.group and student.group.event_id:
                calendar_id = Account.query.filter_by(trainer=student.group.trainer,
                                                      main=True).first().email if student.group.trainer else 'primary'

                # Get group event
                event = service.events().get(calendarId=calendar_id, eventId=student.group.event_id).execute()

                # Remove student from group event
                if 'attendees' in event:
                    event['attendees'] = [acc for acc in event['attendees'] if acc['email'] != main_email]

                    service.events().update(calendarId=calendar_id, eventId=student.group.event_id, body=event,
                                            sendNotifications=True).execute()

            student.group = selected_group

            if student.group and student.group.event_id:
                calendar_id = Account.query.filter_by(trainer=student.group.trainer,
                                                      main=True).first().email if student.group.trainer else 'primary'

                # Get group event
                event = service.events().get(calendarId=calendar_id, eventId=student.group.event_id).execute()

                # Add student to group event
                if 'attendees' not in event:
                    event['attendees'] = []

                event['attendees'].append({'email': main_email})

                service.events().update(calendarId=calendar_id, eventId=student.group.event_id, body=event,
                                              sendNotifications=True).execute()

        db.session.commit()
    except:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'Возникли проблемы при изминении студента {}.'.format(student.name)
        }])

    return json.dumps([{'exec': 'document.location.href = \'/students\''}])


@application.route('/students/<int:id>/delete', methods=['POST'])
@login_required
def ajax_students_delete_action(id):
    try:
        student = Student.query.get(id)

        db.session.delete(student)
        db.session.commit()

        showNotify('Успешно!', 'Студент \"{}\" удален!'.format(student.name), type='success')
    except:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'Возникли проблемы при удалении студента {}.'.format(student.name)
        }])

    return json.dumps([{'exec': 'document.location.href = \'/students\''}])
