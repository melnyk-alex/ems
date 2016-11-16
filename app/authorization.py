# coding: utf-8
import os
import traceback

import httplib2
from flask import session, redirect, request, templating
from flask_login import login_user, logout_user, login_required
from googleapiclient.discovery import build
from oauth2client import client

from app import application, db, lm
from app.functions import getOptions
from app.models import Account
from app.notification import goodbye, welcome, showNotify

flow = client.flow_from_clientsecrets(
    filename=os.path.join(application.config.get('APP_DIR'), 'cred', 'client_secrets.json'),
    scope=['https://www.googleapis.com/auth/userinfo.email',
           'https://www.googleapis.com/auth/userinfo.profile'],
    redirect_uri=application.config.get('HOSTNAME') + '/oauth/gp')
flow.params['include_granted_scopes'] = 'true'
flow.params['approval_prompt'] = 'force'

adminflow = client.flow_from_clientsecrets(
    filename=os.path.join(application.config.get('APP_DIR'), 'cred', 'client_secrets.json'),
    scope=['https://www.googleapis.com/auth/userinfo.email',
           'https://www.googleapis.com/auth/userinfo.profile',
           'https://www.googleapis.com/auth/calendar'],
    redirect_uri=application.config.get('HOSTNAME') + '/admin')
adminflow.params['include_granted_scopes'] = 'true'
adminflow.params['approval_prompt'] = 'force'


def get_service(service, version):
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    http_auth = credentials.authorize(httplib2.Http())
    return build(serviceName=service, version=version, http=http_auth)


@lm.unauthorized_handler
def unauthorized():
    if 'reference' not in session and len(request.path) > 1:
        session['reference'] = request.path

    if 'ref' in request.args:
        session['reference'] = request.args['ref']

    return redirect('/login')


@lm.user_loader
def user_loader(oauth_id):
    return Account.query.filter_by(oauth_id=oauth_id).first()


@application.route('/logout')
def logout():
    logout_user()
    session.clear()
    goodbye()

    return redirect('/')


@application.route('/admin', methods=['GET'])
def oauth_google_plus_admin():
    if 'error' in request.args:
        return redirect('/')
    elif 'code' not in request.args:
        return redirect(adminflow.step1_get_authorize_url())
    else:
        credentials = adminflow.step2_exchange(request.args.get('code'))
        session['credentials'] = credentials.to_json()

        service = get_service('oauth2', 'v2')

        info = service.userinfo().get().execute()

        account = Account.query.filter_by(oauth_id=info['id']).first()

        if account:
            login_user(account)
        else:
            session.clear()

        if 'reference' in session:
            return redirect(session['reference'])

    return redirect('/')


@application.route('/oauth/gp')
def oauth_google_plus():
    if 'code' in request.args:
        try:
            credentials = flow.step2_exchange(request.args.get('code'))
            session['credentials'] = credentials.to_json()
        except:
            traceback.print_exc()
            showNotify('Ошибка!', 'Код авторизации не действителен, выполните вход повторно.', type='error')
            return redirect('/')



        service = get_service('oauth2', 'v2')

        info = service.userinfo().get().execute()

        # Add newest picture to session
        account = Account.query.filter_by(oauth_id=info['id']).first()

        if not account:
            try:
                account = Account('google-plus', info['id'], info['name'], info['email'], info['picture'])

                db.session.add(account)
                db.session.commit()

                showNotify('Здравствуйте!', 'Добро пожаловать!', type='info', icon=account.oauth_name)

                return redirect('/register')
            except:
                traceback.print_exc()
                showNotify('Ошибка!', 'При авторизации возникли проблемы', type='error')

        if account.email == 'edu@codefire.com.ua':
            return redirect(location=adminflow.step1_get_authorize_url())

        account.picture = info['picture']
        db.session.commit()

        login_user(account)

        welcome()

        if 'reference' in session:
            return redirect(session['reference'])

    return redirect('/')


@application.route('/register', methods=['GET'])
@login_required
def register_fill_data():
    return templating.render_template('sign-up.html', options=getOptions('sign-up'))
