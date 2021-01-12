import setuptools
import unasync

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="palazzetti_sdk_local_api",
    version="1.0.3",
    author="Marco Palazzetti",
    author_email="marco.palazzetti@me.com",
    description="IoT Device Communication Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marcopal74/palazzetti_local_api",
    cmdclass={
        'build_py': unasync.cmdclass_build_py(rules=[
            unasync.Rule(
                fromdir="/palazzetti_sdk_local_api/",
                todir="/palazzetti_sdk_local_api_sync/",
                additional_replacements={
                    "Palazzetti": "SyncPalazzetti",
                    "PalComm": "SyncPalComm",
                    "PalDiscovery": "SyncPalDiscovery"
                }
            )
        ])
    },
    packages=setuptools.find_packages(),
    install_requires=[
        'palazzetti_sdk_asset_parser==1.0.7',
        'aiohttp==3.7.3'
    ],
    python_requires='>=3.6',
    include_package_data=True
)