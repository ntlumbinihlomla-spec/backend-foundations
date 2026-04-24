from setuptools import setup, find_packages

setup(
    name="backend-foundations",
    version="0.1.0",
    description="A professional command-line calculator tool built in Python.",
    author="Hlomla Ntlumbini",
    author_email="ntlumbinihlomla@gmail.com",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115,<1.0",
        "uvicorn>=0.30,<1.0",
        "python-multipart>=0.0.9,<1.0",
    ],
    entry_points={
        "console_scripts": [
            "calculator = calculator.app:main",
            "calculator-api = calculator.api:run",
        ]
    },
)
