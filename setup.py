from setuptools import setup, find_packages

setup(
    name="savior",
    version="2.0.1",
    description="Automatic backups for developers who break things",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Noah Edery",
    author_email="noah@redacted.com",
    url="https://github.com/hollowsolve/Savior",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "watchdog>=2.1.0",
        "colorama>=0.4.4",
        "python-dateutil>=2.8.2",
        "psutil>=5.9.0",
        "tqdm>=4.65.0",
    ],
    entry_points={
        "console_scripts": [
            "savior=savior.cli_refactored:cli",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)