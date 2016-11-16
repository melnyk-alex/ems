# coding: utf-8
import json
import re
from datetime import datetime
from os import remove

from flask import session, redirect, request
from flask_login import login_required, current_user
from flask_mail import Message
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.functions import func

from app import application, db, mail
from app.functions import uploadFile, saveFile
from app.models import Account, Student, Trainer, Group, File, Test, Stat
from app.notification import showNotify
from models import History


@application.route('/home-task/send', methods=['POST'])
@login_required
# UPLOADING HOME-TASK
def uploadHomeTask():
    fileList = request.files.getlist('home_task')

    # MAKE MESSAGE
    message = Message('Домашняя работа от {}'.format(current_user.student.name))

    message.recipients = [application.config.get('MAIL_EDUCATION')]
    message.reply_to = message.sender = '{name} <{email}>'.format(name=current_user.student.name,
                                                                  email=current_user.email)

    if current_user.student.group:
        message.subject += ' {}'.format(current_user.student.group.name)

        if current_user.student.group.trainer:
            message.cc = [current_user.student.group.trainer.accounts.filter_by(main=True).first().email]

    comment = request.values.get('comment')
    message.html = '<h3>Комментарии:</h3>\n<p>{}</p>\n'.format(comment)

    uploaded = 0

    list_files = ''

    for f in fileList:
        if f.filename != '':
            uploaded += 1

            checksum = uploadFile(f, comment=comment)

            #     showNotify('Внимание!', 'Файл \\"{filename}\\" уже имеееться на сервере!'.format(filename=f.filename),
            #                type='warning')

            list_files += '<li><a href="{host}/files/{checksum}/{filename}">{filename}</a></li>'.format(
                host=application.config.get('HOSTNAME'), checksum=checksum, filename=f.filename)

            # ATTACH FILE TO E-MAIL
            # f.seek(0)
            # message.attach(f.filename, f.mimetype, f.read())

    if uploaded > 0:
        showNotify('Успешно!', 'Файлов загружено {}!'.format(uploaded), type='success')
        message.html += '<h3>Файлы:</h3>\n<ul>{}</ul>'.format(list_files)

    # if uploaded > 0:
    # elif files > 0:
    #     showNotify('Информация!', 'Ни одного файла не загружено!', type='info')

    try:
        # SENDING E-MAIL
        mail.send(message)

        showNotify('Отправлено!', 'Сообщение успешно отправленно!', type='success')
    except Exception as ex:
        print 'ERROR: %r' % ex
        showNotify('Внимание!', 'При отправке сообщение возникли проблемы!', type='warning')

    return redirect('/files/sanded', 302)


@application.route('/files/upload', methods=['POST'])
@login_required
# UPLOADING HOME-TASK
def filesUpload():
    fileList = request.files.getlist('home_task')
    comment = request.values.get('comment')

    groups_share = Group.query.filter(Group.id.in_(request.values.getlist('group_share'))).all()

    if len(fileList) == 1 and fileList[0].filename == '':
        showNotify('Ошибка!', 'Необходимо выбрать файл(ы)!', type='warning')
        return redirect('/files/upload')

    if not groups_share:
        showNotify('Ошибка!', 'Необходимо выбрать группу!', type='warning')
        return redirect('/files/upload')

    uploaded = 0

    for f in fileList:
        if f.filename != '':
            saveFile(f, comment=comment, groups=groups_share)
            # if not :
            #     showNotify('Внимание!', 'Файл \\"{filename}\\" уже имеется на сервере!'.format(filename=f.filename),
            #                type='warning')
            # if not uploadFile(f, comment=comment, groups=groups_share):
            #     showNotify('Внимание!', 'Файл \\"{filename}\\" уже имеется на сервере!'.format(filename=f.filename),
            #                type='warning')

            uploaded += 1

    showNotify('Информация!', '{0} файлов загружено!'.format(uploaded), type='success' if uploaded > 0 else 'warning')

    return redirect('/files/sanded', 302)


@application.route('/files/<string:action>', methods=['POST'])
@login_required
def filesAction(action):
    fl = File.query.filter_by(id=request.json['id']).first()

    if action == 'delete':
        if fl:
            db.session.delete(fl)
            db.session.commit()
            try:
                remove(application.config['WEB_UPLOAD_DIR'] + fl.checksum)
            except:
                pass

            showNotify('Готово', 'Файл {} успешно удален!'.format(fl.name), type='success')
        else:
            showNotify('Ошибка!', 'Данный файл не найден!', type='error')
    else:
        showNotify('Ошибка!', 'Неизвестное действие "{action}"!'.format(action=action), type='error')

    print request.json['ref'] if 'ref' in request.json else '/'

    return json.dumps(
        [{'exec': 'document.location.href = \'' + (request.json['ref'] if 'ref' in request.json else '/files') + '\''}])


