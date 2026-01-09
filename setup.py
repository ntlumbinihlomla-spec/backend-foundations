from setuptools import setup, find_packages

setup(
    name="backend-foundations",
    version="0.1.0",
    description="A professional command-line calculator tool built in Python.",
    author="Hlomla Ntlumbini",
    author_email="ntlumbinihlomla@gmail.com",
    packages=find_packages(where='calculator'),  # only include `calculator` folder
    entry_points={
        "console_scripts": [
            "calculator = calculator.app:main",
        ]
    },
)
