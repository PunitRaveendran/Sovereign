from app.core.audit import AuditLogger

if __name__ == "__main__":
    logger = AuditLogger()
    print(f"Current Root Hash: {logger._get_last_hash()}\n")
    
    print("Verifying Cryptographic Chain...")
    is_valid, bad_index = logger.verify_chain()
    
    if is_valid:
        print("[OK] SUCCESS: The audit log is cryptographically verified and untampered.")
    else:
        print(f"[FAIL] TAMPER DETECTED: Chain broken at entry index {bad_index}!")
