#!/usr/bin/env python3

"""
Mounts a Veracrypt volume with a Linux filesystem in Windows or Linux.

Volume settings are loaded via a .ini config file or via the command-line.

Since Python does not support subprocess interaction, Veracrypt is launched separately.

Inspired by Aheno Barbus's PowerShell script on SourceForge:
(See https://sourceforge.net/p/veracrypt/discussion/technical/thread/027f5f92bf/)
"""

import argparse
from configparser import ConfigParser
from getpass import getpass
import logging
from pathlib import Path
from shutil import which
from subprocess import CompletedProcess, PIPE, Popen, run
from sys import argv, platform
from typing import Dict, List

if platform == "linux":
    from os import getuid
if platform == "win32":
    from ctypes import windll


class AdminError(Exception):
    """Raised when this script is run without administrative rights."""


class ConfigError(Exception):
    """Raised when this script finds an error with its configuration."""


def build_physical_drive_name(physical_drive_number: int) -> str:
    """Builds a WSL physical drive name from a given drive number."""
    return f"PHYSICALDRIVE{physical_drive_number}"


def build_veracrypt_cmdline(config_data: Dict[str, str]) -> List[str]:
    """Builds command-line call for veracrypt on both Linux and Windows."""
    slot_num: str = config_data.get("slot_num", "1")
    cmdline = [
        "veracrypt",
        "-t",  # Run interactively to prompt for any missing settings
        f"--keyfiles={config_data.get('keyfile_path')}",
        f"--password={config_data.get('volume_password')}",
        f"--pim={config_data.get('personal_iterations_multiplier')}",
        f"--protect-hidden={config_data.get('using_hidden_partition')}",
        f"--slot={slot_num}",
        f"{config_data.get('drive_partition')}",
    ]

    if config_data.getboolean("use_truecrypt"):
        cmdline.insert(3, "-tc")

    if platform == "win32":
        drive_num: int = config_data.get("physical_drive_num")
        wsl_exe: str = config_data.get("wsl_exe")
        mount_point_windows: Path = Path(
            "/mnt", "wsl", build_physical_drive_name(drive_num)
        )

        cmdline.insert(0, wsl_exe)
        cmdline.insert(
            3, "-m=nokernelcrypto"
        )  # WSL doesn't support hardware cryptography
        cmdline.append(mount_point_windows.as_posix())

    if platform == "linux":
        mount_point_linux: Path = Path("/media", f"veracrypt{slot_num}")
        cmdline.append(mount_point_linux.as_posix())

    return cmdline


def have_admin_rights() -> bool:
    """Returns whether this script is running with administrative rights."""
    if platform == "linux":
        return getuid() == 0
    if platform == "win32":
        return windll.shell32.IsUserAnAdmin() != 0
    return False


def load_config_file(config_path: Path) -> Dict[str, str]:
    """
    Loads the config file at the given path, returning the configuration data.
    The data returned will be contained in a name:value dictionary.
    If the config file's sections are incorrect, a ConfigError will be raised.
    """
    VERACRYPT_SECTION_NAME: str = "Veracrypt"

    config = ConfigParser()
    config.read(str(config_path))
    if not VERACRYPT_SECTION_NAME in config:
        raise ConfigError(
            f"Section [{VERACRYPT_SECTION_NAME}] not found in config file!"
        )

    return config[VERACRYPT_SECTION_NAME]


def mount_physical_drive(drive_num: int, wsl_exe: str) -> CompletedProcess[bytes]:
    """
    Mounts the physical drive at the given number using WSL.
    Returns the CompletedProcess results of the mount.
    """
    return run(
        [
            wsl_exe,
            "--mount",
            f"\\\\.\\{build_physical_drive_name(drive_num)}",
            "--bare",
        ],
        stdout=PIPE,
        stderr=PIPE,
    )


def pause_for_input() -> None:
    """Pauses the script for users to read by waiting for user input."""
    input("Press any key to exit...")


