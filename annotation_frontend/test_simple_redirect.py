"""
Simple test for redirect functionality without requiring full app dependencies.
"""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

# Create a minimal app to test redirect logic
app = FastAPI()

# Simulate the settings
class MockSettings:
    API_BASE_PATH = "/api/v1"

settings = MockSettings()

# Add the redirect route (same as in main.py) - but exclude versioned paths
@app.api_route("/api/examples/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.api_route("/api/examples", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def redirect_unversioned_api(request: Request, path: str = ""):
    """
    Backwards compatibility redirect router.
    Issues HTTP 301 permanent redirect from /api/examples to /api/v1/examples
    """
    # Construct the versioned URL
    if path:
        versioned_path = f"{settings.API_BASE_PATH}/examples/{path}"
    else:
        versioned_path = f"{settings.API_BASE_PATH}/examples"
    
    # Preserve query parameters if any
    query_string = str(request.url.query)
    if query_string:
        versioned_path += f"?{query_string}"
    
    # Return HTTP 301 Moved Permanently redirect
    return RedirectResponse(
        url=versioned_path,
        status_code=301,
        headers={"X-API-Version-Redirect": "v1"}
    )

# Add a versioned endpoint to test against
@app.get("/api/v1/examples")
def get_examples():
    return {"examples": [], "total": 0}


def test_redirect_functionality():
    """Test that unversioned API calls redirect to v1"""
    client = TestClient(app)
    
    # Test redirect
    response = client.get("/api/examples", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "/api/v1/examples"
    assert response.headers["x-api-version-redirect"] == "v1"
    
    # Test query parameters are preserved
    response = client.get("/api/examples?page=2&size=20", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "/api/v1/examples?page=2&size=20"
    
    # Test versioned endpoint works directly
    response = client.get("/api/v1/examples")
    assert response.status_code == 200
    assert response.json() == {"examples": [], "total": 0}
    
    print("✅ All redirect tests passed!")


if __name__ == "__main__":
    test_redirect_functionality()
