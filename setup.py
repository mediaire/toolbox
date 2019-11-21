from setuptools import setup, find_packages

import mediaire_toolbox

setup(
    name='mediaire_toolbox',
    version=mediaire_toolbox.__version__,
    maintainer='Joerg Doepfert',

    packages=find_packages(),

    long_description=open('README.md').read(),
    install_requires=[
        'nose',
        'redis',
        'SQLAlchemy',
        'passlib'
    ]
)
