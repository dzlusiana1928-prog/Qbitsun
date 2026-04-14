import hashlib
import json
import time
import os
import threading
import binascii
import ecdsa
import requests 
from flask import Flask, jsonify, request

# --- SECURITY & CRYPTO UTILS ---
class SecurityUtils:
    @staticmethod
    def q_hash(data):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, sort_keys=True)
        if isinstance(data, str):
            data = data.encode()
        h1 = hashlib.sha3_512(data).hexdigest()
        h2 = hashlib.sha3_512(h1.encode()).hexdigest()
        return h1 + h2

    @staticmethod
    def generate_address(public_key_hex):
        raw_hash = hashlib.sha3_256(public_key_hex.encode()).hexdigest()
        base_addr = raw_hash[:20].upper()
        checksum = hashlib.sha256(base_addr.encode()).hexdigest()[:4].upper()
        return f"QBIT-{base_addr}-{checksum}"

    @staticmethod
    def validate_address(address):
        try:
            parts = address.split("-")
            if len(parts) != 3 or parts[0] != "QBIT": return False
            recalc_checksum = hashlib.sha256(parts[1].encode()).hexdigest()[:4].upper()
            return recalc_checksum == parts[2]
        except: return False

# --- BLOCKCHAIN CORE ---
class BlockDAG:
    def __init__(self, miner_address):
        self.dag = []
        self.tx_pool = []
        self.peers = set()
        self.file_path = "koin_dag_final.json"
        self.difficulty = 6
        self.target_block_time = 15
        self.max_supply = 6000000000 * 10**8
        self.lock = threading.Lock()
        self.account_nonces = {}
        self.pending_spent = {}
        self.rate_limits = {}
        self.miner_address = miner_address # Simpan address miner di sini
        
        if os.path.exists(self.file_path):
            self.load_dag()
            if not self.full_audit():
                print("[!] AUDIT FAILED: Chain Corrupt. Resync required.")
                self.dag = []
                self.create_genesis()
        else:
            self.create_genesis()

    def create_genesis(self):
        # Genesis block menggunakan 128 karakter nol sesuai spesifikasi awalmu
        self.create_block(proof=100, parents=['0' * 128])

    def full_audit(self):
        try:
            for i, block in enumerate(self.dag):
                if i == 0: continue
                if block['parents'][0] != SecurityUtils.q_hash(self.dag[i-1]): return False
                if block.get('merkle_root') != self.get_merkle_root(block['transactions']): return False
                check_str = "".join(block['parents']) + str(block['proof'])
                if SecurityUtils.q_hash(check_str)[:block['difficulty']] != "0" * block['difficulty']:
                    return False
            return True
        except KeyError: return False # Menangani jika ada key yang hilang di JSON lama

    def verify_transaction(self, tx_data, is_mining=False):
        try:
            if tx_data['amount'] <= 0 or tx_data['fee'] < 0: return False
            if not SecurityUtils.validate_address(tx_data['sender']): return False
            
            tx_content = f"{tx_data['sender']}{tx_data['recipient']}{tx_data['amount']}{tx_data['nonce']}{tx_data['fee']}"
            tx_hash = SecurityUtils.q_hash(tx_content)
            vk = ecdsa.VerifyingKey.from_string(binascii.unhexlify(tx_data['public_key']), curve=ecdsa.SECP256k1)
            vk.verify(binascii.unhexlify(tx_data['signature']), tx_hash.encode())
            
            balance = self.get_balance(tx_data['sender'], include_pending=(not is_mining))
            if balance < (tx_data['amount'] + tx_data['fee']): return False
            
            return True
        except: return False

    def get_merkle_root(self, txs):
        if not txs: return SecurityUtils.q_hash("empty")
        hashes = [tx['txid'] for tx in txs]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0: hashes.append(hashes[-1])
            hashes = [SecurityUtils.q_hash(hashes[i] + hashes[i+1]) for i in range(0, len(hashes), 2)]
        return hashes[0]

    def create_block(self, proof, parents):
        with self.lock:
            valid_txs = []
            for tx in sorted(self.tx_pool, key=lambda x: x['fee'], reverse=True)[:100]:
                if self.verify_transaction(tx, is_mining=True):
                    valid_txs.append(tx)
            
            total_fees = sum(tx['fee'] for tx in valid_txs)
            reward = (50 * 10**8) >> (len(self.dag) // 100000)
            
            block = {
                'index': len(self.dag) + 1,
                'timestamp': time.time(),
                'transactions': valid_txs,
                'merkle_root': self.get_merkle_root(valid_txs),
                'proof': proof,
                'parents': parents,
                'miner_income': reward + total_fees,
                'miner_wallet': self.miner_address, # Gunakan variabel dari self
                'difficulty': self.difficulty,
                'hash': "" 
            }
            block['hash'] = SecurityUtils.q_hash(block)
            
            self.tx_pool = [tx for tx in self.tx_pool if tx not in valid_txs]
            for tx in valid_txs:
                self.pending_spent[tx['sender']] = max(0, self.pending_spent.get(tx['sender'], 0) - (tx['amount'] + tx['fee']))
            
            self.dag.append(block)
            self.save_dag()
            return block

    def get_balance(self, address, include_pending=True):
        balance = 0
        for block in self.dag:
            if block.get('miner_wallet') == address: balance += block.get('miner_income', 0)
            for tx in block['transactions']:
                if tx['sender'] == address: balance -= (tx['amount'] + tx['fee'])
                if tx['recipient'] == address: balance += tx['amount']
        if include_pending:
            balance -= self.pending_spent.get(address, 0)
        return balance

    def save_dag(self):
        temp_path = self.file_path + ".tmp"
        with open(temp_path, 'w') as f:
            json.dump(self.dag, f, indent=4)
        os.replace(temp_path, self.file_path)

    def load_dag(self):
        with open(self.file_path, 'r') as f:
            self.dag = json.load(f)

# --- WEB SERVER & CONFIG ---
app = Flask(__name__)

# FIX URUTAN: Tentukan address dulu baru buat objek koin_dag
PUBLIC_KEY_USER = "5b393a9ec632a785c1712db492033af33dfac56a37617d70cd83373f0972"
my_address = SecurityUtils.generate_address(PUBLIC_KEY_USER)

# Masukkan my_address ke dalam parameter BlockDAG
koin_dag = BlockDAG(miner_address=my_address)

@app.route('/send', methods=['POST'])
def send_coin():
    ip = request.remote_addr
    if time.time() - koin_dag.rate_limits.get(ip, 0) < 1:
        return jsonify({'error': 'Rate limit exceeded'}), 429
    koin_dag.rate_limits[ip] = time.time()

    data = request.get_json()
    if len(json.dumps(data)) > 5000:
        return jsonify({'error': 'Transaction size too large'}), 400

    if not koin_dag.verify_transaction(data):
        return jsonify({'error': 'Verification failed'}), 400

    tx_id = SecurityUtils.q_hash(f"{data['sender']}{data['nonce']}{time.time()}")
    data['txid'] = tx_id
    
    with koin_dag.lock:
        koin_dag.tx_pool.append(data)
        koin_dag.pending_spent[data['sender']] = koin_dag.pending_spent.get(data['sender'], 0) + int((data['amount'] + data['fee']) * 10**8)
    
    return jsonify({'message': 'TX Accepted', 'txid': tx_id}), 201

@app.route('/peers/sync', methods=['GET'])
def sync_chain():
    return jsonify({'chain': koin_dag.dag, 'length': len(koin_dag.dag)})

def miner_thread():
    print(f"[*] CORE ONLINE | ADDR: {my_address}")
    while True:
        num_p = min(len(koin_dag.dag), 3)
        # Ambil hash dari blok sebelumnya
        parents = [koin_dag.dag[-i].get('hash', SecurityUtils.q_hash(koin_dag.dag[-i])) for i in range(1, num_p + 1)]
        
        target = "0" * koin_dag.difficulty
        proof = 0
        base = "".join(parents)
        while True:
            if SecurityUtils.q_hash(base + str(proof))[:koin_dag.difficulty] == target:
                break
            proof += 1
            if proof % 500000 == 0: time.sleep(0.01)
            
        koin_dag.create_block(proof, parents)
        print(f"[+] Block #{len(koin_dag.dag)} Mined!")

if __name__ == '__main__':
    threading.Thread(target=miner_thread, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
