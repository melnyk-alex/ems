# coding: utf-8
import datetime
from collections import OrderedDict

from app import db


class Page(db.Model):
    __table_args__ = (db.UniqueConstraint('path', 'access', name='_path_access_unique'),)
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(1024))
    template = db.Column(db.String(255))
    access = db.Column(db.String(255), nullable=False)
    # Menu
    name = db.Column(db.String(255))
    icon = db.Column(db.String(255))
    # Menu - Sorting
    index = db.Column(db.Integer)
    parent_id = db.Column(db.Integer, db.ForeignKey('page.id'), index=True)
    parent = db.relationship(lambda: Page, backref='children', remote_side=[id, index],
                             order_by=lambda: Page.index.asc())

    def __init__(self, path, title=None, template=None, access=None, name=None, icon=None, index=None, parent_id=None):
        self.path = path
        self.title = title
        self.template = template
        self.access = access
        self.name = name
        self.icon = icon
        self.index = index
        self.parent_id = parent_id

    def __repr__(self):
        return '<Page #%r>' % (self.id)


class Account(db.Model):
    __table_args__ = (db.UniqueConstraint('oauth_name', 'oauth_id', name='uq_oauth_name_id'),)
    id = db.Column(db.Integer, primary_key=True)
    oauth_name = db.Column(db.String(255), nullable=False)
    oauth_id = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(255))
    picture = db.Column(db.String(255))
    student_id = db.Column(db.Integer,
                           db.ForeignKey('student.id', name='fk_account_student', onupdate='CASCADE',
                                         ondelete='RESTRICT'))
    trainer_id = db.Column(db.Integer,
                           db.ForeignKey('trainer.id', name='fk_account_trainer', onupdate='CASCADE',
                                         ondelete='RESTRICT'))
    files = db.relationship(lambda: File, backref='account', lazy='dynamic')
    active = db.Column(db.Boolean, default=True)
    main = db.Column(db.Boolean, default=True)
    messages = db.relationship(lambda: Message, backref='account', lazy='dynamic')

    # FLASK-LOGIN
    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    is_anonymous = False

    def get_id(self):
        return self.oauth_id

    # FLASK-LOGIN
    def __init__(self, oauth_name=None, oauth_id=None, name=None, email=None, picture=None, active=None):
        self.oauth_name = oauth_name
        self.oauth_id = oauth_id
        self.name = name
        self.email = email
        self.picture = picture
        self.active = active

    def __repr__(self):
        return '<Account #%r>' % (self.id)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(32))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id', name='fk_student_group', ondelete='RESTRICT',
                                                   onupdate='CASCADE'))  # MTO

    accounts = db.relationship(lambda: Account, backref='student', lazy='dynamic')
    stats = db.relationship(lambda: Stat, backref='student', lazy='dynamic')

    def __init__(self, name=None, phone=None, group_id=None):
        self.name = name
        self.phone = phone
        self.group_id = group_id

    def __repr__(self):
        return '<Student #%r>' % (self.id)

    def lastStat(self):
        return self.stats.order_by(Stat.id.desc()).limit(1).first()

    def bestStat(self):
        return self.stats.order_by(Stat.answers.desc()).limit(1).first()


mtm_group_file = db.Table('group_file', db.Column('id', db.Integer, primary_key=True),
                          db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
                          db.Column('file_id', db.Integer, db.ForeignKey('file.id')))


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    begin = db.Column(db.DateTime)
    schedule = db.Column(db.String(255))
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainer.id', name='fk_group_trainer', ondelete='RESTRICT',
                                                     onupdate='CASCADE'))  # MTO

    students = db.relationship(lambda: Student, backref='group', lazy='dynamic')
    files = db.relationship(lambda: File, secondary=mtm_group_file, backref=db.backref('groups', lazy='dynamic'))
    complete = db.Column(db.Boolean, default=True)
    messages = db.relationship(lambda: Message, backref='group', lazy='dynamic')
    event_id = db.Column(db.String(255), nullable=True)

    def __init__(self, name=None, begin=None, schedule=None, trainer_id=None, complete=False):
        self.name = name
        self.begin = begin
        self.schedule = schedule
        self.trainer_id = trainer_id
        self.complete = complete

    def student_files_stat(self):
        data = []

        for student in self.students:
            studentDict = OrderedDict()

            for file in student.accounts.filter_by(main=True).first().files:
                date = file.timestamp.strftime("%m.%d")
                count = studentDict.get(date)

                studentDict.update({
                    date: count + 1 if count else 1
                })

            data.append({
                student.name: studentDict
            })

        return data

    def lesson_days_str(self):
        w_days = self.schedule.replace('MO', 'ПН').replace('TU', 'ВТ').replace('WE', 'СР').replace('TH', 'ЧТ')\
            .replace('FR', 'ПТ').replace('SA', 'СБ').replace('SU', 'ВС')

        return w_days

    def lesson_time_str(self):
        return self.begin.strftime('%H:%M') + ' - ' + self.begin.replace(hour=(self.begin.hour + 2)).strftime('%H:%M')

    def lesson_from_to_time(self):
        return self.lesson_time_format(self.begin)

    def lesson_time_format(self, timestamp):
        return '{date} ({start} - {end})'.format(
            date=timestamp.strftime('%d.%m.%Y'),
            start=timestamp.strftime('%H:%M'),
            end=timestamp.replace(hour=(timestamp.hour + 2)).strftime('%H:%M')
        )

    def next_lessons(self, count=1):
        dates = self.next_lessons_dates(count=count)

        lessons = []

        for date in dates:
            lessons.append(self.lesson_time_format(date))

        return lessons

    def __repr__(self):
        return '<Group #{}>'.format(self.id)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    message = db.Column(db.String)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id', name='fk_msg_account'))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id', name='fk_msg_group'))

    def __init__(self, timestamp, message):
        self.timestamp = timestamp
        self.message = message


class Trainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(32), unique=True)
    groups = db.relationship(lambda: Group, backref='trainer', lazy='dynamic')
    accounts = db.relationship(lambda: Account, backref='trainer', lazy='dynamic')

    def __init__(self, name=None, phone=None):
        self.name = name
        self.phone = phone

    def __repr__(self):
        return '<Trainer #%r>' % (self.id)


class File(db.Model):
    __table_args__ = (db.UniqueConstraint('checksum', 'account_id', name='uq_checksum_account'),)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    checksum = db.Column(db.String(32), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    comment = db.Column(db.String(512))
    account_id = db.Column(db.Integer, db.ForeignKey('account.id', name='fk_file_account'))

    def __init__(self, name, size=None, checksum=None, timestamp=None, comment=None, account_id=None):
        self.name = name
        self.size = size
        self.checksum = checksum
        self.timestamp = timestamp
        self.comment = comment
        self.account_id = account_id

    def size_str(self):
        from hurry.filesize import size, alternative

        return size(self.size, system=alternative)

    def __repr__(self):
        return '<File %r>' % (self.id)


class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(1024))
    correctanswer = db.Column(db.Integer)
    answeramount = db.Column(db.Integer)
    answer = db.Column(db.String(1024))
    option1 = db.Column(db.String(255))
    option2 = db.Column(db.String(255))
    option3 = db.Column(db.String(255))
    option4 = db.Column(db.String(255))
    option5 = db.Column(db.String(255))

    def __init__(self, question=None, correctanswer=None, answeramount=None, answer=None, option1=None, option2=None,
                 option3=None, option4=None, option5=None):
        self.question = question
        self.correctanswer = correctanswer
        self.answeramount = answeramount
        self.answer = answer
        self.option1 = option1
        self.option2 = option2
        self.option3 = option3
        self.option4 = option4
        self.option5 = option5

    def __repr__(self):
        return '<Test %r>' % (self.id)


class Stat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    questions = db.Column(db.Integer, nullable=False)
    answers = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', name='fk_stat_student', ondelete='SET NULL',
                                                     onupdate='CASCADE'))

    def __init__(self, questions=None, answers=None, timestamp=None):
        self.questions = questions
        self.answers = answers
        self.timestamp = timestamp

    def __repr__(self):
        return '<Stat %r answers: %s>' % (self.id, self.answers)


class Polls(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String)
    answer1 = db.Column(db.String(255))
    answer2 = db.Column(db.String(255))
    answer3 = db.Column(db.String(255))
    answer4 = db.Column(db.String(255))
    answer5 = db.Column(db.String(255))

    def __init__(self, question, answer1=None, answer2=None, answer3=None, answer4=None, answer5=None):
        self.question = question
        self.answer1 = answer1
        self.answer2 = answer2
        self.answer3 = answer3
        self.answer4 = answer4
        self.answer5 = answer5


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    message = db.Column(db.String)
    status = db.Column(db.String(255))
    icon = db.Column(db.String(255))

    def __init__(self, timestamp, message=None, status=None, icon=None):
        self.timestamp = timestamp
        self.message = message
        self.status = status
        self.icon = icon


mtm_student_category = db.Table('link_student_to_resource_category',
                                db.Column('resource_category_id', db.Integer, db.ForeignKey('resource_category.id')),
                                db.Column('student_id', db.Integer, db.ForeignKey('student.id')))


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    external_link = db.Column(db.String)
    category_id = db.Column(db.Integer, db.ForeignKey('resource_category.id', name='fk_resource_category'))

    def __init__(self, name=None):
        self.name = name


class ResourceCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    type = db.Column(db.String(255))

    resources = db.relationship(lambda: Resource, backref='category', lazy='dynamic')

    students = db.relationship('Student', secondary=mtm_student_category,
                               backref=db.backref('categories', lazy='dynamic'))

    def __init__(self, name=None):
        self.name = name
