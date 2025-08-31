from web3 import Web3
from web3.exceptions import TransactionNotFound
from eth_account import Account
from eth_account.messages import encode_defunct
from datetime import datetime, timezone
from colorama import Fore, Style
import asyncio, secrets, json, os, pytz

wib = pytz.timezone('Asia/Jakarta')

class PharosSingleSwap:
    def __init__(self):
        # Contract & RPC
        self.RPC_URL = "https://api.zan.top/node/v1/pharos/testnet/54b49326c9f44b6e8730dc5dd4348421"
        self.WPHRS_CONTRACT_ADDRESS = "0x76aaaDA469D23216bE5f7C596fA25F282Ff9b364"
        self.USDT_CONTRACT_ADDRESS = "0xD4071393f8716661958F766DF660033b3d35fD29"
        self.SWAP_ROUTER_ADDRESS = "0x1A4DE519154Ae51200b0Ad7c90F7faC75547888a"

        # ERC20 ABI
        self.ERC20_CONTRACT_ABI = json.loads('''[
            {"type":"function","name":"balanceOf","stateMutability":"view","inputs":[{"name":"address","type":"address"}],"outputs":[{"name":"","type":"uint256"}]},
            {"type":"function","name":"allowance","stateMutability":"view","inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"outputs":[{"name":"","type":"uint256"}]},
            {"type":"function","name":"approve","stateMutability":"nonpayable","inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"outputs":[{"name":"","type":"bool"}]},
            {"type":"function","name":"decimals","stateMutability":"view","inputs":[],"outputs":[{"name":"","type":"uint8"}]}
        ]''')

        self.used_nonce = {}
        self.wphrs_amount = 0.0  # user input
        self.tx_count = 0

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}", flush=True
        )

    async def get_web3(self):
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        web3.eth.get_block_number()  # Test connection
        return web3

    def generate_swap_option(self):
        # Single PHRS -> USDT
        from_token = self.WPHRS_CONTRACT_ADDRESS
        to_token = self.USDT_CONTRACT_ADDRESS
        from_ticker = "PHRS"
        to_ticker = "USDT"
        swap_amount = self.wphrs_amount
        return from_token, to_token, from_ticker, to_ticker, swap_amount

    async def approve_token_if_needed(self, web3, account, token_addr, amount):
        token_contract = web3.eth.contract(address=token_addr, abi=self.ERC20_CONTRACT_ABI)
        allowance = token_contract.functions.allowance(account.address, self.SWAP_ROUTER_ADDRESS).call()
        if allowance >= int(amount * (10 ** 18)):
            self.log("Token already approved.")
            return True
        tx = token_contract.functions.approve(self.SWAP_ROUTER_ADDRESS, int(amount * (10 ** 18))).build_transaction({
            "from": account.address,
            "nonce": self.used_nonce[account.address],
            "gas": 100000,
            "gasPrice": web3.to_wei(5, 'gwei'),
        })
        signed = account.sign_transaction(tx)
        tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)
        self.used_nonce[account.address] += 1
        self.log(f"Approved {amount} PHRS for swap. TX: {tx_hash.hex()}")
        return True

    async def execute_swap(self, web3, account):
        from_token, to_token, from_ticker, to_ticker, swap_amount = self.generate_swap_option()
        await self.approve_token_if_needed(web3, account, from_token, swap_amount)
        # Simplified: send PHRS -> USDT using router (pseudo)
        tx = {
            "from": account.address,
            "to": self.SWAP_ROUTER_ADDRESS,
            "value": int(swap_amount * (10 ** 18)),
            "nonce": self.used_nonce[account.address],
            "gas": 200000,
            "gasPrice": web3.to_wei(5, 'gwei'),
            "chainId": 688688
        }
        signed = account.sign_transaction(tx)
        tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        self.used_nonce[account.address] += 1
        self.tx_count += 1
        self.log(f"Swap executed: {swap_amount} PHRS -> USDT. TX: {tx_hash.hex()}")
        return receipt

    async def run(self, private_key):
        account = Account.from_key(private_key)
        web3 = await self.get_web3()
        if account.address not in self.used_nonce:
            self.used_nonce[account.address] = web3.eth.get_transaction_count(account.address)
        await self.execute_swap(web3, account)


if __name__ == "__main__":
    bot = PharosSingleSwap()
    # input PHRS amount
    bot.wphrs_amount = float(input("Enter PHRS amount to swap (e.g., 0.2-0.5): "))
    private_key = input("Enter your wallet private key: ")
    asyncio.run(bot.run(private_key))
