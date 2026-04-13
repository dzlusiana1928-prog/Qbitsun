import hashlib
import json
import time
import os
import threading
from flask import Flask, jsonify, request

class BlockDAG:
    def __init__(self):
        self.dag = []
        self.transactions = [] 
        self.file_path = "koin_dag_final.json"
        self.difficulty = 5 
        self.max_supply = 6000000000 * 100000000 # 6 Miliar Koin (Satoshi unit)
        self.halving_interval = 100000 # Halving setiap 100rb blok
        
        if os.path.exists(self.file_path):
            self.load_dag()
        else:
            self.create_block(proof=100, parents=['0' * 256])

    def q_hash(self, data):
        """ULTRA-SECURE SHA3-1024 BIT (DUAL LAYER)"""
        if isinstance(data, bytes): data = data.hex()
        encoded = json.dumps(data, sort_keys=True).encode()
        # Layer 1 & 2 menghasilkan total 1024-bit hash
        h1 = hashlib.sha3_512(encoded).hexdigest()
        h2 = hashlib.sha3_512(h1.encode()).hexdigest()
        return h1 + h2 

    def get_halving_reward(self):
        """Sistem Halving: Hadiah berkurang setengah setiap interval"""
        base_reward = 50 * 100000000
        halvings = len(self.dag) // self.halving_interval
        return base_reward >> halvings # Bitwise shift untuk bagi 2

    def get_reward(self):
        total_minted = sum(b['reward'] for b in self.dag)
        if total_minted >= self.max_supply:
            return 0 
        return self.get_halving_reward()

    def create_block(self, proof, parents):
        # Akumulasi Fee Transaksi untuk penambang
        total_fees = sum(tx.get('fee', 0) for tx in self.transactions)
        block_reward = self.get_reward()
        
        block = {
            'index': len(self.dag) + 1,
            'timestamp': time.time(),
            'transactions': list(self.transactions),
            'proof': proof,
            'parents': parents,
            'reward': block_reward,
            'total_fees': total_fees,
            'miner_income': block_reward + total_fees, # Pendapatan total penambang
            'difficulty': self.difficulty,
            'version': 'Quantum-1024-Final'
        }
        
        self.transactions = [] 
        self.adjust_difficulty() # Keamanan nambah otomatis kalau miner banyak
        self.dag.append(block)
        self.save_dag()
        return block

    def adjust_difficulty(self):
        """Dynamic Difficulty Adjustment (BPS Stability)"""
        if len(self.dag) < 10: return
        # Target: 10 blok harus selesai dalam 5 detik (Kaspa Speed 0.5s/block)
        waktu_nyata = self.dag[-1]['timestamp'] - self.dag[-10]['timestamp']
        if waktu_nyata < 5: 
            self.difficulty += 1 # Makin banyak orang/speed, makin sulit teka-tekinya
        elif waktu_nyata > 15:
            self.difficulty = max(1, self.difficulty - 1)

    def proof_of_work(self, last_hashes):
        proof = 0
        base = "".join(last_hashes)
        while True:
            guess = f'{base}{proof}'
            if self.q_hash(guess)[:self.difficulty] == "0" * self.difficulty:
                return proof
            proof += 1

    def save_dag(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.dag, f, indent=4)

    def load_dag(self):
        with open(self.file_path, 'r') as f:
            self.dag = json.load(f)

app = Flask(__name__)
koin_dag = BlockDAG()
my_wallet = "QU-Aset" + hashlib.sha3_256(b"dheva").hexdigest()[:20]

def dag_miner():
    print(f"[*] BIT-ASET ULTRA-QUANTUM 1024-BIT STARTED")
    print(f"[*] WALLET PENAMBANG: {my_wallet}")
    while True:
        try:
            num_p = min(len(koin_dag.dag), 3)
            parents = [koin_dag.q_hash(koin_dag.dag[-i]) for i in range(1, num_p + 1)]
            proof = koin_dag.proof_of_work(parents)
            
            new_block = koin_dag.create_block(proof, parents)
            print(f"[+] Blok #{new_block['index']} Mined! Income: {new_block['miner_income']/100000000:.8f} Koin | Diff: {new_block['difficulty']}")
            time.sleep(0.3)
        except Exception as e:
            time.sleep(1)

@app.route('/dag', methods=['GET'])
def get_dag():
    return jsonify({'chain': koin_dag.dag, 'difficulty': koin_dag.difficulty}), 200

# Endpoint untuk kirim transaksi (simulasi)
@app.route('/send', methods=['POST'])
def send_coin():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount', 'fee']
    if not all(k in values for k in required):
        return 'Missing values', 400
    
    # Masuk ke antrian transaksi
    tx_data = {
        'sender': values['sender'],
        'recipient': values['recipient'],
        'amount': int(values['amount'] * 100000000), # Ubah ke Satoshi
        'fee': int(values['fee'] * 100000000)      # Ubah ke Satoshi
    }
    koin_dag.transactions.append(tx_data)
    return jsonify({'message': 'Transaksi masuk antrian!'}), 201

if __name__ == '__main__':
    threading.Thread(target=dag_miner, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
