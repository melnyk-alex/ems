# coding: utf-8
from datetime import timedelta

from flask import session
from flask.sessions import SessionInterface

from app import application


class BeakerSession(SessionInterface):
    def open_session(self, app, request):
        session = request.environ['beaker.session']
        return session

    def save_session(self, app, session, response):
        return session.save()


@application.before_request
def make_session_permanent():
    session.permanent = True
    application.permanent_session_lifetime = timedelta(minutes=30)
