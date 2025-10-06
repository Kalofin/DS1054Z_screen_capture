@echo off
rem ensure pyinstaller is available
pip install pyinstaller

rem generate an executable, put all transient files in build
# feel free to put UPX in the path to reduce the executable size
pyinstaller --onefile --specpath build --distpath . --workpath build OscScreenGrabLAN.py

rem remove all transient files - this slows down subsequent builds
rd /s /q build
