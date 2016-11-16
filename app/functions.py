# coding: utf-8
from datetime import datetime, timedelta
import hashlib
import os

from flask import session
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from werkzeug.utils import secure_filename

from app import db, application
from app.models import Page, Account, File, Group


def currentAccount(account_id=None):
    if account_id:
        return Account.query.filter_by(id=account_id).first()
    elif session.has_key('account_id'):
        return Account.query.filter_by(id=session['account_id']).first()


def getUserOptions():
    options = {
        'account': current_user,
        'account_type': 'guest'
    }

    # Get user info
    if not current_user.is_anonymous:
        if current_user.student:
            options.update({'account_type': 'student'})
        elif current_user.trainer:
            options.update({'account_type': 'trainer'})
        elif current_user.email == application.config['WEB_ROOT_EMAIL']:
            options.update({'account_type': 'root'})

    return options


def getPageOptions(url, access):
    options = {
        'url': url,
        'pages': Page.query.filter((Page.access == access) & (Page.parent_id == None)).order_by(Page.index.asc()).all(),
        'page': Page.query.filter_by(path=url).filter_by(access=access).first()
    }

    return options


def getOptions(url):
    ''' Getting options for request runtime.

    :param url: path for options
    :return: options dict.
    '''
    options = getUserOptions()
    pages = getPageOptions(url, options['account_type'])
    options.update(pages)
    options.update({
        'today': datetime.now(),
        'tomorrow': datetime.now() + timedelta(days=1)
    })

    return options


def saveFile(f, comment=None, groups=None):
    checksum = hashlib.md5(f.read()).hexdigest()

    file_size = writeFile(f, checksum)

    uploaded = File.query.filter_by(checksum=checksum).first()

    if not uploaded:
        uploaded = File(name=secure_filename(f.filename), checksum=checksum, timestamp=datetime.now(), comment=comment,
                        size=file_size)
        uploaded.account = current_user
        db.session.add(uploaded)

    uploaded.groups.extend(groups)

    try:
        db.session.commit()
    except IntegrityError as ex:
        application.logger.error(ex)
        db.session.rollback()
        return False

    return True


def writeFile(f, name):
    path = os.path.join(application.config.get('WEB_UPLOAD_DIR'), name)

    if not os.path.exists(path):
        f.seek(0)
        f.save(path)

    f.seek(0, os.SEEK_END)
    return f.tell()


def uploadFile(f, comment=None, groups=None):
    ''' Storing file and writing information into database.

    :param f: storing file.
    :param comment: comments for file.
    :param group: share with group.
    :return: True if ok, otherwise False.
    '''
    checksum = hashlib.md5(f.read()).hexdigest()

    # getting file size
    f.seek(0, os.SEEK_END)
    file_size = f.tell()

    # save file ot disk
    path = os.path.join(application.config.get('WEB_UPLOAD_DIR'), checksum)

    if not os.path.exists(path):
        f.seek(0)
        f.save(path)

    if not groups:
        upload_file = File(name=secure_filename(f.filename), checksum=checksum,
                           timestamp=datetime.now(), comment=comment, size=file_size)

        upload_file.account = current_user

        try:
            db.session.add(upload_file)
            db.session.commit()
        except IntegrityError as ex:
            application.logger.error(ex)
            db.session.rollback()
    else:
        for group in groups:
            upload_file = File(name=secure_filename(f.filename), checksum=checksum,
                               timestamp=datetime.now(), comment=comment, size=file_size)

            # owner & group
            upload_file.account = current_user
            upload_file.group = group

            try:
                db.session.add(upload_file)
                db.session.commit()
            except IntegrityError as ex:
                application.logger.error(ex)
                db.session.rollback()

    return checksum