from setuptools import setup

import mediaire_toolbox

setup(
    name='mediaire_toolbox',
    version=mediaire_toolbox.__version__,
    maintainer='joerg doepfert',
    packages=['mediaire_toolbox',
              'mediaire_toolbox.queue'],
    long_description=open('README.md').read(),
    install_requires=[
        'nose',
        'redis',
    ]
)