def validate_config_data(config_data: Dict[str, str]) -> None:
    """
    Validates the given configuration data.
    If the data fails validation, a ConfigError will be raised for the first failure.
    """
    DRIVE_PARTITION_CONFIG_NAME: str = "drive_partition"
    DRIVE_NUM_CONFIG_NAME: str = "physical_drive_num"
    WSL_EXE_CONFIG_NAME: str = "wsl_exe"
    WSL_ROOT_CONFIG_NAME: str = "wsl_root"

    if platform == "win32":
        if not config_data.get(WSL_ROOT_CONFIG_NAME):
            raise ConfigError(
                f"""{WSL_ROOT_CONFIG_NAME.upper()} is not set!
Please set it to WSL's root share path for the current distribution [e.g. '\\\\wsl.localhost\\Ubuntu']."""
            )

        config_data[WSL_EXE_CONFIG_NAME] = config_data.get(WSL_EXE_CONFIG_NAME, "wsl")
        wsl_path: str = config_data[WSL_EXE_CONFIG_NAME]
        if not which(wsl_path):
            raise ConfigError(
                f"""Unable to find Windows Subsystem for Linux executable at '{wsl_path}'!
Please make sure WSL is installed at the path set for {WSL_EXE_CONFIG_NAME.upper()} in the config file."""
            )

        if not config_data.get(DRIVE_NUM_CONFIG_NAME):
            wmic_result = run(["wmic.exe", "diskdrive", "list", "brief"], stdout=PIPE)
            wmic_drive_list = wmic_result.stdout.decode()
            raise ConfigError(
                f"""{DRIVE_NUM_CONFIG_NAME.upper()} is not set!
Please set it to the DeviceID for the drive containing the Veracrypt volume. [e.g. '0' for 'PHYSICALDRIVE0'].
Currently detected physical drives:
{wmic_drive_list}"""
            )

    if not config_data.get(DRIVE_PARTITION_CONFIG_NAME):
        lsblk_cmdline: List[str] = ["lsblk"]

        # In Windows, we need to mount the drive first and prepend WSL to the command
        if platform == "win32":
            wsl_path: str = config_data[WSL_EXE_CONFIG_NAME]
            mount_physical_drive(config_data[DRIVE_NUM_CONFIG_NAME], wsl_path)
            lsblk_cmdline.insert(0, wsl_path)

        lsblk_result = run(lsblk_cmdline, stdout=PIPE)
        partition_list = lsblk_result.stdout.decode()
        raise ConfigError(
            f"""{DRIVE_PARTITION_CONFIG_NAME.upper()} is not set!
Please set it to the Linux partition of the Veracrypt volume [e.g. '/dev/sda1'].
Currently detected Linux partitions:
{partition_list}"""
        )

    if not config_data.get("volume_password"):
        config_data["volume_password"] = getpass(prompt="Enter Volume Password: ")


def main(config_path: Path) -> int:
    """
    Contains the main functionality of this script.
    """
    log_formatter = logging.Formatter("%(levelname)s: %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    logger = logging.getLogger()
    logger.addHandler(stream_handler)
    logger.setLevel(logging.INFO)

    try:
        if not have_admin_rights():
            raise AdminError

        logger.info(f"Loading configuration from config file '{config_path.name}'...")
        config_data: Dict[str, str] = load_config_file(config_path)
        for config_name, config_value in config_data.items():
            config_value = (
                "******" if (config_name == "volume_password") else config_value
            )
            logger.debug(f"{config_name}={config_value}")
        validate_config_data(config_data)

        if platform == "win32":
            drive_num: int = config_data.get("physical_drive_num")
            mount_point_windows: Path = Path(
                config_data.get("wsl_root"),
                "mnt",
                "wsl",
                build_physical_drive_name(drive_num),
            )

            if not mount_point_windows.exists():
                logger.info(f"Creating mount point at '{mount_point_windows}'...")
                Path.mkdir(mount_point_windows)

            logger.info(f"Mounting Veracrypt drive at drive number '{drive_num}'...")
            mount_physical_drive(drive_num, config_data.get("wsl_exe"))

        veracrypt_cmdline = build_veracrypt_cmdline(config_data)
        # NOTE: DO NOT log or print command line args
        # The password may be in plaintext on the command line!
        veracrypt_cmdline_len = len(veracrypt_cmdline)
        drive_partition: str = veracrypt_cmdline[veracrypt_cmdline_len - 2]
        mount_point: str = veracrypt_cmdline[veracrypt_cmdline_len - 1]
        logger.info(
            f"Mounting Veracrypt volume '{drive_partition}' to '{mount_point}'..."
        )
        veracrypt_cmdline_str = " ".join(veracrypt_cmdline)

        # Since Python doesn't support subprocess interaction, launch in a separate shell.
        veracrypt_process = Popen(veracrypt_cmdline_str, shell=True)
        # Wait for the mounting to finish, since on Linux closing early might stop the mount.
        veracrypt_process.wait()
        return 0

    except AdminError:
        logger.error(f"This script requires administrative rights to mount volumes.")
        logger.error(f"Please re-run this script as an administrator or as root.")
        pause_for_input()
        return -1

    except ConfigError as config_error:
        logger.error("An error has been detected in the configuration file:")
        logger.error(f"{config_error}")
        pause_for_input()
        return -2


def parse_arguments(arguments: List[str]) -> argparse.Namespace:
    """
    Parses command-line arguments into namespace data.
    """
    parser = argparse.ArgumentParser(
        description="Mounts a Veracrypt volume with a Linux filesystem in Windows or Linux."
    )
    parser.add_argument(
        "--config",
        "-c",
        dest="config_path",
        required=True,
        type=Path,
        help="Path to a .ini configuration file for this script.",
    )

    return parser.parse_args(arguments)


if __name__ == "__main__":
    exit(main(**vars(parse_arguments(argv[1:]))))
