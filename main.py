# -*- coding: utf-8 -*-

from utils.yaml_config_parser import global_setting_parser
from ui.main.app import start_app

def main():
    global_setting_parser().configure_from_yaml("logger.yml")
    # Set the environment variable  
    # os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(os.path.dirname(__file__), "platforms")
    # start_app()
    # test_logger()
    # test_file_handler()

if __name__ == "__main__":
    # Check if the script is being run directly
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        # Optionally, you can log the error or handle it as needed
        # For example, you could write to a log file or display a message box