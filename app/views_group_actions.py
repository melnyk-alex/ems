# coding: utf-8
import json
import traceback
from datetime import datetime, timedelta

from flask import request
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app import application, db
from app.models import Group, Account, Trainer
from app.notification import showNotify
from app.authorization import get_service


@application.route('/groups/add', methods=['POST'])
@login_required
def ajax_groups_add_action():
    data = request.json

    try:
        group = Group()
        group.name = data['name']
        group.begin = datetime.strptime(data['date'] + ' ' + data['time'], '%d.%m.%Y %H:%M')
        group.schedule = str.join(', ', data['weekdays'] if 'weekdays' in data else [])
        group.trainer_id = data['trainer_id'] if data['trainer_id'] else None

        db.session.add(group)
        db.session.commit()

        showNotify('Успешно!', 'Группа {} создана!'.format(group.name), type='success')
    except IntegrityError:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'Группа {} уже существует.'.format(group.name)
        }])
    except Exception:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'Невозможно создать группу {}.'.format(group.name)
        }])

    if group.trainer:
        calendarId = Account.query.filter_by().filter_by(main=True, trainer=group.trainer,
                                                         oauth_name='google-plus').first().email
    else:
        calendarId = 'primary'

    try:
        event_data = create_event(group.name, group.begin.strftime('%Y-%m-%dT%H:%M:00'),
                                  (group.begin + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:00'),
                                  group.schedule)

        # Create event if not exists.
        event = get_service('calendar', 'v3').events().insert(calendarId=calendarId, body=event_data).execute()
        group.event_id = event['id']
        db.session.commit()
    except Exception:
        traceback.print_exc()

    return json.dumps([{'exec': 'document.location.href = \'/groups\''}])


@application.route('/groups/<int:id>/edit', methods=['POST'])
@login_required
def ajax_groups_edit_action(id):
    data = request.json

    try:
        group = Group.query.get(id)

        group.name = data['name']
        group.begin = datetime.strptime(data['date'] + ' ' + data['time'], '%d.%m.%Y %H:%M')
        group.schedule = str.join(', ', data['weekdays']) if isinstance(data['weekdays'], list) else data['weekdays']
        group.complete = data['complete'] == 'on' if 'complete' in data else False

        service = get_service('calendar', 'v3')

        trainer = Trainer.query.get(data['trainer_id'])

        if group.trainer != trainer:
            trainerIdFrom = group.trainer_id
            calendarIdFrom = Account.query.filter_by(main=True, trainer_id=trainerIdFrom,
                                                     oauth_name='google-plus').one().email if trainerIdFrom else 'primary'

            trainerIdTo = data['trainer_id']
            calendarIdTo = Account.query.filter_by(main=True, trainer_id=trainerIdTo,
                                                   oauth_name='google-plus').one().email if trainerIdTo else 'primary'

            if group.event_id:
                service.events().move(calendarId=calendarIdFrom, eventId=group.event_id,
                                      destination=calendarIdTo).execute()

        group.trainer_id = data['trainer_id'] or None
        db.session.commit()

        calendar_id = group.trainer.accounts.filter_by(main=True, trainer_id=group.trainer_id,
                                                       oauth_name='google-plus').one().email if group.trainer_id else 'primary'

        if group.event_id and group.complete:
            end_date = (datetime.strptime(data['complete_date'], '%d.%m.%Y') + timedelta(days=1))

            event_data = create_event(group.name, group.begin.strftime('%Y-%m-%dT%H:%M:00'),
                                      (group.begin + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:00'), group.schedule,
                                      end_date.strftime('%Y%m%d'))

            # Update existing event.
            event = service.events().get(calendarId=calendar_id, eventId=group.event_id).execute()
            event.update(event_data)
            service.events().update(calendarId=calendar_id, eventId=group.event_id, body=event,
                                    sendNotifications=True).execute()
            # Delete event_id from group
        elif group.event_id:
            event_data = create_event(group.name, group.begin.strftime('%Y-%m-%dT%H:%M:00'),
                                      (group.begin + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:00'), group.schedule)

            # Update existing event.
            event = service.events().get(calendarId=calendar_id, eventId=group.event_id).execute()
            event.update(event_data)
            service.events().update(calendarId=calendar_id, eventId=group.event_id, body=event,
                                    sendNotifications=True).execute()
        elif not group.event_id:
            if not group.complete:
                event_data = create_event(group.name, group.begin.strftime('%Y-%m-%dT%H:%M:00'),
                                          (group.begin + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:00'),
                                          group.schedule)
            else:
                end_date = (datetime.strptime(data['complete_date'], '%d.%m.%Y') + timedelta(days=1))
                event_data = create_event(group.name, group.begin.strftime('%Y-%m-%dT%H:%M:00'),
                                          (group.begin + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:00'),
                                          group.schedule,
                                          end_date.strftime('%Y%m%d'))

            # list = [x for x in ['a', 'b', 'c', 'd', 'e', 'f'] if x not in ['c', 'e']]
            if len(group.students.all()) > 0:
                event_data.update({
                    'attendees': [{'email': acc.email} for student in group.students for acc in student.accounts if
                                  acc.main]
                })

            # Create event if not exists.
            event = service.events().insert(calendarId=calendar_id, body=event_data, sendNotifications=True).execute()
            # Save event_id into group
            group.event_id = event['id']
            db.session.commit()

        showNotify('Успешно!', 'Данные группы {} изменены!'.format(group.name), type='success')
    except Exception:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'На сервере возникли проблемы.'
        }])

    return json.dumps([{'exec': 'document.location.href = \'/groups\''}])


@application.route('/groups/<int:id>/delete', methods=['POST'])
@login_required
def ajax_groups_delete_action(id):
    try:
        group = Group.query.get(id)

        db.session.delete(group)
        db.session.commit()

        showNotify('Успешно!', 'Группа {} удалена!'.format(group.name), type='success')
    except Exception:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'При удалении группы возникли проблемы.'
        }])

    calendar_id = 'melnyk@codefire.com.ua'

    try:
        get_service('calendar', 'v3').events().delete(calendarId=calendar_id, eventId=group.event_id,
                                                      sendNotifications=True).execute()
    except Exception:
        traceback.print_exc()

    return json.dumps([{'exec': 'document.location.href = \'/groups\''}])


def create_event(title, time_from, time_to, days, until=None):
    event_data = {
        'summary': title,
        'start': {
            'dateTime': time_from,
            'timeZone': 'Europe/Kiev'
        },
        'end': {
            'dateTime': time_to,
            'timeZone': 'Europe/Kiev'
        },
        'recurrence': [
            'RRULE:FREQ=WEEKLY;BYDAY={};'.format(
                days.replace(' ', '')) if not until else 'RRULE:FREQ=WEEKLY;BYDAY={};UNTIL={}'.format(
                days.replace(' ', ''), until.replace(' ', ''))
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 60},
                {'method': 'popup', 'minutes': 60}
            ]
        }
    }

    return event_data
