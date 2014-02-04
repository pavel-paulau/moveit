from setuptools import setup

setup(
    name='moveit',
    version='0.2',
    description='ns_server master events analyzer',
    author='Pavel Paulau',
    author_email='pavel.paulau@gmail.com',
    py_modules=['moveit'],
    entry_points={
        'console_scripts': ['moveit = moveit:main']
    },
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
