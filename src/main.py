"""
===================================================================================================
Title : main.py

Description : Entry point

Copyright - Jadkins-Me

This Code/Software is licensed to you under GNU AFFERO GENERAL PUBLIC LICENSE (GPL), Version 3
Unless required by applicable law or agreed to in writing, the Code/Software distributed
under the GPL Licence is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. Please review the Licences for the specific language governing
permissions and limitations relating to use of the Code/Software.

===================================================================================================
"""
import os
import signal
import sys
import logging
import config
import version
from dotenv import load_dotenv
from watcher import Watcher

logging.basicConfig(level=logging.INFO)

def main():
    
    logging.info(f"git: {version.get_git_commit_hash()} name: {version.BUILD_NAME} version: {version.BUILD_VERSION}")

    #load environment
    load_dotenv()

    #pass any changes
    listen = os.getenv("LISTEN") or "8080"              # default port we listen on for prometheus scrape
    config_file = os.getenv("CONFIG_FILE") or "./config.yml"    # config file containing token info
    host = os.getenv("HOST") or "0.0.0.0"       # host IP to bind to, by default 0.0.0.0 is all/* ipv4

    #load the configuration
    appconfig = config.get_config(config_file)
    if not appconfig:
        logging.error("Error: can't read config file ",config_file)
        sys.exit(1)

    watcher = Watcher()
    if not watcher.set_prometheus(appconfig):
        logging.error("Error: can't enable Prometheus Metrics, is your config file valid ?")
        sys.exit(1)

    if not watcher.start(listen=listen, host=host):
        logging.error("Error: unable to start HTTP Prometheus Endpoint on port : ", listen)
        sys.exit(1)

    def signal_handler(sig, frame):
        logging.info("INFO: Received QUIT signal, exiting...")
        sys.exit(0)

    #register termination signals
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logging.info("Prometheus Endpoint Started : OK")

    #now wait.....
    signal.pause()

if __name__ == "__main__":
    main()