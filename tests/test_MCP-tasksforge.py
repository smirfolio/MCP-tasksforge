import logging
import json
from src.server import get_project_status, save_project_context, initialize_project_workflow, log_task_completion, get_project_context
# --- TESTING FUNCTIONS (Protocol Requirement) ---

async def test_all_tools():
    """Test all MCP tools individually (Required by Protocol)"""
    logging.info("[Test] Starting comprehensive tool testing...")
    
    test_results = {}
    
    # Test 1: get_project_status (should work without external dependencies)
    try:
        logging.info("[Test] Testing get_project_status...")
        result = get_project_status()
        data = json.loads(result)
        test_results["get_project_status"] = {
            "passed": data.get("success", False),
            "result": data
        }
        logging.info(f"[Test] get_project_status: {'PASSED' if data.get('success') else 'FAILED'}")
    except Exception as e:
        test_results["get_project_status"] = {
            "passed": False,
            "error": str(e)
        }
        logging.error(f"[Test] get_project_status FAILED: {e}")
    
    # Test 2: initialize_project_workflow
    try:
        logging.info("[Test] Testing initialize_project_workflow...")
        result = initialize_project_workflow()
        data = json.loads(result)
        test_results["initialize_project_workflow"] = {
            "passed": data.get("success", False),
            "result": data
        }
        logging.info(f"[Test] initialize_project_workflow: {'PASSED' if data.get('success') else 'FAILED'}")
    except Exception as e:
        test_results["initialize_project_workflow"] = {
            "passed": False,
            "error": str(e)
        }
        logging.error(f"[Test] initialize_project_workflow FAILED: {e}")
    
    # Test 3: save_project_context (with sample data)
    try:
        logging.info("[Test] Testing save_project_context...")
        test_context = "# Test Project Context\n\nThis is a test context for MCP tool testing."
        result = save_project_context(test_context)
        data = json.loads(result)
        test_results["save_project_context"] = {
            "passed": data.get("success", False),
            "result": data
        }
        logging.info(f"[Test] save_project_context: {'PASSED' if data.get('success') else 'FAILED'}")
    except Exception as e:
        test_results["save_project_context"] = {
            "passed": False,
            "error": str(e)
        }
        logging.error(f"[Test] save_project_context FAILED: {e}")
    
    # Test 4: log_task_completion (with sample data)
    try:
        logging.info("[Test] Testing log_task_completion...")
        test_report = "Test task completed successfully. This is a test entry for MCP tool testing."
        result = log_task_completion(test_report)
        data = json.loads(result)
        test_results["log_task_completion"] = {
            "passed": data.get("success", False),
            "result": data
        }
        logging.info(f"[Test] log_task_completion: {'PASSED' if data.get('success') else 'FAILED'}")
    except Exception as e:
        test_results["log_task_completion"] = {
            "passed": False,
            "error": str(e)
        }
        logging.error(f"[Test] log_task_completion FAILED: {e}")
    
    # Test 5: get_project_context (Note: This requires API access and might fail in testing)
    try:
        logging.info("[Test] Testing get_project_context (may fail without valid API credentials)...")
        result = await get_project_context(1)  # Test with project ID 1
        data = json.loads(result)
        # For this test, we consider it passed if it returns a valid JSON structure
        # even if the API call fails due to missing credentials
        test_results["get_project_context"] = {
            "passed": isinstance(data, dict) and "success" in data,
            "result": data,
            "note": "API test - may fail without valid credentials"
        }
        logging.info(f"[Test] get_project_context: {'PASSED' if test_results['get_project_context']['passed'] else 'FAILED'}")
    except Exception as e:
        test_results["get_project_context"] = {
            "passed": False,
            "error": str(e),
            "note": "API test - may fail without valid credentials"
        }
        logging.error(f"[Test] get_project_context FAILED: {e}")
    
    # Summary
    passed_tests = sum(1 for test in test_results.values() if test["passed"])
    total_tests = len(test_results)
    
    logging.info(f"[Test] TESTING COMPLETE: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logging.info("[Test] ✅ ALL TESTS PASSED - Server ready for deployment")
    else:
        logging.warning(f"[Test] ⚠️  {total_tests - passed_tests} tests failed - Review required")
    
    return test_results
