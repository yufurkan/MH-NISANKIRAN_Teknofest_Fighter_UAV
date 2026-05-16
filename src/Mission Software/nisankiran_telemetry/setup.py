import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'nisankiran_telemetry'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='federstation',
    maintainer_email='federstation@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
   entry_points={
        'console_scripts': [
            'radar = nisankiran_telemetry.server_listener:main',
            'fake_server = nisankiran_telemetry.fake_server:main',
            'vision = nisankiran_telemetry.vision:main', 
        ],
    },

    
)
