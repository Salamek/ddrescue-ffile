from setuptools import setup, find_packages


def read_readme() -> str:
    with open('README.md', 'r', encoding='utf-8') as f:
        return f.read()


setup(
    name='ddrescue-ffile',
    version='0.0.1',
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=[
        'tqdm',
    ],
    tests_require=[
        'tox'
    ],
    url='https://github.com/Salamek/ddrescue-ffile',
    license='GPL-3.0 ',
    author='Adam Schubert',
    author_email='adam.schubert@sg1-game.net',
    description='ddrescue image corrupted files detection tool',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    test_suite='tests',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development',
    ],
    python_requires='>=3.4',
    project_urls={
        'Release notes': 'https://github.com/Salamek/ddrescue-ffile/releases',
    },
)