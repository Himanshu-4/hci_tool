# -*- coding: utf-8 -*-

import sys
import os
# from pathlib import Path

# The base path is very important here as application depens on it for multiple things 
BASE_PATH = None

# include the BASE level directory into the sys 

# Determine the base path (project root directory)
if BASE_PATH is None:
    BASE_PATH = os.environ.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
    
# Add the base path to sys.path if not already present
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

sys._BASE_PATH = BASE_PATH

# create app_data folder and also append its path

# Create the app_data directory if it doesn't exist and append its path as _APP_DATA_PATH
APP_DATA_PATH = os.path.join(BASE_PATH, "app_data")
if not os.path.exists(APP_DATA_PATH):
    os.makedirs(APP_DATA_PATH, exist_ok=True)

if APP_DATA_PATH not in sys.path:
    sys.path.insert(1, APP_DATA_PATH)

sys._APP_DATA_PATH = APP_DATA_PATH


# ============================================================================================================
# ----------------------------  Application config YAML file is syscfg.yml -----------------------------------
# ============================================================================================================

APP_CONFIG_FILE = 'syscfg.yml'
sys._APP_CONFIG_PATH = APP_CONFIG_FILE




# after init the sys path we can process the rest of the modules
""" please note that this module is initied before other modules as this will run the 
 YML parser after which there are some other modules that depednds on the parsed config
 file for their static initialization (like logger which have their confi deps on yml files )
"""
from utils.yaml_cfg_parser import global_setting_parser
from ui.main.app import start_app




def main():
    # global_setting_parser().configure_from_yaml("logger.yml")
    # Set the environment variable  
    # os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(os.path.dirname(__file__), "platforms")
    start_app()
    # test_file_handler()

if __name__ == "__main__":
    # Check if the script is being run directly
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        # Optionally, you can log the error or handle it as needed
        # For example, you could write to a log file or display a message box