# coding: utf-8
import os
import re
from collections import OrderedDict
from datetime import datetime, timedelta

from flask import templating, safe_join, send_from_directory, abort, session, request, make_response
from flask_login import login_required, current_user
from sqlalchemy import func

from app import application, db
from app.functions import getOptions
from app.models import Page, Account, Student, Trainer, Group, File, Test, Stat, History, ResourceCategory, Polls

from app.authorization import flow, adminflow

# CLOSING SESSION AFTER REQUEST
@application.teardown_request
def teardown_request(exception=None):
    if db.session:
        db.session.close()

    pass


# apple-touch-icon.png
@application.route('/assets/<path:filename>')
def ok(filename):
    filename = safe_join('assets/', filename)
    cache_timeout = application.get_send_file_max_age(filename)
    return send_from_directory(application.static_folder, filename, cache_timeout=cache_timeout)


@application.route('/robots.txt')
@application.route('/sitemap.xml')
def default_files():
    filename = request.url_rule.rule[1:]
    cache_timeout = application.get_send_file_max_age(filename)

    return send_from_directory(application.static_folder, filename, cache_timeout=cache_timeout)


@application.errorhandler(404)
@application.errorhandler(403)
# ERROR HANDLERS
def page_not_found(e):
    message = 'Данный адрес не существует.'

    if e.code == 403:
        message = 'Данный адрес не доступен!'

    return templating.render_template('errors/errors.html', code=e.code, message=message), e.code



@application.route('/login', methods=['GET'])
# AUTHORIZATION
def login():
    options = getOptions('/login')
    options.update({
        'today': datetime.now(),
        'oauth2': flow.step1_get_authorize_url(),
        'oauth2admin': adminflow.step1_get_authorize_url()
    })

    # if 'ref' in request.args and 'reference' not in session:
    #     session['reference'] = request.args['ref']

    # Show notify if exists
    if 'notify' in session:
        options.update({
            'notify': session.pop('notify')
        })

    return templating.render_template('sign-in.html', options=options)


@application.route('/files/<path:filename>/<path:reprname>')
@login_required
# FILES REQUEST RESOLVER
def files_resolve(filename, reprname=None):
    filename = safe_join('', filename)
    cache_timeout = application.get_send_file_max_age(filename)
    resp = send_from_directory(application.config['WEB_UPLOAD_DIR'], filename, cache_timeout=cache_timeout)
    resp.headers.add('Content-Disposition', 'attachment; filename=\"{}\"'.format(reprname or filename))
    return resp


@application.route('/', methods=['GET', 'POST'])
@application.route('/<path:url>', methods=['GET', 'POST'])
@login_required
# URL REQUEST RESOLVER
def get_post_page(url='index'):
    # Getting options
    options = getOptions(url)

    # Show notify if exists
    if 'notify' in session:
        options.update({
            'notify': session.pop('notify')
        })

    # Check page exists
    if not options['page']:
        return abort(404)

    # Check access to page
    if options['page'] not in options['pages'] and Page.query.get(options['page'].parent_id) not in options['pages']:
        print('%r isn\'t allowed for %r!' % (options['page'], options['account']['user']))
        return abort(403, 'Page "{page}" isn\'t allowed!'.format(page=url))

    extract_options(options)

    return templating.render_template((options['page'].template or 'index') + '.html', options=options)


def extract_options(options):
    if options['account_type'] in ['root']:
        extract_root_options(options)
    elif options['account_type'] in ['trainer']:
        extract_trainer_options(options)
    elif options['account_type'] in ['student']:
        extract_student_options(options)


def extract_root_options(options):
    options.update({
        'history': History.query.order_by(History.timestamp.desc()).all()
    })

    if options['url'] in ['index']:
        options.update({
            'users': len(Account.query.all()),
            'students': len(Student.query.all()),
            'trainers': len(Trainer.query.all()),
            'filesCount': len(os.walk(application.config.get('WEB_UPLOAD_DIR')).next())
        })

    options.update({'trainerList': Trainer.query.all()})

    if options['url'] in ['users', 'students', 'groups', 'trainers']:
        options.update({'groupList': Group.query.all()})
        options.update({'groups': Group.query})
        options.update({'studentList': Student.query.all()})

    if options['url'] in ['files', 'index']:
        options.update({'fileList': File.query.all()})

    if options['url'] in ['groups']:
        ts = datetime.now().strftime('%m%y')
        groups = Group.query.filter(Group.name.like('%' + ts)).all()

        options.update({
            'next_group_name': str(len(groups) + 1) + ts
        })

    options.update({
        'newUserList': Account.query.filter(
            (Account.email != application.config.get('WEB_ROOT_EMAIL')) & (Account.student == None) & (
                Account.trainer == None)).all(),
        'userList': Account.query.filter(
            (Account.student != None) | (Account.trainer != None)).all()
    })


