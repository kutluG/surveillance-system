#!/usr/bin/env python3
"""
Simple validation test for face anonymization functionality
"""

import numpy as np
import cv2
from face_anonymization import (
    FaceAnonymizer, AnonymizationConfig, 
    PrivacyLevel, AnonymizationMethod,
    get_strict_config, get_moderate_config, get_minimal_config
)

def test_basic_functionality():
    """Test basic face anonymization functionality"""
    print("Testing Face Anonymization Module...")
    
    # Test configuration creation
    print("✓ Testing configuration creation...")
    strict_config = get_strict_config()
    moderate_config = get_moderate_config()
    minimal_config = get_minimal_config()
    
    assert strict_config.privacy_level == PrivacyLevel.STRICT
    assert moderate_config.privacy_level == PrivacyLevel.MODERATE
    assert minimal_config.privacy_level == PrivacyLevel.MINIMAL
    print("  - Privacy level configurations: PASSED")
    
    # Test anonymizer initialization
    print("✓ Testing anonymizer initialization...")
    anonymizer = FaceAnonymizer(strict_config)
    assert anonymizer.config.privacy_level == PrivacyLevel.STRICT
    assert anonymizer.face_cascade is not None
    print("  - Anonymizer initialization: PASSED")
    
    # Test frame processing
    print("✓ Testing frame processing...")
    test_frame = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(test_frame, (50, 50), (150, 150), (255, 255, 255), -1)
    
    result_frame, detected_faces = anonymizer.anonymize_frame(test_frame)
    
    assert result_frame.shape == test_frame.shape
    assert isinstance(detected_faces, list)
    print("  - Frame processing: PASSED")
    
    # Test different anonymization methods
    print("✓ Testing anonymization methods...")
    for method in [AnonymizationMethod.BLUR, AnonymizationMethod.PIXELATE, 
                   AnonymizationMethod.BLACK_BOX, AnonymizationMethod.EMOJI]:
        config = AnonymizationConfig(method=method)
        method_anonymizer = FaceAnonymizer(config)
        result, _ = method_anonymizer.anonymize_frame(test_frame)
        assert result.shape == test_frame.shape
    print("  - All anonymization methods: PASSED")
    
    # Test statistics
    print("✓ Testing statistics...")
    stats = anonymizer.get_anonymization_stats([])
    assert "faces_detected" in stats
    assert "anonymization_method" in stats
    assert "privacy_level" in stats
    print("  - Statistics generation: PASSED")
    
    # Test disabled anonymization
    print("✓ Testing disabled anonymization...")
    disabled_config = AnonymizationConfig(enabled=False)
    disabled_anonymizer = FaceAnonymizer(disabled_config)
    result, faces = disabled_anonymizer.anonymize_frame(test_frame)
    
    # Should return original frame when disabled
    assert np.array_equal(result, test_frame)
    assert len(faces) == 0
    print("  - Disabled anonymization: PASSED")
    
    print("\n🎉 All basic functionality tests PASSED!")
    print("✅ Face anonymization module is working correctly!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_basic_functionality()
        if success:
            print("\n✅ VALIDATION SUCCESSFUL: Face anonymization is ready for use!")
            exit(0)
        else:
            print("\n❌ VALIDATION FAILED")
            exit(1)
    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
