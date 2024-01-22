from eth_account.signers.local import LocalAccount
from web3 import Web3, HTTPProvider
from flashbots import flashbot
from eth_account.account import Account
import math, time, json

url = 'https://ethereum-mainnet.core.chainstack.com/a951a2a9d1ec6468535add4e38ade398'
web3 = Web3(Web3.HTTPProvider(url))

if not web3.is_connected():
    raise Exception("Unable to connect to Ethereum network")
else:
    print("Connected to Ethereum network")

ETH_SIGNER_KEY = ''
ETH_ACCOUNT_SIGNATURE: LocalAccount = Account.from_key(ETH_SIGNER_KEY)

flashbots_provider = flashbot.FlashbotsProvider(web3, sign_with=ETH_ACCOUNT_SIGNATURE, flashbots_url="https://relay.flashbots.net")

ETH_MY_WALLET_PRIVATE_KEY = ''

with open('miningRigABI.json') as f:
    miningRigABI = json.load(f)

with open('spawnManagerABI.json') as f:
    spawnManagerABI = json.load(f)

with open('erc20ABI.json') as f:
    erc20ABI = json.load(f)

miningRigContractAddress = web3.to_checksum_address('0x2D50efbc3690b6D0Ea0B179C18F016ae9031c00a') # MiningRigV3

miningRigContract = web3.eth.contract(address=miningRigContractAddress, abi=miningRigABI)

spawnManagerContractAddress = web3.to_checksum_address('0xCc57c9F7Ae5419Cfb6FE24fBD126b00C979E946C') # SpawnManagerV2

spawnManagerContract = web3.eth.contract(address=spawnManagerContractAddress, abi=spawnManagerABI)

tokenContractAddress = web3.to_checksum_address('0x423f4e6138E475D85CF7Ea071AC92097Ed631eea')

tokenContract = web3.eth.contract(address=tokenContractAddress, abi=erc20ABI)


def monitor_and_execute():
    lastKnownSpawnIndex = 3
    max_attempts = 500
    transaction_confirmed = False
    
    while True:
        usesLeftForSpawn = miningRigContract.functions.usesLeftForSpawn().call()
        print(f"usesLeftForSpawn: {usesLeftForSpawn}")

        if usesLeftForSpawn <= 250:
            spawn_index = spawnManagerContract.functions.spawnIndex().call()
            print(f"Current spawnIndex: {spawn_index}")

            if spawn_index > lastKnownSpawnIndex:
                balance = math.floor(web3.fromWei(tokenContract.functions.balanceOf(ETH_MY_WALLET_PRIVATE_KEY.address).call(), 'ether'))
                rounded_balance = web3.toWei(balance, 'ether')
                attempt = 0

                while not transaction_confirmed and attempt < max_attempts:
                    nonce = web3.eth.get_transaction_count(ETH_MY_WALLET_PRIVATE_KEY.address)
                    gas_price = web3.toWei(100 + attempt * 10, 'gwei') 
                    transaction = spawnManagerContract.functions.spawnThrough(spawn_index, rounded_balance).buildTransaction({
                        'from': ETH_MY_WALLET_PRIVATE_KEY.address,
                        'chainId': 1,
                        'gas': 2000000,
                        'maxFeePerGas': gas_price,
                        'maxPriorityFeePerGas': gas_price / 2,
                        'nonce': nonce,
                    })

                    signed_txn = web3.eth.account.sign_transaction(transaction, private_key=ETH_MY_WALLET_PRIVATE_KEY)
                    
                    flashbots_bundle = [
                        {"signed_transaction": signed_txn.rawTransaction}
                    ]
                    
                    block_number = web3.eth.block_number
                    
                    send_result = flashbots_provider.send_bundle(
                        bundle=flashbots_bundle,
                        target_block_number=block_number + 1
                    )
                    
                    if send_result:
                        print("Flashbots bundle sent")
                        try:
                            send_result.wait()
                            receipts = send_result.receipts()
                            if receipts:
                                print("Transaction confirmed in Flashbots bundle")
                                transaction_confirmed = True
                            else:
                                print("Transaction failed or was not included")
                        except Exception as e:
                            print(f"Error with Flashbots bundle: {e}")
                    else:
                        print("Failed to send Flashbots bundle")
                    
                    if transaction_confirmed:
                        break
                    else:
                        attempt += 1
                        time.sleep(10)
            else:
                time.sleep(2)
        else:
            time.sleep(15)

monitor_and_execute()