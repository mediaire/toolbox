from setuptools import setup

import mediaire_toolbox

setup(
    name='mediaire python toolbox',
    version=mediaire_toolbox.__version__,
    maintainer='joerg doepfert',
    packages=['mediaire_toolbox', 'mediaire_toolbox.queue'],
    long_description=open('README.md').read(),
)