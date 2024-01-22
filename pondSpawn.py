from web3 import Web3
import math
import time
import json
import os


url = 'https://ethereum-mainnet.core.chainstack.com/a951a2a9d1ec6468535add4e38ade398'
web3 = Web3(Web3.HTTPProvider(url))

if not web3.is_connected():
    raise Exception("Unable to connect to Ethereum network")
else:
    print("Connected to Ethereum network")


myWalletAddress = "myWalletAddress"
myPrivateKey = "myPrivateKey"

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
    
    while True:
        usesLeftForSpawn = miningRigContract.functions.usesLeftForSpawn().call()
        print(f"usesLeftForSpawn: {usesLeftForSpawn}")

        if usesLeftForSpawn <= 250:
            spawn_index = spawnManagerContract.functions.spawnIndex().call()
            print(f"Current spawnIndex: {spawn_index}")

            if spawn_index > lastKnownSpawnIndex:
                balance = math.floor(web3.fromWei(tokenContract.functions.balanceOf(myWalletAddress).call(), 'ether'))
                rounded_balance = web3.toWei(balance, 'ether')
                attempt = 0
                while not transaction_confirmed and attempt < max_attempts:
                    nonce = web3.eth.get_transaction_count(myWalletAddress)
                    gas_price = web3.to_wei('100' + attempt * 10, 'gwei') 
                    transaction = spawnManagerContract.functions.spawnThrough(spawn_index, rounded_balance).buildTransaction({
                        'from': myWalletAddress,
                        'chainId': 1,
                        'gas': 2000000,
                        'maxFeePerGas': gas_price,
                        'maxPriorityFeePerGas': gas_price,
                        'nonce': nonce,
                    })

                    signed_txn = web3.eth.account.sign_transaction(transaction, private_key=myPrivateKey)
                    try:
                        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                        print(f"Attempt {attempt + 1}: Transaction sent! Hash: {tx_hash.hex()}")

                        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                        if tx_receipt.status == 1:
                            print("Transaction confirmed.")
                            transaction_confirmed = True
                        else:
                            print("Transaction failed.")
                    except ValueError as e:
                        print(f"Attempt {attempt + 1}: Error during transaction: {e}")

                    attempt += 1
                    time.sleep(0.1)
                if transaction_confirmed:
                    break
        else:
            time.sleep(15)

monitor_and_execute()