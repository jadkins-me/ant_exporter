"""
===================================================================================================
Title : config.py

Description : Configuration and Class Defintions

Copyright - Jadkins-Me

This Code/Software is licensed to you under GNU AFFERO GENERAL PUBLIC LICENSE (GPL), Version 3
Unless required by applicable law or agreed to in writing, the Code/Software distributed
under the GPL Licence is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. Please review the Licences for the specific language governing
permissions and limitations relating to use of the Code/Software.

===================================================================================================
"""

import yaml
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
# Token Definition
class Token:
    symbol: str                         # Symbol of token i.e ETH / ANT
    contract: str = None                # Contract address for TOKEN - GAS and ETH Tokens might not have this so set to 0
    decimal: int = field(default=18)    # Default to 18 decimal places

@dataclass
class Wallet:
    name: str                           # Short name for wallet
    address: str                        # ERC Address
    track_for: Dict[str, List[str]]     # Tokens we want to check balance for
    labels: Dict[str, str]              # Labels used in Prometheus Client

@dataclass
class ConfigYAML:
    chains: Dict[str, str]
    tokens: Dict[str, List[Token]]
    wallets: List[Wallet]

def get_config(path: str) -> ConfigYAML:
    try:
        with open(path, 'r') as file:
            c = yaml.safe_load(file)
            c['tokens'] = {k: [Token(**token) for token in v] for k, v in c['tokens'].items()}
            c['wallets'] = [Wallet(**wallet) for wallet in c['wallets']]
            return ConfigYAML(**c)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None