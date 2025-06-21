#!/usr/bin/env python3
import sys
import traceback

try:
    import enhanced_prompt_service.main
    print("✅ Main module imported successfully")
except Exception as e:
    print(f"❌ Error importing main: {e}")
    traceback.print_exc()
    sys.exit(1)
