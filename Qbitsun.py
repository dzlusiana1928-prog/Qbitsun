import hashlib
import json
import time
import os
import threading
import binascii
import ecdsa
from flask import Flask, jsonify, request

class BlockDAG:
    def __init__(self):
        self.dag = []
        self.transactions = [] 
        self.file_path = "koin_dag_final.json"
        self.difficulty = 5 
        self.max_supply = 6000000000 * 100000000 
        self.halving_interval = 100000 
        self.blacklist = set() # AI Sentinel Blacklist
        
        if os.path.exists(self.file_path):
            self.load_dag()
            if not self.is_chain_valid():
                print("[!] CRITICAL: Integrity Violation Detected!")
        else:
            self.create_block(proof=100, parents=['0' * 256])

    def q_hash(self, data):
        """ULTRA-SECURE SHA3-1024 BIT"""
        if isinstance(data, bytes): data = data.hex()
        encoded = json.dumps(data, sort_keys=True).encode()
        h1 = hashlib.sha3_512(encoded).hexdigest()
        h2 = hashlib.sha3_512(h1.encode()).hexdigest()
        return h1 + h2 

    def get_merkle_root(self, transactions):
        """Merkle Tree Implementation untuk validasi 100% aman"""
        if not transactions:
            return self.q_hash("empty_tx")
        hashes = [self.q_hash(tx) for tx in transactions]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            hashes = [self.q_hash(hashes[i] + hashes[i+1]) for i in range(0, len(hashes), 2)]
        return hashes[0]

    def ai_sentinel_scan(self, sender, amount, tx_count_in_pool):
        """AI Guardian: Mendeteksi Spam & Anomali Transaksi"""
        # Proteksi Spam: Jika satu alamat kirim > 50 tx di antrean
        sender_txs = [tx for tx in self.transactions if tx['sender'] == sender]
        if len(sender_txs) > 50:
            self.blacklist.add(sender)
            return False, "AI Detected Spamming: Address Blacklisted"
        
        # Proteksi Transaksi Padat: Prioritaskan volume/fee
        if tx_count_in_pool > 1000 and amount < 1000: # 0.00001 koin
            return False, "AI Protocol: Network Congested, Low Priority Rejected"
            
        return True, "Safe"

    def get_balance(self, address):
        balance = 0
        for block in self.dag:
            if block.get('miner_wallet') == address:
                balance += block['miner_income']
            for tx in block.get('transactions', []):
                if tx['sender'] == address:
                    balance -= (tx['amount'] + tx['fee'])
                if tx['recipient'] == address:
                    balance += tx['amount']
        return balance

    def verify_signature(self, public_key_hex, signature_hex, message):
        try:
            pub_key_bytes = binascii.unhexlify(public_key_hex)
            sig_bytes = binascii.unhexlify(signature_hex)
            vk = ecdsa.VerifyingKey.from_string(pub_key_bytes, curve=ecdsa.SECP256k1)
            return vk.verify(sig_bytes, message.encode())
        except:
            return False

    def is_chain_valid(self):
        for i in range(1, len(self.dag)):
            current = self.dag[i]
            # Validasi Merkle Root
            if current['merkle_root'] != self.get_merkle_root(current['transactions']):
                return False
            # Validasi Proof of Work
            base = "".join(current['parents'])
            guess = f'{base}{current["proof"]}'
            if self.q_hash(guess)[:current['difficulty']] != "0" * current['difficulty']:
                return False
        return True

    def create_block(self, proof, parents):
        # AI Logic: Ambil maksimal 500 tx terbaik jika padat
        final_txs = sorted(self.transactions, key=lambda x: x['fee'], reverse=True)[:500]
        total_fees = sum(tx.get('fee', 0) for tx in final_txs)
        
        block = {
            'index': len(self.dag) + 1,
            'timestamp': time.time(),
            'transactions': final_txs,
            'merkle_root': self.get_merkle_root(final_txs),
            'proof': proof,
            'parents': parents,
            'reward': self.get_halving_reward() if len(self.dag) > 0 else 0,
            'miner_income': (self.get_halving_reward() if len(self.dag) > 0 else 0) + total_fees,
            'miner_wallet': my_wallet,
            'difficulty': self.difficulty,
            'version': 'AI-Quantum-Sovereign-v3'
        }
        
        # Hapus tx yang sudah masuk blok dari pool
        self.transactions = [tx for tx in self.transactions if tx not in final_txs]
        self.adjust_difficulty()
        self.dag.append(block)
        self.save_dag()
        return block

    def get_halving_reward(self):
        return (50 * 100000000) >> (len(self.dag) // self.halving_interval)

    def adjust_difficulty(self):
        if len(self.dag) < 10: return
        dt = self.dag[-1]['timestamp'] - self.dag[-10]['timestamp']
        if dt < 5: self.difficulty += 1
        elif dt > 15: self.difficulty = max(1, self.difficulty - 1)

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

# --- PERBAIKAN: DOMPET DIBUAT DULUAN DI SINI ---
# JANGAN LUPA GANTI PUBLIC KEY DI BAWAH INI DENGAN PUNYAMU YANG ASLI
PUBLIC_KEY_USER = "5b393a9ec632a785c1712db492033af33dfac56a37617d70cd83373f0972" # Ganti dengan punyamu (minimal 64 karakter hex)
my_wallet = "QBIT-" + PUBLIC_KEY_USER[:20]

# --- SETELAH DOMPET ADA, BARU JALANKAN BLOCKCHAIN-NYA ---
koin_dag = BlockDAG()

def dag_miner():
    print(f"[*] AI-SENTINEL ACTIVE | WALLET: {my_wallet}")
    while True:
        try:
            num_p = min(len(koin_dag.dag), 3)
            parents = [koin_dag.q_hash(koin_dag.dag[-i]) for i in range(1, num_p + 1)]
            proof = koin_dag.proof_of_work(parents)
            new_block = koin_dag.create_block(proof, parents)
            print(f"[+] Block #{new_block['index']} | Saldo: {koin_dag.get_balance(my_wallet)/100000000:.2f} | TX: {len(new_block['transactions'])}")
            time.sleep(0.1 if len(koin_dag.transactions) > 100 else 0.5)
        except: time.sleep(1)

@app.route('/send', methods=['POST'])
def send_coin():
    v = request.get_json()
    if v['sender'] in koin_dag.blacklist:
        return jsonify({'error': 'Address blacklisted by AI Sentinel'}), 403
        
    is_safe, msg = koin_dag.ai_sentinel_scan(v['sender'], v['amount'], len(koin_dag.transactions))
    if not is_safe: return jsonify({'error': msg}), 429

    # Validasi Saldo & Signature
    if koin_dag.get_balance(v['sender']) < (v['amount'] + v['fee']) * 100000000:
        return jsonify({'error': 'Insufficient Balance'}), 400

    msg_sign = f"{v['sender']}{v['recipient']}{v['amount']}{int(time.time()/60)}" # Nonce-like time protection
    if not koin_dag.verify_signature(v['public_key'], v['signature'], msg_sign):
        return jsonify({'error': 'Invalid Signature'}), 401

    koin_dag.transactions.append({
        'sender': v['sender'], 'recipient': v['recipient'],
        'amount': int(v['amount'] * 100000000), 'fee': int(v['fee'] * 100000000),
        'timestamp': time.time()
    })
    return jsonify({'message': 'Transaction secured by AI & queued'}), 201

if __name__ == '__main__':
    threading.Thread(target=dag_miner, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
