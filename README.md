# DS1054Z_screen_capture
'OscScreenGrabLAN.py' is a Python script that captures
whatever is displayed on the screen of a Rigol DS1000Z series oscilloscope.

It can save data as a WYSIWYG (What You See Is What You Get) picture of the oscilloscope screen, copy it to the Windows clipboard, or as a text file in CSV (Comma Separated Values) format.

To achieve this, SCPI (Standard Commands for Programmable Instruments) are sent from the computer to the oscilloscope, using the LXI (LAN-based eXtensions for Instrumentation) protocol over a Telnet connection.
The computer and the oscilloscope are connected together by a LAN (Local Area Network).
No USB (Universal Serial Bus), no VISA (Virtual Instrument Software Architecture), no IVI (Interchangeable Virtual Instrument) and no Rigol drivers are required.

Tested with Windows 11, Python 3.12, pillow and Rigol DS1104Z.
Not tested with Linux (yet!).


# User Manual:

This program captures either the waveform data or an image of the whole screen of a Rigol DS1000Z series oscilloscope. 
Waveform data is stored as CSV. Screenshots can be saved as PNG or BMP, or copied to the clipboard. Clipboard currently works on Windows only.
The output filename contains the oscilloscope's identification and a timestamp.

    The program is using LXI protocol, so the computer must have LAN connection with the oscilloscope.
    USB and/or GPIB connections are not used by this software.
    No VISA, IVI or Rigol drivers are needed.
	
# Installation:
1. Install Python 3.12
1. Clone this repository and go to the directory it was clones to.
1. Generate a virtual environment  
    ```python -m venv .venv```
1. Activate the virtual environment  
    - Windows: ```.venv\Scripts\activate.bat```
    - Others: ```.venv/bin/activate```
1. Install required packages in a virtual environment  
    ```pip install -r requirements.txt```


# Running the script
1. Connect the oscilloscope to the LAN
1. In the Command Prompt, change the directory (CD) to the path were 'OscScreenGrabLAN.py' and activate the virtual environment
1. Run the OscScreenGrabLAN.py in the Command Prompt
   - To take a screenshot and copy it to the clipboard:  
       ```python OscScreenGrabLAN.py -i <Oscilloscpe FQDN or IP address>``` 
   - To take a screenshot and save it as a PNG file in the captures subdirectory:  
       ```python OscScreenGrabLAN.py -f png -i <Oscilloscpe FQDN or IP address>``` 
   - To download the data of all visible waveforms and save it to a CSV in the captures subdirectory:  
       ```python OscScreenGrabLAN.py -f csv -i <Oscilloscpe FQDN or IP address>``` 
	
# Generate a stand-alone executable
1. In the Command Prompt, change the directory to the clone of this repository and activate the virtual environment
1. Run ```generate_executable.bat``` on Windows, or ```./generate_executable.sh``` on other systems
1. A redistributable executable should now be available in the repositories' directory.
    