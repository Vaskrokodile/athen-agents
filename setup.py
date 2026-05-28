from setuptools import setup, find_packages

setup(
    name="athen-agents",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "textual>=1.0.0",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.0",
        "rich>=13.7.0"
    ],
    entry_points={
        "console_scripts": [
            "athen=athen.cli:main",
        ],
    },
    author="Athen Developers",
    description="A self-learning CLI Agentic Harness",
    python_requires=">=3.8",
)
