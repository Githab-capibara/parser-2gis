import pathlib
import re
import sys

from setuptools import Command, setup

PACKAGE_NAME = "parser_2gis"
ROOT_DIR = pathlib.Path(__file__).parent
VERSION_PATH = ROOT_DIR / PACKAGE_NAME / "version.py"
README_PATH = ROOT_DIR / "README.md"

long_description = README_PATH.read_text(encoding="utf-8")
long_description_content_type = "text/markdown"

match = re.search(
    r'^version\s*=\s*[\'"](?P<version>.+?)[\'"]', VERSION_PATH.read_text(encoding="utf-8"), re.M
)
assert match
version = match.group("version")


class BuildStandaloneCommand(Command):
    """Собственная команда для сборки автономного приложения."""

    description = "Сборка автономного приложения с помощью PyInstaller"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import os
        import shutil
        import subprocess

        try:
            # Имя файла дистрибутива
            dist_filename = "Parser2GIS"

            # Команда сборки (только для Linux)
            build_cmd = [
                "pyinstaller",
                "--clean",
                "--onefile",
                "--windowed",
                "-n",
                dist_filename,
                "--icon",
                "parser_2gis/data/images/icon.png",
                "--add-data",
                f"parser_2gis/data{os.pathsep}parser_2gis/data",
                "parser-2gis.py",
            ]

            print("Running command: %s" % " ".join(build_cmd), file=sys.stderr)
            subprocess.check_call(build_cmd)
        finally:
            # Очистка
            shutil.rmtree(ROOT_DIR / "build", ignore_errors=True)
            try:
                os.remove(ROOT_DIR / f"{dist_filename}.spec")
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    setup(
        name="parser-2gis",
        version=version,
        description="Парсер сайта 2GIS",
        long_description=long_description,
        long_description_content_type=long_description_content_type,
        author="Andy Trofimov",
        author_email="interlark@gmail.com",
        packages=[PACKAGE_NAME],
        include_package_data=True,
        python_requires=">=3.10",
        keywords="parser scraper 2gis",
        url="https://github.com/Githab-capibara/parser-2gis",
        project_urls={
            "Documentation": "https://github.com/Githab-capibara/parser-2gis/wiki",
            "GitHub": "https://github.com/Githab-capibara/parser-2gis",
            "Changelog": "https://github.com/Githab-capibara/parser-2gis/blob/main/CHANGELOG.md",
        },
        install_requires=[
            "pychrome>=0.2.4",
            "pydantic>=2.0.0,<3",
            "psutil>=5.4.8",
            "requests>=2.32.4",
            "xlsxwriter>=3.0.5",
            "rich>=13.0.0",
            "tqdm>=4.66.3",
            "jinja2>=3.1.6",
            "pillow>=10.3.0",
            "urllib3>=2.6.3",
            "setuptools>=78.1.1",
            "pyyaml>=6.0",
            "ratelimit>=2.2.1",
        ],
        extras_require={
            "dev": [
                "pytest>=6.2,<8",
                "tox>=4.0",
                "pre-commit>=2.6",
                "wheel>=0.46.2",
                "pyinstaller>=6.6.0",
            ],
            "tui": ["textual>=0.50.0"],
            "all": [
                "textual>=0.50.0",
                "pytest>=6.2,<8",
                "tox>=4.0",
                "pre-commit>=2.6",
                "wheel>=0.46.2",
                "pyinstaller>=6.6.0",
            ],
        },
        classifiers=[
            "Topic :: Internet",
            "Topic :: Utilities",
            "Operating System :: POSIX :: Linux",
            "Environment :: X11 Applications",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Natural Language :: Russian",
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        ],
        license="LGPLv3+",
        entry_points={"console_scripts": ["parser-2gis = parser_2gis:main"]},
        cmdclass={"build_standalone": BuildStandaloneCommand},
    )
