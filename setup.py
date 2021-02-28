import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="palazzetti_sdk_local_api",
    version="1.0.10",
    author="Marco Palazzetti",
    author_email="marco.palazzetti@me.com",
    description="IoT Device Communication Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marcopal74/palazzetti_local_api",
    packages=setuptools.find_packages(),
    install_requires=[
        'palazzetti_sdk_asset_parser>=1.0.10',
        'aiohttp>=3.7.1'
    ],
    python_requires='>=3.6',
    include_package_data=True
)