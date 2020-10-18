import setuptools
from distutils.util import convert_path

DEPENDENCIES = [
    "azure-identity",
    "pkg-resources",
    "azure-mgmt-resource"
]

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="azure_python_arm_deployer", # Replace with your own username
    version="0.0.1",
    author="Rishabh Jain",
    author_email="rijain@microsoft.com",
    description="Deployer package to deploy or delete Azure resources based on ARM templates",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=DEPENDENCIES,
    package_data={
        "azure_arm_deployer":[
            "templates/*/*.*"
        ]
    }
)