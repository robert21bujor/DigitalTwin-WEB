"""
Setup script for Agent Communication Infrastructure
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="agent-comms",
    version="1.0.0",
    author="Agent Communication Team",
    description="Production-ready agent-to-agent communication infrastructure",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "memory": [
            "google-api-python-client>=2.0.0",
            "google-auth>=2.0.0",
            "qdrant-client>=1.0.0",
        ],
        "ai": [
            "openai>=1.0.0",
            "tiktoken>=0.5.0",
        ],
        "data": [
            "numpy>=1.24.0",
            "pandas>=2.0.0",
        ],
        "web": [
            "fastapi>=0.104.0",
            "uvicorn>=0.23.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.11.0",
            "pytest-cov>=4.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "agent-demo=AgentComms.demo:main",
            "agent-test=AgentComms.test_integration:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 