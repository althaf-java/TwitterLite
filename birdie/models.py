import redis

# connexion à la base de données
DBSession = redis.Redis(unix_socket_path='/var/run/redis/redis.sock')
