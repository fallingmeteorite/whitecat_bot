from .logging import *

# Initialize logger configuration with a specified log directory
log_directory = f"{os.getcwd()}/log"  # Replace this path with your desired log storage path
configure_logger(log_directory)