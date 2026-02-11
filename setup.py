from setuptools import setup, find_packages

setup(
    name='pylinkit',
    version='4.0.0',
    description='Python LinkIt BLE/USB configuration tool',
    author='Liam Wickins',
    author_email='liam@icoteq.com',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
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
    ],
    entry_points={
        'console_scripts': [
            'pylinkit = pylinkit.__main__:main'
        ]
    },
)
