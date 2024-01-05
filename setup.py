from setuptools import setup, find_packages
import re

with open("loguru/__init__.py", "r") as file:
    regex_version = r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]'
    version = re.search(regex_version, file.read(), re.MULTILINE).group(1)


def get_requirements():
    """Build the requirements list for this project"""
    requirements_list = []

    with open("requirements.txt", 'r') as reqs:
        for install in reqs:
            requirements_list.append(install.strip())

    return requirements_list


setup(
    name='twine_to_json',
    version=version,
    description='make json from twine story',
    author='Vaclav_V',
    packages=find_packages(),
    install_requires=get_requirements(),
)
