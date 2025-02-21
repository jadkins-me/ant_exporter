"""
===================================================================================================
Title : watcher.py

Description : Chain Watcher and Prometheus Instance

Copyright - Jadkins-Me

This Code/Software is licensed to you under GNU AFFERO GENERAL PUBLIC LICENSE (GPL), Version 3
Unless required by applicable law or agreed to in writing, the Code/Software distributed
under the GPL Licence is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. Please review the Licences for the specific language governing
permissions and limitations relating to use of the Code/Software.

===================================================================================================
"""

import time
import sys
import logging
from web3 import Web3
from prometheus_client import Gauge, CollectorRegistry, CONTENT_TYPE_LATEST
from prometheus_client.core import REGISTRY
from flask import Flask, Response, json
from waitress import serve
from threading import Thread

class WatchItem:
    def __init__(self, token, wallet, decimals, metric, labels):
        self.token = token
        self.wallet = wallet
        self.decimals = decimals
        self.metric = metric
        self.labels = labels

class Watcher:
    def __init__(self):
        self.geth = {}
        self.items = {}
        self.metrics = {}  # Initialize metrics dictionary
        self.contract_abi  = {}
        #Constants
        self.const_chainrefresh = 1800   # 30 minutes

    def add_geth(self, name, url):
        try:
            eth = Web3(Web3.HTTPProvider(url))
            self.geth[name] = eth
        except Exception as e:
            logging.error(f"Error adding geth client for {name}: {str(e)}")
            return False
        return True

    def set_prometheus(self, config) -> bool:
        for name, url in config.chains.items():
            if not self.add_geth(name, url):
                logging.error(f"Failed to add chain '{name}' with URL '{url}'")
                return False

        tokens_map = {chain: {token.symbol: token for token in tokens} for chain, tokens in config.tokens.items()}

        for wallet in config.wallets:
            for chain, symbols in wallet.track_for.items():
                if chain not in config.chains:
                    logging.error(f"Unknown chain '{chain}' in wallet '{wallet.address}'")
                    return False
                for symbol in symbols:
                    token = tokens_map[chain].get(symbol)
                    if not token:
                        logging.error(f"Unknown token '{symbol}' for chain '{chain}' in wallet '{wallet.address}'")
                        return False
                    labels = wallet.labels.copy()
                    labels.update({
                        'symbol': symbol,
                        'name': wallet.name,
                        'wallet': wallet.address,
                        'token': token.contract,
                        'chain': chain
                    })
                    
                    # Create a unique identifier for the metric
                    metric_key = tuple(sorted(labels.items()))
                    if metric_key not in self.metrics:
                        # Ensure that label names are unique
                        unique_labelnames = list(set(labels.keys()))
                        name_value = dict(metric_key)['name']
                                                     
                        metric_name = f'token_balance_{name_value}_{symbol}_{chain}'  # Make metric name unique
           
                        metric = Gauge(name=metric_name, documentation='Token Balance', labelnames=unique_labelnames, registry=REGISTRY)
                        self.metrics[metric_key] = metric
                    else:
                        metric = self.metrics[metric_key]

                    item = WatchItem(token.contract, wallet.address, token.decimal, metric, labels)
                    self.items.setdefault(chain, []).append(item)

        return True


    def start(self, listen: str, host: str = "0.0.0.0"):
        
        # Load the contract ABI from a file - need rework ##JAD this is wrong place
        try:
            with open('./abi.json') as abi_file:
                self.contract_abi = json.load(abi_file)
        except Exception as e:
            logging.error(f"Error: Unable to load default ERC-20 Token ABI contract definition file.")
            return False

        registry = CollectorRegistry()

        for chain in self.items:
            for item in self.items[chain]:
                if item.metric not in registry._names_to_collectors:
                    registry.register(item.metric)

        app = Flask(__name__)

        @app.route('/metrics')
        def metrics():
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

        def run_server():
            app.run(host=host, port=int(listen))

        def update_tokens():
            while True:
                for chain, items in self.items.items():
                    def update_chain(c):
                        for item in self.items[c]:
                            balance = self.get_token_balance(c, item)
                            item.metric.labels(**item.labels).set(balance) 
                    update_chain(chain)

                time.sleep(self.const_chainrefresh) #query every xx to not overload the RPC endpoint

        # Start the update tokens loop before the webserver, else we could try and serve null values
        update_thread = Thread(target=update_tokens)
        update_thread.start() 

         # Start the HTTP server using Waitress
        try:
            serve(app, host=host, port=int(listen))
        except Exception as e:
            logging.error("Unable to launch Web enpoint ? is the address and port avaialble ?")
            return False
        finally:
            return True   

    def stop(self):
        pass

    def get_token_balance(self, chain, item):
        #hopefully handle gas, as it's not bound to contract address
        if item.token == "0x0000000000000000000000000000000000000000" or item.token == "" or item.token=="0":
            return self.get_gas_balance(chain, item)

        try:
            eth = self.geth[chain]
            contract = eth.eth.contract(address=item.token, abi=self.contract_abi)
            #need to handle ERC Checksum - nasty, need rework this #JAD
            balance = contract.functions.balanceOf(eth.to_checksum_address(item.wallet)).call()
            return self.convert_float(balance, item.decimals)
        except Exception as e:
            logging.error(f"ERROR: Can't get token balance for chain='{chain}', wallet='{item.wallet}', token='{item.token}': {str(e)}")
            return -1

    def get_gas_balance(self, chain, item):
        try:
            eth = self.geth[chain]
            #need to handle ERC Checksum - nasty, need rework this #JAD
            balance = eth.eth.get_balance(eth.to_checksum_address(item.wallet))
            return self.convert_float(balance, item.decimals)
        except Exception as e:
            logging.error(f"ERROR: Can't get gas balance for chain='{chain}', wallet='{item.wallet}', token='{item.token}': {str(e)}")
            return -1

    @staticmethod
    def convert_float(balance, decimals):
        return balance / (10 ** decimals)