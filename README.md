# veracryptmountpy
Python script to mount a Veracrypt volume via the command line in both Linux and Windows.

I personally use this script to share an Veracrypt-encrypted ext4 drive between Fedora and Windows OSes. It will likely be just as useful for users of a Linux or Windows machine, regardless of if it is single- or dual-boot.

This Python script is inspired by Aheno Barbus's PowerShell script on SourceForge:
(See https://sourceforge.net/p/veracrypt/discussion/technical/thread/027f5f92bf/).


## Limitations
- If running this script in Windows, your Veracrypt partition **_must_** be on a _separate drive_ from your Windows partition! This is a known limitation of WSL 2 as of the writing of this README.
- Python cannot run external applications interactively. Thus, if errors occur after Veracrypt's command-line takes over, they may not be displayed.


## Usage
### Prerequisites
- Python 3 installed
- Veracrypt installed

If using Windows:
- WSL 2 installed
- Linux OS installed in WSL
- Veracrypt installed _within_ WSL Linux OS

### Linux
1. Copy "mount_veracrypt_volume.py" and "veracrypt_volume_settings.example.ini" to the directory "$HOME/bin/".
2. Rename "veracrypt_volume_settings.example.ini" to "veracrypt_volume_settings.ini".
3. Set `DRIVE_PARTITION` in "veracrypt_volume_settings.ini" to the _Linux_ name of the encrypted partition.
4. (Optional) Modify other settings within "veracrypt_volume_settings.ini" as desired.
5. (Optional) Copy "mount_veracrypt_volume.desktop" to your Desktop folder.
6a. If using the desktop icon, double click the desktop icon.
6b. Otherwise, run `sudo -i python $HOME/bin/mount_veracrypt_volume.py -c $HOME/bin/veracrypt_volume_settings.ini` in the terminal.
7. Follow the prompts to enter your administrative password and partition password (if not set in the settings file).
8. The encrypted Veracrypt volume should be mounted!

### Windows
1. Copy "mount_veracrypt_volume.py" and "veracrypt_volume_settings.example.ini" to the directory "%USERPROFILE%\bin\".
2. Rename "veracrypt_volume_settings.example.ini" to "veracrypt_volume_settings.ini".
3. Set `DRIVE_PARTITION` in "veracrypt_volume_settings.ini" to the _Linux_ name of the encrypted partition.
4. (Optional) Modify other settings within "veracrypt_volume_settings.ini" as desired.
5a. Run `python %USERPROFILE%\bin\mount_veracrypt_volume.py -c veracrypt_volume_settings.ini` in a command prompt _with administrative permissions_.
5b. Create a shortcut _with administrative permissions_ that runs the above command (replacing `python` with the path to your python 3 executable), and double-click that shortcut instead.
6. Follow the prompts to enter your administrative password and partition password (if not set in the settings file).
7. The encrypted Veracrypt volume should be mounted!


## Troubleshooting
In general, the script will attempt to give you sensible error messages if there are errors, and should prompt for any missing data it needs to decrypt the partition.

### Finding Drive Partition Name
If you run the script with `DRIVE_PARTITION` unset, it should display a list of drive partitions it finds.

If that fails, check out https://sourceforge.net/p/veracrypt/discussion/technical/thread/027f5f92bf/ for more detailed instructions of how to list the Linux drive partition names.
