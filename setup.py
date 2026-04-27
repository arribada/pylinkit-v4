from setuptools import setup, find_packages

with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pylinkit',
    version='4.1.1',
    description='Python LinkIt V4 tracker configuration tool (BLE / USB / UART)',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    author='FOURNIER Geoffrey',
    author_email='fournier.geoffrey77@gmail.com',
    url='https://github.com/arribada/pylinkit-v4',
    license='GPL-3.0-or-later',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Communications :: Ham Radio',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'bleak',
        'pyserial',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'pylinkit = pylinkit.__main__:main'
        ]
    },
)
