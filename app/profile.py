# coding: utf-8
from flask import templating, safe_join, send_from_directory, abort, session, request, make_response
from flask_login import login_required, current_user

from app import application, db
from app.functions import getOptions


@application.route("/profile")
def get_profile():
    options = getOptions('/profile')

    return templating.render_template('student/profile.html', options=options)
