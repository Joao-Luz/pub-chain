from random import randint, uniform
from bitstring import BitArray
import pandas as pd
import paho.mqtt.client as mqtt
import hashlib
import json

class PubChainServer:
    def new_transaction(self) -> None:
        # choose a new random challenge that hasn't been chosen yet
        old_challenges = [t['challenge'] for t in self.transactions]
        new_challenge = 10 if len(old_challenges) == 0 else old_challenges[-1]+1

        # while new_challenge in old_challenges and len(old_challenges) < 128:
        #     new_challenge = randint(1, 128)

        self.current_transaction_id += 1
        new_transaction = {'transaction_id': self.current_transaction_id, 'challenge': new_challenge, 'seed': '', 'winner': -1}
        self.transactions.append(new_transaction)
        self.publish_challenge()

    def seed_valid(challenge : int, seed : str) -> bool:
        hash_object = hashlib.sha1(bytes.fromhex(seed))
        hashed = hash_object.digest()

        # the challenge is the number of '0's that must exist at the start of the hash
        mask = BitArray('0b' + '1'*challenge).tobytes()
        mask += (20-len(mask))*b'\00'

        # do bitwise xor between mask and hashed
        return not bool.from_bytes(bytes([h & m for h,m in zip(hashed, mask)]), 'big')

    def print_transactions(self) -> None:
        print('\nTRANSACTION TABLE -------------------')
        print(pd.DataFrame.from_dict(self.transactions))
        print('-------------------------------------\n')

    def publish_challenge(self) -> None:
        transaction_id = self.current_transaction_id
        challenge = self.transactions[transaction_id]['challenge']

        # generate a json string containing the message
        msg = json.dumps({
                "transaction_id": transaction_id,
                "challenge": challenge
            })

        self.client.publish('ppd/challenge', msg)
        self.print_transactions()
    
    def publish_result(self, transaction_id : int) -> None:
        transaction = self.transactions[transaction_id]
        client_id = transaction['winner']
        seed = transaction['seed']

        msg = json.dumps({
            "transaction_id": transaction_id,
            "client_id": client_id,
            "seed": seed
        })

        self.client.publish('ppd/result', msg)
        self.print_transactions()
    
    def set_winner(self, transaction_id:  int, client_id : int, seed : str) -> None:
        self.transactions[transaction_id]['winner'] = client_id
        self.transactions[transaction_id]['seed'] = seed
        self.publish_result(transaction_id)
        self.new_transaction()

    def receive_seed(client : mqtt.Client, userdata : dict, message) -> None:
        server = userdata['server']

        payload = json.loads(message.payload)
        client_id = payload['client_id']
        transaction_id = payload['transaction_id']
        seed = payload['seed']
        challenge = server.transactions[transaction_id]['challenge']

        if PubChainServer.seed_valid(challenge, seed) and server.transactions[transaction_id]['winner'] == -1:
            server.set_winner(transaction_id, client_id, seed)

    def loop(self) -> None:
        self.client.loop_forever()

    def __init__(self, broker_address : str) -> None:
        self.broker_address = broker_address
        self.client = mqtt.Client('pub-chain-server', userdata={'server': self})
        self.client.connect(broker_address)
        self.client.subscribe('ppd/seed')
        self.client.message_callback_add('ppd/seed', PubChainServer.receive_seed)

        self.transactions = []
        self.current_transaction_id = -1
        self.new_transaction()

pub_chain_server = PubChainServer('127.0.0.1')
pub_chain_server.loop()