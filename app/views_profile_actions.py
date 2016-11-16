# coding: utf-8
import json
import traceback

from flask import request
from flask_login import login_required, current_user

from app import application, db


@application.route('/profile/save', methods=['POST'])
@login_required
def ajax_profile_save():
    data = request.json

    try:
        account = current_user

        account.name = data['name']
        account.phone = data['phone']

        db.session.commit()
    except:
        traceback.print_exc()
        return json.dumps([{
            'status': 'danger',
            'title': 'Внимание!',
            'text': 'Возникли проблемы при создании Вашего аккаунта.'
        }])

    return json.dumps([{'exec': 'document.location.href = \'/\''}])
