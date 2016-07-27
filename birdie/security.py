from pyramid.security import Authenticated
from pyramid.security import Allow

import birdie.models
    
from cryptacular.bcrypt import BCRYPTPasswordManager

from .models import (
    DBSession
)

Crypt = BCRYPTPasswordManager()

class RootFactory(object):
    __acl__ = [
        (Allow, Authenticated, 'registered')
    ]
    def __init__(self, request):
        pass
        

def check_login(login, password):
    user = DBSession.hmget('user:'+login,'password')
    if user[0] is not None:
        hashed_password = user[0]
        if hashed_password.decode() == password:
            return True
    return False
