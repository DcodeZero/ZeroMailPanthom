from setuptools import setup, find_packages

setup(
    name="email_campaign",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.1',
        'python-dateutil>=2.8.2',
    ],
)