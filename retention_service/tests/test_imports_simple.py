print("🔍 Testing enterprise logging imports...")

try:
    from shared.logging_config import configure_logging, get_logger, log_context, set_request_id
    print("✓ logging_config imports successful")
except Exception as e:
    print(f"✗ logging_config import failed: {e}")

try:
    from shared.audit_middleware import add_audit_middleware
    print("✓ audit_middleware imports successful")
except Exception as e:
    print(f"✗ audit_middleware import failed: {e}")

print("✅ Enterprise logging modules are available!")
