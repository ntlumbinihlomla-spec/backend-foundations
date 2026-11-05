from setuptools import setup, find_packages

setup(
    name="backend-foundations",
    version="0.4.0",
    description="A Python automation toolkit with CLI utilities and FastAPI services.",
    author="Hlomla Ntlumbini",
    author_email="ntlumbinihlomla@gmail.com",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115,<1.0",
        "uvicorn>=0.30,<1.0",
        "python-multipart>=0.0.9,<1.0",
        "stripe>=13.0,<14.0",
        "SQLAlchemy>=2.0,<3.0",
        "psycopg[binary]>=3.1,<4.0",
        "reportlab>=4.0,<5.0",
        "httpx>=0.28,<1.0",
    ],
    entry_points={
        "console_scripts": [
            "calculator = calculator.app:main",
            "task-api = task_api.server:main",
            "calculator-api = calculator.api:run",
        ]
    },
)
