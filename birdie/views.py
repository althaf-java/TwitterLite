from pyramid.response import Response
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    )
from pyramid.renderers import get_renderer
from pyramid.security import (
    remember, 
    forget, 
    authenticated_userid,
    )
from pyramid.view import (
    view_config,
    forbidden_view_config,
    )
from pyramid.url import route_url

from repoze.timeago import get_elapsed
from datetime import datetime
import time

from .models import (
    DBSession
)

from .security import check_login


conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_birdie_db" script
    to initialize your database tables.  Check your virtual 
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""

MAX_CHIRPS = 15
MAX_MY_CHIRPS = 5
MAX_USERS = 5
MAX_FRIENDS = 0
MAX_FOLLOWERS = 0

class BirdieViews(object):
    def __init__(self, request):
        self.request = request
        renderer = get_renderer("templates/layout-bootstrap.pt")
        self.layout = renderer.implementation().macros['layout']
        self.logged_in = authenticated_userid(request)
        self.app_url = request.application_url
        self.static_url = request.static_url

    @view_config(route_name='about',
                renderer='templates/about-bootstrap.pt')
    def about_page(self):
        return {}
    
    @view_config(route_name='home',
                renderer='templates/birdie-bootstrap.pt')
    def birdie_view(self):
        username = self.logged_in
        user = None
        chirps, users = [], []
        if username:
            userData = DBSession.hmget('user:'+username,['fullname'])
            friends = DBSession.zrange('following:'+username,0,-1)
            friendsUTF8 = []
            for f in friends:
                friendsUTF8.append(f.decode('utf8'))
            user = {'username' : username,
                    'fullname' : userData[0],
                    'friends'  : friendsUTF8}

        # liste des chirps
        timelineChirps = DBSession.lrange('timeline',0,MAX_CHIRPS-1)
        for chirpsId in timelineChirps:
            aChirp = DBSession.hmget('chirp:'+str(int(chirpsId)),['chirp','author','timestamp'])
            author = DBSession.hmget('user:'+aChirp[1].decode('utf8'),['fullname'])
            if aChirp[0]:
                chirps.append({'chirp'     : aChirp[0],
                               'author'    : {'username' : aChirp[1].decode("utf8"),'fullname':author[0]},
                               'timestamp' : datetime.strptime(aChirp[2].decode("utf8"), "%Y-%m-%d %H:%M:%S.%f")})

        return {'elapsed': get_elapsed,
            'user': user,
            'chirps': chirps,
            'latest_users': DBSession.lrange('lastUsers',0,MAX_USERS-1),
            'users_count'  : DBSession.llen('lastUsers'),
            'chirps_count' : DBSession.llen('timeline'),
        }


    @view_config(route_name='mybirdie',
                permission='registered',
                renderer='templates/mybirdie-bootstrap.pt')
    def my_birdie_view(self):
        username = self.logged_in
        chirps = []
        my_chirps = []
        
        # liste des followers
        followers = []
        followersId = DBSession.zrange('followers:'+username,0,-1)
        for fid in followersId:
            user = DBSession.hmget('user:'+str(fid),'fullname')
            followers.append({'username' : fid,
                              'fullname' : user[0]})
        
        # liste des amis
        friends= []
        friendsId = DBSession.zrange('following:'+username,0,-1)
        for fid in friendsId:
            user = DBSession.hmget('user:'+str(fid),'fullname')
            friends.append({'username' : fid,
                            'fullname' : user[0]})
        
        userData = DBSession.hmget('user:'+username,'fullname','about')
        user = {'username'       : username,
                'fullname'       : userData.pop(0),
                'about'          : userData.pop(0),
                'followers'      : followers,
                'friends'        : friends,
                'followersCount' : DBSession.zcount('followers:'+username,'-inf','+inf'),
                'friendsCount'   : DBSession.zcount('following:'+username,'-inf','+inf')}
        
        # ajoute un nouveau chirp
        if ('form.submitted' in self.request.params and self.request.params.get('chirp')):
            dataChirp = {'chirp'     : self.request.params.get('chirp'),
                         'author'    : username,
                         'timestamp' : datetime.utcnow()}
            chirpId = DBSession.incr('next_chirp_id');
            DBSession.hmset('chirp:'+str(chirpId),dataChirp)
            
            # liste des chirps écrits de l'utilisateur
            DBSession.lpush('chirpsOfUser:'+username,chirpId)
            
            # liste de followers
            listOfFollowers = DBSession.zrange('followers:'+username,0,-1)
            
            # mise à jour de la liste de chirp des utilisateurs
            for follower in listOfFollowers:
                DBSession.zadd('chirpsForUser:'+follower.decode('utf8'),chirpId,chirpId)
            
            # mise à jour de la liste principale
            DBSession.lpush('timeline',chirpId)

            url = self.request.route_url('mybirdie', username=username)
            return HTTPFound(url)

        # liste des chirps écrit par l'utilisateur
        listOfMyChirps = DBSession.lrange('chirpsOfUser:'+username,0,MAX_MY_CHIRPS-1)
        for chirpsId in listOfMyChirps:
            aChirp = DBSession.hmget('chirp:'+str(int(chirpsId)),['chirp','timestamp'])
            if aChirp[0]:
                my_chirps.append({'chirp'     : aChirp[0],
                                  'timestamp' : datetime.strptime(aChirp[1].decode("utf8"), "%Y-%m-%d %H:%M:%S.%f")})

        # liste des chirps suivi par l'utilisateur
        listOfMyfollowedChirps = DBSession.zrevrange('chirpsForUser:'+username,0,MAX_CHIRPS-1)
        for chirpsId in listOfMyfollowedChirps:
            aChirp = DBSession.hmget('chirp:'+str(int(chirpsId)),['chirp','author','timestamp'])
            author = DBSession.hmget('user:'+str(aChirp[1]),['fullname'])
            if aChirp[0]:
                chirps.append({'chirp'     : aChirp[0],
                               'author'    : {'username' : aChirp[1],'fullname':author[0]},
                               'timestamp' : datetime.strptime(aChirp[2].decode("utf8"), "%Y-%m-%d %H:%M:%S.%f")})

        return {'elapsed': get_elapsed,
                'user': user,
                'chirps': chirps,
                'my_chirps': my_chirps}


    @view_config(route_name='login',
                renderer='templates/login-bootstrap.pt')
    @forbidden_view_config(renderer='birdie:templates/login-bootstrap.pt')
    def login(self):
        request = self.request
        login_url = request.route_url('login')
        join_url = request.route_url('join')
        came_from = request.params.get('came_from')
        if not came_from : # first time it enters the login page
            came_from = request.referer
        message = ''
        login = ''
        password = ''
        if 'form.submitted' in request.params:
            login = request.params['login']
            password = request.params['password']
            if check_login(login, password):
                headers = remember(request, login)
                if (came_from == login_url or came_from == join_url or came_from == self.app_url):
                    came_from = request.route_url('mybirdie', username=login)  # never use login form itself as came_from
                return HTTPFound(location=came_from,
                                 headers=headers)
            message = 'Failed login'

        return {'message'   : message,
                'came_from' : came_from,
                'login'     : login,
                'password'  : password}

    @view_config(route_name='logout')
    def logout(self):
        headers = forget(self.request)
        url = self.request.route_url('home')
        return HTTPFound(location=url,
                         headers=headers)


    @view_config(route_name='join',
                renderer='birdie:templates/join-bootstrap.pt')
    def join(self):

        request = self.request
        join_url = request.route_url('join')
        login_url = request.route_url('login')
        came_from = request.params.get('came_from')
        if not came_from: # first time it enters the join page
            came_from = request.referer
        
        if 'form.submitted' in request.params:
        # registration form has been submitted
            username = request.params.get('username')
            password = request.params.get('password')
            confirm = request.params.get('confirm')
            fullname = request.params.get('fullname')
            about = request.params.get('about')
            message = ''

            user = DBSession.hmget('user:'+username,'password')

            if username is '':
                message = "The username is required."
            elif (password is '' and confirm is ''):
                message = "The password is required."
            elif user[0]:
                message = "The username {} already exists.".format(username)
            elif confirm != password:
                message = "The passwords don't match."
            elif len(password) < 6:
                message = "The password is too short."

            if message:
                return {'message'   : message,
                        'came_from' : came_from,
                        'username'  : username,
                        'fullname'  : fullname,
                        'about'     : about}
           
            # register new user
            userData = {'password' : password,
                       'fullname'  : fullname,
                       'about'     : about,
                       'dor'       : datetime.utcnow()}

            DBSession.hmset('user:'+username,userData);
            DBSession.lpush('lastUsers',username)

            headers = remember(request, username)
            
            if (came_from == join_url or came_from == login_url or came_from == self.app_url):
                came_from = request.route_url('mybirdie', username=username)  # never use login form itself as came_from
            return HTTPFound(location = came_from,
                             headers = headers)

        # default - prepare empty sign in form
        return {'message'   : '',
                'came_from' : came_from,
                'username'  : '',
                'fullname'  : '',
                'about'     : ''}


    @view_config(route_name='profile',
                 permission='registered',
                 renderer='birdie:templates/user-bootstrap.pt')
    def profile_view(self):
        auth_username = self.logged_in
        username = self.request.matchdict['username']
        chirps = []
        
        if auth_username==username: # redirect to my_birdie page
            return HTTPFound(location = self.request.route_url('mybirdie', username=username))

        ###########################
        # utilisateur authentifié
        ###########################

        # liste des amis
        friendsAuth = []
        friendsList = DBSession.zrange('following:'+auth_username,0,-1)
        for fid in friendsList:
            friendsAuth.append(fid.decode('utf8'))

        auth_userData = DBSession.hmget('user:'+auth_username,['fullname','about'])
        auth_user = {'username' : username,
                     'fullname' : auth_userData[0],
                     'about'    : auth_userData[1],
                     'friends'  : friendsAuth}

        ##########################
        # Profil utilisateur
        ##########################

        userData = DBSession.hmget('user:'+username,['fullname','about'])
        user = {'username'       : username,
                'fullname'       : userData[0],
                'about'          : userData[1],
                'followersCount' : DBSession.zcount('followers:'+username,'-inf','+inf'),
                'friendsCount'   : DBSession.zcount('following:'+username,'-inf','+inf')}

        # liste des chirps écrit par l'utilisateur
        listOfMyChirps = DBSession.lrange('chirpsOfUser:'+username,0,MAX_CHIRPS-1)
        for chirpsId in listOfMyChirps:
            aChirp = DBSession.hmget('chirp:'+str(int(chirpsId)),['chirp','timestamp'])
            if aChirp[0]:
                chirps.append({'chirp'     : aChirp[0],
                               'timestamp' : datetime.strptime(aChirp[1].decode("utf8"), "%Y-%m-%d %H:%M:%S.%f")})
        
        return {'elapsed'   : get_elapsed,
                'auth_user' : auth_user,
                'user'      : user,
                'chirps'    : chirps}

    @view_config(route_name='follow',
                 permission="registered",
                 renderer='birdie:templates/fake.pt')
    def follow(self):
        username = self.logged_in
        came_from=self.request.referer
        if not came_from:
            came_from=self.app_url

        friend_username = self.request.matchdict.get('username')
        
        chirpToAddToPersonalTimeline = DBSession.lrange('chirpsOfUser:'+friend_username,0,-1)
        for chirpId in chirpToAddToPersonalTimeline:
            DBSession.zadd('chirpsForUser:'+username,chirpId.decode("utf8"),chirpId.decode("utf8"))

        DBSession.zadd('following:'+username,friend_username,time.time())
        DBSession.zadd('followers:'+friend_username,username,time.time())
        return HTTPFound(location=came_from)


    @view_config(route_name='unfollow',
                 permission="registered",
                 renderer='birdie:templates/fake.pt')
    def unfollow(self):
        username = self.logged_in
        came_from=self.request.referer
        if not came_from:
            came_from=self.app_url
        
        friend_username = self.request.matchdict.get('username')
        
        chirpToRemoveFromPersonalTimeline = DBSession.lrange('chirpsOfUser:'+friend_username,0,-1)
        for chirpId in chirpToRemoveFromPersonalTimeline:
            DBSession.zrem('chirpsForUser:'+username,chirpId.decode("utf8"))

        DBSession.zrem('following:'+username,friend_username)
        DBSession.zrem('followers:'+friend_username,username)

        return HTTPFound(location=came_from)

