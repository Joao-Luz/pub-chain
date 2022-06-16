# pub-chain

This is a simple implementation of a block-chain-like system using a publisher/subscriber structure in python. It uses the [mosquitto](https://mosquitto.org/man/mosquitto_pub-1.html) broker to handle the messages.

## How it works

The `pub-chain` is divided in two main programs: `pub-chain-server` and `pub-chain-client`.

### Server

The server keeps the transactions in a table and publishes the challenges in the broker (under the `tpp/challenge` topic) and listens to the seed submissions (under `tpp/seed`). When a seed is submitted, it validates the seed, updates the transaction table and publishes the winner in the broker (under the `tpp/results` topic).

### Client

The client listens to the challenges from the broker and tries to mine the transaction. It does so in parallel, bruteforcing its way through all possible seeds. When the client finds a valid seed, it publishes to the `tpp/seed` topic. When a message comes through the `tpp/results` topic, it checks if it's about the current transaction being processed and, if thats the case, terminates the processes related to that transaction.

## How to run

For the server, run:

    python pub_chain_server.py

For the client, run:

    python pub_chain_client.py

## Explanation video

None (yet ;])