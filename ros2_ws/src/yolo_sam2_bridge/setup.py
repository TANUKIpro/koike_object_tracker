from setuptools import setup

package_name = 'yolo_sam2_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/yolo_sam2.launch.py']),
        ('share/' + package_name, ['params.yaml', 'README.md']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='dev',
    maintainer_email='dev@example.com',
    description='YOLOv11 + SAM2 bridge node.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'yolo_sam2_node = yolo_sam2_bridge.yolo_sam2_node:main',
        ],
    },
)
