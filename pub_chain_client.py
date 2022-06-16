import paho.mqtt.client as mqtt
from bitstring import BitArray
from multiprocessing import Process, Value
import hashlib
import os
import json
import time

class PubChainClient:
    def publish_seed(self, client, transaction_id : int, seed : str) -> None:
        msg = json.dumps({
            "client_id": self.id,
            "transaction_id": transaction_id,
            "seed": seed
        })

        # print(f'Publishing seed {seed}...')
        client.publish('ppd/seed', msg)

    def parallel_mine(self, n : int, step : int, mask : bytes, transaction_id : int) -> None:
        id = n
        while True:
            seed = n.to_bytes((n.bit_length()+7)//8, 'big')
            hash_object = hashlib.sha1(seed)
            hashed = hash_object.digest()

            xor = bytes([h & m for h,m in zip(hashed, mask)])

            if not bool.from_bytes(xor, "big"):
                client = mqtt.Client(f'pub-chain-client-{self.id}-{id}')
                client.connect(self.broker_address)
                print(f'{seed.hex()} - {hashed}')
                self.publish_seed(client, transaction_id, seed.hex())
                break
            
            n += step

    def mine(self, transaction_id : int, challenge : int) -> None:

        # the challenge is the number of '0's that must exist at the start of the hash
        mask = BitArray('0b' + '1'*challenge).tobytes()
        mask += (20-len(mask))*b'\00'

        print(f'Mining for transaction {transaction_id} (challenge = {challenge})...')

        thread_count = os.cpu_count()
        self.mining_processes[transaction_id] = []

        for n in range(thread_count):
            p = Process(target=self.parallel_mine, args=(n, thread_count, mask, transaction_id))
            p.start()
            self.mining_processes[transaction_id].append(p)

    def receive_challenge(client : mqtt.Client, userdata : dict, message) -> None:
        cli = userdata['cli']

        payload = json.loads(message.payload)
        transaction_id = payload['transaction_id']
        challenge = payload['challenge']

        cli.mine(transaction_id, challenge)

    def receive_result(client : mqtt.Client, userdata : dict, message) -> None:
        cli = userdata['cli']

        payload = json.loads(message.payload)
        transaction_id = payload['transaction_id']

        for p in cli.mining_processes[transaction_id]:
            p.terminate()
        
        del cli.mining_processes[transaction_id]

    def loop(self):
        self.client.loop_forever()

    def __init__(self, broker_address : str) -> None:
        self.id = 19

        self.broker_address = broker_address
        self.client = mqtt.Client(f'pub-chain-client-{self.id}', userdata={'cli': self})
        self.client.connect(broker_address)
        self.client.subscribe('ppd/challenge')
        self.client.subscribe('ppd/result')

        self.client.message_callback_add('ppd/challenge', PubChainClient.receive_challenge)
        self.client.message_callback_add('ppd/result', PubChainClient.receive_result)

        self.mining_processes = {}


pub_chain_client = PubChainClient('127.0.0.1')
pub_chain_client.loop()


# def on_message(client, userdata, message):
#     print("received message: " ,str(message.payload.decode("utf-8")))

# # mqttBroker = "127.0.0.1"
# mqttBroker = "broker.emqx.io"

# client = mqtt.Client("Node_3")
# client.connect(mqttBroker)

# client.loop_start()

# client.subscribe("rsv/temp")
# client.subscribe("rsv/light")
# client.on_message=on_message

# time.sleep(30000)
# client.loop_stop()