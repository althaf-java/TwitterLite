from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from .security import RootFactory


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    
    authc_policy = AuthTktAuthenticationPolicy('b1rd13')
    authz_policy = ACLAuthorizationPolicy()
    
    config = Configurator(root_factory=RootFactory,
                          authentication_policy=authc_policy,
                          authorization_policy=authz_policy,                          
                          settings=settings)
    # for pyramid 1.5 branch compatibility
    config.include('pyramid_chameleon')
    
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('about', '/about')
    config.add_route('join', '/join')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('mybirdie', '/{username}')
    config.add_route('profile', '/{username}/view')
    config.add_route('follow', '/{username}/follow')
    config.add_route('unfollow', '/{username}/unfollow')
    config.scan()
    return config.make_wsgi_app()