def extract_trainer_options(options):
    if options['url'] in ['index']:
        cwd = datetime.now()

        today_groups = current_user.trainer.groups.filter(Group.complete == True).filter(
            Group.schedule.contains(str(cwd.weekday()))).filter(
            func.TIME(Group.begin).__gt__(cwd.time())).order_by(func.TIME(Group.begin)).all()

        cwd = datetime.now() + timedelta(days=1)

        tomorrow_groups = current_user.trainer.groups.filter(Group.complete == True).filter(
            Group.schedule.contains(str(cwd.weekday()))).order_by(func.TIME(Group.begin)).all()

        options.update({
            'timetable': {
                'today': today_groups,
                'tomorrow': tomorrow_groups
            }
        })

    if options['url'] in ['index', 'files/sanded', 'files/received']:
        trainer_file_list = File.query.join(Account).join(Trainer).filter_by(id=current_user.trainer.id).order_by(
            File.timestamp.desc()).all()
        student_file_list = File.query.join(Account).join(Student).join(Group).filter(
            Group.trainer == current_user.trainer).order_by(File.timestamp.desc()).all()

        options.update({
            'trainerFileList': trainer_file_list,
            'studentFileList': student_file_list
        })


def extract_student_options(options):
    options.update({
        'poll': Polls.query.order_by(Polls.id.desc()).limit(1).first()
    })

    options.update({
        'history': History.query.order_by(History.timestamp.desc()).limit(10).all()
    })
    options.update({
        'categories': ResourceCategory.query.all()
    })

    if 'testing' in session:
        testing = session.pop('testing') if session['testing'].has_key('finished') else session['testing']

        options.update({
            'testing': {
                'tests': Test.query.filter(Test.id.in_(testing['tests'])).all(),
                'index': testing['index'],
                'answers': testing['answers'],
                'correct': testing['correct'],
                'finished': testing['finished'] if testing.has_key('finished') else False
            }
        })

    uploaded_files = File.query.join(Account).join(Student).filter(Student.id == current_user.student.id).order_by(
        File.timestamp.asc()).all()

    # if url in ['index', 'files']:
    options.update({
        'uploadedFiles': uploaded_files
    })

    if current_user.student.stats.all():
        options.update({
            'stats': {
                'last': current_user.student.stats.order_by(Stat.timestamp.desc()).first(),
                'best': current_user.student.stats.order_by(Stat.answers.desc()).first()
            }
        })

    # STATISTIC
    group_files_stat = OrderedDict()

    if current_user.student.group:
        for student in current_user.student.group.students.order_by(Student.id.desc()):
            student_files = File.query.join(Account).join(Student).filter(
                Student.id == student.id).order_by(File.timestamp.desc()).all()

            files_stat = OrderedDict()

            for studentFile in student_files:
                ts = studentFile.timestamp.strftime('%Y.%m.%d')
                files_stat.update({
                    ts: files_stat[ts] + 1 if files_stat.has_key(ts) else 1
                })

            group_files_stat.update({student: files_stat})

    options.update({'group_files_stat': group_files_stat})


@application.route('/students/<path:action>')
@application.route('/students/<path:action>/<path:group_id>')
def transform_view(action, group_id=None):
    file_contents = ''

    studentList = Student.query.all()

    extension = 'txt'
    mime = 'text/plain'

    if group_id:
        studentList = Student.query.filter_by(group_id=group_id).all()

    if action == 'emails':
        file_contents = str.join('\n', [acc.email for student in studentList for acc in student.accounts.all()])
    elif action == 'phones':
        file_contents = str.join('\n', [re.sub('[\\s\-\(\)\+]+', '', student.phone) for student in studentList if
                                        student.phone])
    elif action == 'contacts':
        file_contents = 'Name,Mobile Phone,E-mail Address\n'

        for stud in studentList:
            emails = str.join(',', [a.email for a in stud.accounts.all()])
            file_contents += str.join(',', [stud.name or '', stud.phone or '', '"' + emails + '"']) + '\n'

        extension = 'csv'
        mime = 'text/csv'
    else:
        return abort(404, 'File not found!')

    response = make_response(file_contents)
    response.headers['Content-Type'] = '{mime}; charset=utf-8'.format(mime=mime)
    response.headers['Content-Disposition'] = 'attachment; filename={name}-{group}.{ext}'.format(name=action,
                                                                                                 group=Group.query.filter_by(
                                                                                                     id=group_id).first().name if group_id else 'all',
                                                                                                 ext=extension)

    return response
