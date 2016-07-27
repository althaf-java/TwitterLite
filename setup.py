import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid>=1.4',
    'pyramid_chameleon', # for compatibility with pyramid 1.5 branch
    'redis',
    'hiredis',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar>=1.0.8',
    'waitress',
    'repoze.timeago',
    'cryptacular',
    ]

setup(name='birdie',
      version='0.1',
      description='birdie',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='gr-',
      author_email='guillaume.raschia@gmail.com',
      url='https://github.com/gr-',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='birdie',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = birdie:main
      """,
      )
