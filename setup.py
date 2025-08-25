from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="browserbud",
    version="1.0.0",
    author="Srinath Srinivasan",
    description="AI-powered learning companion that transforms web browsing into organized knowledge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/srinath1510/BrowserBud",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Education",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pocketflow",
        "beautifulsoup4>=4.12.0",
        "html2text>=2020.1.16",
        "python-dateutil>=2.8.2",
        "validators>=0.20.0",
        "urllib3>=1.26.0",
        "requests>=2.28.0",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "anthropic>=0.8.0",
        "python-dotenv>=1.0.0",
        "neo4j==5.14.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
            "coverage>=7.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "browserbud=main:main",
            "browserbud-api=start_fastapi:main",
            "browserbud-test=test_pipeline_no_api:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml", "*.json"],
        "config": ["*.py"],
        "nodes": ["*.py"],
        "api": ["*.py"],
    },
    keywords="ai, learning, knowledge-management, notion, neo4j, llm, anthropic",
    project_urls={
        "Bug Reports": "https://github.com/srinath1510/BrowserBud/issues",
        "Source": "https://github.com/srinath1510/BrowserBud",
        "Documentation": "https://github.com/srinath1510/BrowserBud#readme",
    },
)