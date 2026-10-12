from setuptools import find_packages, setup

package_name = 'lab10'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mxet_ta',
    maintainer_email='mxet_ta@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            "color_sensor = lab10.color_node:main",
            "Section50X = lab10.Section50X.ur_controller:main",
            "Section501 = lab10.Section501.ur_controller:main",
            "Section502 = lab10.Section502.ur_controller:main",
            "Section503 = lab10.Section503.ur_controller:main",
            "Section504 = lab10.Section504.ur_controller:main",
            "Section505 = lab10.Section505.ur_controller:main",
            "Section506 = lab10.Section506.ur_controller:main",
            "Section507 = lab10.Section507.ur_controller:main",
        ],
    },
)
