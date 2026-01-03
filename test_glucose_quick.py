"""
Quick test for Dalla Man glucose model
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the new model
from src.core.models.glucose import DallaManModel, DallaManParams

def test_glucose_model():
    """Test 50g carb meal"""
    
    print("\n" + "="*60)
    print("DALLA MAN MODEL - QUICK TEST")
    print("="*60)
    
    # Create model
    print("\nCreating model...")
    model = DallaManModel()
    
    # Test 50g meal
    print("\nSimulating 50g carb meal...")
    result = model.simulate(50, duration=240)
    
    print("\n=== SIMULATION RESULTS ===")
    print(f"Peak glucose: {result['peak_glucose']:.1f} mg/dL")
    print(f"Time to peak: {result['time_to_peak']:.0f} minutes")
    print(f"Glucose excursion: {result['excursion']:.1f} mg/dL")
    print(f"Final glucose: {result['final_glucose']:.1f} mg/dL")
    
    # Validate with 75g OGTT
    print("\n=== VALIDATION (75g OGTT) ===")
    is_valid = model.validate(verbose=True)
    
    # Plot
    print("\n=== CREATING PLOT ===")
    try:
        model.plot(result, save_path='glucose_test_result.png')
        print("✓ Plot saved as 'glucose_test_result.png'")
    except Exception as e:
        print(f"✗ Plot failed: {e}")
    
    return is_valid

if __name__ == '__main__':
    success = test_glucose_model()
    
    print("\n" + "="*60)
    if success:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ VALIDATION FAILED (but model ran)")
    print("="*60 + "\n")
    
    sys.exit(0 if success else 1)
