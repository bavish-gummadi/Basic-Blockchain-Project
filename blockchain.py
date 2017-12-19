import hashlib
import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse
import requests

class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []

        #Creation of the genesis block
        self.new_block(previous_hash = 1, proof = 100)

        #Utilize set for nodes to ensure there are no duplicate nodes
        self.nodes = set()

    def register_node(self, address):
        '''
        Adds a new node to our list of nodes
        :param address: <str> the address of the new node. Ex: 'http://192.168.0.5:5000'
        :return: None
        '''

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)


    #enters a new block into the Blockchain
    def new_block(self, proof, previous_hash = None):
        '''
        This is a bare bones block of a blockchain
        :param proof: <int> the proof given by the proof of work algorithm
        :param previous_hash: (optional) <str> the hash value of the previous block
        :return: <dict> The new block
        '''

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        #resets the list of transactions
        self.current_transactions = []
        #adds the block to the chain
        self.chain.append(block)
        return block

        pass
    #enters a new transaction into the list of transactions
    def new_transaction(self, sender, recepient, amount):
        '''
        :param sender: <str> This is the address of the sender
        :param recepient: <str> This is the adress of the recipient
        :param amount: <int> This is the amount transferred
        :return: <int> Returns the number of the index of the block in the chain
        '''

        #Creates a dictionary within the current transactions list with one transaction
        self.current_transactions.append(
            {'sender': sender,
             'recepient': recepient,
             'amount': amount},
        )
        return self.last_block['index'] + 1
        pass

    @staticmethod

    #hashes a block
    def hash(block):
        '''
        Creates a SHA-256 hash of the block
        :param block: <dict> Block that will be hashed
        :return: <str> the hash
        '''

        #sorts and hashes the block, must be sorted for consistent hashing
        block_string = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(block_string).hexdigest()
        pass

    @property

    #returns the last block in the chain
    def last_block(self):
        return self.chain[-1]
        pass

    def proof_of_work(self, last_proof):
        '''
        The proof of work algorithm will be quite simple:
        -find a number b such that hash(ab) has four leading zeroes
        -a is the previous proof and b is the new proof we are trying to find
        :param last_proof: <int> The last proof
        :return: <int>
        '''
        #We iterate until we find a value for proof that statisfies the algorithm.
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        '''
        This validates the proof and checks whether or not the hash of last_proof with proof
        contains four leading zeroes
        :param last_proof: <int> the last proof
        :param proof: <int> the current proof (the one we are trying to find)
        :return: <bool> Return True if the hash of the two has four leading zeroes, False if not
        '''
        #hashes last_proof with proof
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    def valid_chain(self, chain):
        '''
        This will determine if a given blockchain is valid
        :param chain: <list> The blockchain we are checking
        :return: <bool> True if the blockchain is valid, false if not
        '''

        last_block = chain[0]
        index = 1

        while index < len(chain):
            block = chain[index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            #check if the hash of the last block matches
            if block['previous_hash'] != self.hash(last_block):
                return False

            #verify that the proof of work matches as well
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            #Incrementations
            last_block = block
            index += 1

        return True

    def resolve_conflicts(self):
        '''
        This is the conflict resolution algorithm and it will be quite simple for the purposes of this program
        This will resolve conflicts by replacing our chain with the longest chain in the network
        :return: <bool> return True if the chain was replaces, False if not
        '''

        neighbors = self.nodes
        new_chain = None

        #max_length initially set to the current length of the chain to ensure that the chain we find is always longer
        max_length = len(self.chain)

        #find and verify all the chains from the nodes in our network
        for node in neighbors:
            #gets the chain of the current node in neighbors
            response = requests.get(f'http//{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                #Now we want to verify the chain and see if it has a higher length than our max_length
                if length > max_length and self.valid_chain():
                    max_length = length
                    new_chain = chain

        #Replace our chain with a new, longer, and valid chain, if we found one
        if new_chain:
            self.chain = new_chain
            return True
        return False

#Instantiate our Node
app = Flask(__name__)

#Generate a globally unique address for our node
#uuid4 generates a random ID, each uuid has a different method of generating addresses
node_identifier = str(uuid4()).replace('-', '')

blockchain = Blockchain()

#The following are the methods associated with the Flask
@app.route('/mine', methods = ['GET'])
def mine():
    #We must run the proof of work algorithm to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    #We must receive some reward for finding the proof
    #The sender will be identified as 0 because we are mining an entirely new coin
    blockchain.new_transaction(
        sender = 0,
        recepient = node_identifier,
        amount = 1,
    )

    #Create the new block and add it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    response = {
        'message': "New Block added to chain",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods = ['POST'])
def new_transactions():
    #parses values from request and stores in request
    values = request.get_json()

    #Checks to see whether the values contain all required for transaction
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    #Adds a new transaction to our list of transactions in blockchain, new_transaction() returns an index
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods = ['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }

    #JSONify converts from HTML to JSON
    return jsonify(response), 200

if __name__ == '__main__':
    #runs the server on port 5000
    app.run(host = '0.0.0.0', port = 5000)

