from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='hci',
    version='0.0.8',
    description='Library for creating and parsing HCI packets.',
    url='https://github.com/Himanshu-4/hci-tool',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    keywords=['HCI', 'protocol','encode', 'decode',
              'ble', 'bluetooth low energy'],
    packages=find_packages(exclude=['struct', 'docs', 'os']),
    python_requires='>=3.5',
    install_requires=[
        'pyserial>=3.0',
        'pyqt5>=5.15.4',
    ],
    package_data={
        '': ['*.txt', '*.rst'],
        'hci': ['*.txt', '*.rst'],
        'hci/cmds': ['*.txt', '*.rst'],
        'hci/transport': ['*.txt', '*.rst'],
        'hci/transport/SDIO': ['*.txt', '*.rst'],
        'hci/transport/UART': ['*.txt', '*.rst'],
        'hci/transport/USB': ['*.txt', '*.rst'],
        'hci/cmd': ['*.txt', '*.rst'],
        'hci/cmd/cmd_opcodes': ['*.txt', '*.rst'],
        'hci/cmd/cmd_parser': ['*.txt', '*.rst'],
        'hci/cmd/cmd_base_packet': ['*.txt', '*.rst'],
        'hci/cmd/cmds': ['*.txt', '*.rst'],
        'hci/cmd/cmds/commands': ['*.txt', '*.rst'],
        'hci/cmd/cmds/commands/commands': ['*.txt', '*.rst'],   
    },
    author='Himanshu',
    author_email='himanshuj0304@gmail.com',

)