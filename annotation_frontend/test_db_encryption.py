#!/usr/bin/env python3
"""
Integration test for database encryption functionality.
Tests that the EncryptedType and EncryptedJSONType work correctly with SQLAlchemy.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_encryption():
    """Test database field encryption integration."""
    print("🗄️  Database Encryption Integration Test")
    print("=" * 50)
    
    try:
        from models import AnnotationExample, EncryptedType, EncryptedJSONType, AnnotationStatus
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from datetime import datetime
        
        # Create in-memory database for testing
        engine = create_engine("sqlite:///:memory:")
        
        # Create tables
        from models import Base
        Base.metadata.create_all(engine)
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("✅ Database and tables created successfully")
        
        # Test data
        test_data = {
            "example_id": "test_example_001",
            "camera_id": "camera_001", 
            "timestamp": datetime.now(),
            "frame_data": "base64_encoded_frame_data_here_would_be_much_longer==",
            "original_detections": [
                {"bbox": [100, 200, 300, 400], "confidence": 0.95, "class": "person"}
            ],
            "confidence_scores": {"person": 0.95, "vehicle": 0.02},
            "bbox": [100, 200, 300, 400],
            "label": "person_with_sensitive_info",
            "notes": "This person appears to be John Doe, frequently seen at this location",
            "status": AnnotationStatus.PENDING,
            "annotator_id": "annotator_001",
            "quality_score": 0.9
        }
        
        print(f"Test data prepared:")
        print(f"  - Frame data length: {len(test_data['frame_data'])} chars")
        print(f"  - Detections: {len(test_data['original_detections'])} items")
        print(f"  - Label: {test_data['label']}")
        print(f"  - Notes: {test_data['notes'][:50]}...")
        
        # Create and save example
        example = AnnotationExample(**test_data)
        session.add(example)
        session.commit()
        
        print("✅ Data saved to database (encrypted automatically)")
        
        # Retrieve the example
        retrieved = session.query(AnnotationExample).filter_by(example_id="test_example_001").first()
        
        assert retrieved is not None, "Failed to retrieve example"
        print("✅ Data retrieved from database (decrypted automatically)")
        
        # Verify data integrity
        assert retrieved.frame_data == test_data["frame_data"], "Frame data mismatch"
        assert retrieved.original_detections == test_data["original_detections"], "Detections mismatch"
        assert retrieved.confidence_scores == test_data["confidence_scores"], "Confidence scores mismatch"
        assert retrieved.bbox == test_data["bbox"], "Bbox mismatch"
        assert retrieved.label == test_data["label"], "Label mismatch"
        assert retrieved.notes == test_data["notes"], "Notes mismatch"
        
        print("✅ All encrypted fields maintain data integrity")
        
        # Test that data is actually encrypted in storage by examining raw SQL
        raw_result = session.execute(
            "SELECT frame_data, label, notes, original_detections FROM annotation_examples WHERE example_id = ?", 
            (test_data["example_id"],)
        ).fetchone()
        
        if raw_result:
            stored_frame, stored_label, stored_notes, stored_detections = raw_result
            
            # The stored values should be different from original (encrypted + base64)
            assert stored_frame != test_data["frame_data"], "Frame data not encrypted!"
            assert stored_label != test_data["label"], "Label not encrypted!"
            assert stored_notes != test_data["notes"], "Notes not encrypted!"
            
            # Should be base64-encoded strings
            import base64
            try:
                base64.b64decode(stored_frame)
                base64.b64decode(stored_label) 
                base64.b64decode(stored_notes)
                print("✅ Stored data is properly base64-encoded (encrypted)")
            except Exception as e:
                print(f"❌ Stored data encoding issue: {e}")
        
        # Test multiple records with same data (should have different encrypted values)
        example2 = AnnotationExample(
            example_id="test_example_002",
            camera_id="camera_001",
            timestamp=datetime.now(),
            frame_data=test_data["frame_data"],  # Same data
            label=test_data["label"],            # Same data
            status=AnnotationStatus.PENDING
        )
        session.add(example2)
        session.commit()
        
        # Get raw encrypted values for both records
        results = session.execute(
            "SELECT example_id, frame_data, label FROM annotation_examples ORDER BY example_id"
        ).fetchall()
        
        if len(results) >= 2:
            _, enc_frame1, enc_label1 = results[0]
            _, enc_frame2, enc_label2 = results[1]
            
            # Encrypted values should be different (due to random IV)
            assert enc_frame1 != enc_frame2, "Same plaintext should encrypt to different ciphertext!"
            assert enc_label1 != enc_label2, "Same plaintext should encrypt to different ciphertext!"
            print("✅ Same plaintext encrypts to different ciphertext (random IV working)")
        
        session.close()
        print("✅ Database encryption integration test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Database encryption test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_database_encryption()
    if success:
        print("\n🎉 All database encryption tests passed!")
        print("Your sensitive annotation data is properly encrypted in the database.")
    else:
        print("\n❌ Database encryption tests failed!")
        sys.exit(1)