@application.route('/users/<path:action>/<path:value>/<int:id>', methods=['POST'])
@login_required
def usersAction(action, value, id):
    account = Account.query.get(id)

    if account:
        if action in ['bind']:
            if value in ['student', 'trainer']:
                user = Student() if value == 'student' else Trainer()

                if request.json[value + '_id']:
                    query = Student.query if value == 'student' else Trainer.query
                    user = query.filter_by(id=request.json[value + '_id']).first()
                else:
                    user.name = request.json['account_name']
                    db.session.add(user)

                if value == 'student':
                    account.student = user
                else:
                    account.trainer = user

                # account.name = request.json['account_name']
                db.session.commit()

                showNotify('Успешно!', 'Аккаунт привязан к {}!'.format(user.name), type='success')
            else:
                showNotify('Ошибка!', 'Неизвестное значение "%r"!' % value, type='error')
        elif action in ['unbind']:
            if value in ['user']:
                account.trainer = None
                account.student = None
                db.session.commit()

                showNotify('Успешно!', 'Аккаунт отвязан!', type='success')
            else:
                showNotify('Ошибка!', 'Неизвестное значение "%r"!' % value, type='error')

        elif action in ['delete']:
            if value in ['user']:
                db.session.delete(account)
                db.session.commit()

                showNotify('Успешно!', 'Аккаунт удален!', type='success')
        else:
            showNotify('Ошибка!', 'Неизвестное действие {}!'.format(action), type='error')
    else:
        showNotify('Ошибка!', 'Аккаунт #{} не найден!'.format(id), type='error')

    return json.dumps([{'exec': 'document.location.href = \'/users\''}])


@application.route('/messages/<string:action>', methods=['POST'])
def ajaxMessageAction(action):
    from models import Message

    gid = request.json['group'] if 'group' in request.json else -1
    group = Group.query.get(id=gid)

    if not group:
        group = current_user.student.group

    respDict = []

    if action == 'send':
        messageText = re.sub(' +', ' ', request.json['message'])

        if messageText:
            message = Message(datetime.now(), messageText)
            message.account = current_user
            message.group = group

            try:
                db.session.add(message)
                db.session.commit()
            except IntegrityError as ex:
                application.logger.error(ex)
                db.session.rollback()

    if action == 'read':
        msgList = []
        count = request.json['count'] if 'count' in request.json else 5

        if current_user.student and current_user.student.group or current_user.trainer:
            for msg in group.messages.order_by(Message.timestamp.desc()).limit(count)[::-1]:
                msgList.append({
                    'account': {
                        'picture': msg.account.picture,
                        'name': msg.account.student.name if msg.account.student else msg.account.trainer.name if msg.account.trainer else msg.account.name
                    },
                    'message': {
                        'id': msg.id,
                        'text': msg.message,
                        'time': msg.timestamp.strftime(
                            '%H:%M' if datetime.now().date() == msg.timestamp.date() else '%d/%m/%Y %H:%M')
                    }
                })

        respDict.append({
            'chat': msgList
        })

    return json.dumps(respDict)


@application.route('/trainers/<path:action>', methods=['POST'])
@application.route('/trainers/<path:action>/<int:id>', methods=['POST'])
@login_required
def ajaxTrainersAction(action, id=None):
    trainer = Trainer.query.filter_by(id=id).first()

    if action in ['add'] and not trainer:
        trainer = Trainer()
        db.session.add(trainer)

    if trainer:
        if action in ['add', 'edit']:
            trainer.name = request.json['name']
            trainer.phone = request.json['phone']
            db.session.commit()

            showNotify('Успешно!', 'Тренер {} сохранен!'.format(trainer.name), type='success')
        elif action in ['delete']:
            db.session.delete(trainer)
            db.session.commit()

            showNotify('Успешно!', 'Тренер {} удален!'.format(trainer.name), type='success')
        else:
            showNotify('Ошибка!', 'Неизвестное действие {}!'.format(action), type='error')
    else:
        showNotify('Ошибка!', 'Неизвестный идентификатор {}!'.format(id), type='error')

    return json.dumps([{'exec': 'document.location.href = \'/trainers\''}])


@application.route('/testing/<path:action>', methods=['GET', 'POST'])
def testingAction(action):
    if action in ['begin']:
        session['testing'] = {
            'tests': [t.id for t in Test.query.order_by(func.random()).distinct(Test.id).limit(10).all()],
            'index': 0,
            'answers': {},
            'correct': 0
        }

    if action in ['submit']:
        if 'id' and 'option' in request.values:
            session['testing']['answers'].update({
                request.values['id']: request.values['option']
            })
        action = 'next'

    if action in ['prev', 'next']:
        index = session['testing']['index']
        index = index + 1 if action == 'next' else index - 1

        if index < 0:
            index = 0

        session['testing'].update({'index': index})

        if session['testing']['index'] > 9:
            return redirect('/testing/result')

    if action in ['result']:
        correct = 0

        for id, value in session['testing']['answers'].iteritems():
            test = Test.query.get(id)

            if test.correctanswer == int(value):
                correct += 1

        session['testing'].update({'correct': correct})

        if 'finished' not in session['testing']:
            stat = Stat(10, session['testing']['correct'], datetime.now())
            db.session.add(stat)
            stat.student = current_user.student
            db.session.commit()

            session['testing'].update({'finished': True})

    return redirect('/testing')


@application.route('/polls/<int:id>', methods=['POST'])
def processPolls(id):
    print request.values
    return redirect(request.referrer)


@application.route('/history/add', methods=['POST'])
@application.route('/history/edit/<int:id>', methods=['POST'])
def ajaxHistoryEdit(id=None):
    event = History.query.filter_by(id=id).first()

    if not event:
        event = History(timestamp=datetime.now())
        db.session.add(event)

    if event:
        event.message = request.json['message']
        event.status = request.json['status']
        event.icon = request.json['icon']

        db.session.commit()

    return json.dumps([{'exec': 'document.location.href = \'' + request.referrer + '\''}])


@application.route('/history/delete/<int:id>', methods=['POST'])
def ajaxHistoryDelete(id):
    event = History.query.get(id)

    if event:
        db.session.delete(event)
        db.session.commit()

    return json.dumps([{'exec': 'document.location.href = \'' + request.referrer + '\''}])
