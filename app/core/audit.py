import hashlib
import json
import os
import time

class AuditLogger:
    def __init__(self, log_file: str = "audit_log.jsonl"):
        self.log_file = os.path.join(os.getcwd(), log_file)
        self.genesis_hash = "0" * 64
        self._ensure_genesis()

    def _ensure_genesis(self):
        """Ensures the log file exists and has the genesis entry."""
        if not os.path.exists(self.log_file) or os.path.getsize(self.log_file) == 0:
            genesis_entry = {
                "timestamp": time.time(),
                "action": "GENESIS",
                "role": "SYSTEM",
                "tool": "N/A",
                "kwargs_hash": "N/A",
                "outcome": "SUCCESS",
                "prev_hash": self.genesis_hash
            }
            # Calculate hash of genesis
            entry_str = json.dumps(genesis_entry, sort_keys=True)
            genesis_entry["hash"] = hashlib.sha256(entry_str.encode()).hexdigest()
            
            with open(self.log_file, "w") as f:
                f.write(json.dumps(genesis_entry) + "\n")

    def _get_last_hash(self) -> str:
        """Reads the last hash from the file. Re-seeds genesis if file is missing."""
        self._ensure_genesis()
        last_line = None
        with open(self.log_file, "r") as f:
            for line in f:
                last_line = line
        if last_line:
            try:
                return json.loads(last_line).get("hash", self.genesis_hash)
            except json.JSONDecodeError:
                pass
        return self.genesis_hash

    def log_action(self, action: str, role: str, tool: str, kwargs: dict, outcome: str):
        """
        Logs an action cryptographically.
        Kwargs are hashed to prevent sensitive data leaks in the log.
        """
        prev_hash = self._get_last_hash()
        
        # Redact kwargs by hashing their JSON representation
        kwargs_str = json.dumps(kwargs, sort_keys=True)
        kwargs_hash = hashlib.sha256(kwargs_str.encode()).hexdigest()
        
        entry = {
            "timestamp": time.time(),
            "action": action,
            "role": role,
            "tool": tool,
            "kwargs_hash": kwargs_hash,
            "outcome": outcome,
            "prev_hash": prev_hash
        }
        
        # Calculate current hash over the strict JSON representation WITHOUT the 'hash' key
        entry_str = json.dumps(entry, sort_keys=True)
        entry["hash"] = hashlib.sha256(entry_str.encode()).hexdigest()
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
        return entry["hash"]

    def verify_chain(self) -> tuple[bool, int]:
        """
        Verifies the cryptographic integrity of the entire log.
        Returns (is_valid, failing_index).
        """
        if not os.path.exists(self.log_file):
            return True, -1
            
        with open(self.log_file, "r") as f:
            lines = f.readlines()
            
        if not lines:
            return True, -1
            
        expected_prev = self.genesis_hash
        
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False, i
                
            stored_hash = entry.pop("hash", None)
            stored_prev = entry.get("prev_hash")
            
            # 1. Verify chain continuity
            if i == 0:
                if stored_prev != self.genesis_hash:
                    return False, i
            else:
                if stored_prev != expected_prev:
                    return False, i
                    
            # 2. Verify payload integrity
            entry_str = json.dumps(entry, sort_keys=True)
            recalculated_hash = hashlib.sha256(entry_str.encode()).hexdigest()
            
            if recalculated_hash != stored_hash:
                return False, i
                
            expected_prev = stored_hash
            
        return True, -1
