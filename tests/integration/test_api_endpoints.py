"""
Integration tests for the FastAPI endpoints in backend.main.

Uses httpx.AsyncClient (via pytest-asyncio) to hit the app directly
without spinning up a live server.

Endpoints tested:
    GET  /api/health
    POST /api/upload          (ZIP validation, discovery result)
    GET  /api/status/{job_id} (known / unknown job)
    GET  /api/files/{job_id}  (known / unknown job)
    GET  /api/profile/{job_id}(missing profile → 404)
    DELETE /api/job/{job_id}  (cleanup)
    POST /api/process/{job_id}(not-found / re-process guard)
"""

import io
import zipfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app


# =============================================================================
# Helpers
# =============================================================================

def _make_zip_bytes(include_files: bool = True) -> bytes:
    """Create an in-memory ZIP and return its bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if include_files:
            zf.writestr("brochure.pdf", b"%PDF-1.4 fake pdf content " * 10)
            zf.writestr("prices.csv", b"Name,Price\nTrek A,5000\nTrek B,8000\n")
            zf.writestr("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    return buf.getvalue()


def _make_empty_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as _:
        pass
    return buf.getvalue()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# =============================================================================
# Health endpoint
# =============================================================================

class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_has_status_ok(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_has_storage_key(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert "storage" in data

    @pytest.mark.asyncio
    async def test_health_has_llm_keys(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert "ollama" in data or "groq" in data


# =============================================================================
# Upload endpoint
# =============================================================================

class TestUploadEndpoint:

    @pytest.mark.asyncio
    async def test_upload_valid_zip_returns_200(self, client):
        zip_bytes = _make_zip_bytes()
        resp = await client.post(
            "/api/upload",
            files={"file": ("sample_business.zip", zip_bytes, "application/zip")},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_returns_job_id(self, client):
        zip_bytes = _make_zip_bytes()
        resp = await client.post(
            "/api/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")},
        )
        data = resp.json()
        assert "job_id" in data
        assert len(data["job_id"]) > 0

    @pytest.mark.asyncio
    async def test_upload_returns_file_collection(self, client):
        zip_bytes = _make_zip_bytes()
        resp = await client.post(
            "/api/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")},
        )
        data = resp.json()
        assert "file_collection" in data

    @pytest.mark.asyncio
    async def test_upload_non_zip_returns_400(self, client):
        resp = await client.post(
            "/api/upload",
            files={"file": ("document.pdf", b"fake pdf", "application/pdf")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_txt_file_returns_400(self, client):
        resp = await client.post(
            "/api/upload",
            files={"file": ("notes.txt", b"some text", "text/plain")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_empty_zip_returns_200(self, client):
        """Empty ZIPs are valid, just have zero files."""
        zip_bytes = _make_empty_zip_bytes()
        resp = await client.post(
            "/api/upload",
            files={"file": ("empty.zip", zip_bytes, "application/zip")},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_upload_empty_zip_total_files_zero(self, client):
        zip_bytes = _make_empty_zip_bytes()
        resp = await client.post(
            "/api/upload",
            files={"file": ("empty.zip", zip_bytes, "application/zip")},
        )
        data = resp.json()
        fc = data.get("file_collection", {})
        assert fc.get("total_files", 0) == 0

    @pytest.mark.asyncio
    async def test_upload_status_is_discovered(self, client):
        zip_bytes = _make_zip_bytes()
        resp = await client.post(
            "/api/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")},
        )
        data = resp.json()
        assert data["status"] == "discovered"


# =============================================================================
# Status endpoint
# =============================================================================

class TestStatusEndpoint:

    @pytest.fixture()
    async def uploaded_job_id(self, client) -> str:
        """Upload a ZIP and return the job_id."""
        zip_bytes = _make_zip_bytes()
        resp = await client.post(
            "/api/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")},
        )
        return resp.json()["job_id"]

    @pytest.mark.asyncio
    async def test_status_known_job_returns_200(self, client, uploaded_job_id):
        resp = await client.get(f"/api/status/{uploaded_job_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_status_has_job_id(self, client, uploaded_job_id):
        resp = await client.get(f"/api/status/{uploaded_job_id}")
        data = resp.json()
        assert data["job_id"] == uploaded_job_id

    @pytest.mark.asyncio
    async def test_status_unknown_job_returns_404(self, client):
        resp = await client.get("/api/status/nonexistent-job-xyz")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_status_has_progress_field(self, client, uploaded_job_id):
        resp = await client.get(f"/api/status/{uploaded_job_id}")
        data = resp.json()
        assert "progress" in data


# =============================================================================
# Files endpoint
# =============================================================================

class TestFilesEndpoint:

    @pytest.fixture()
    async def uploaded_job_id(self, client) -> str:
        zip_bytes = _make_zip_bytes()
        resp = await client.post(
            "/api/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")},
        )
        return resp.json()["job_id"]

    @pytest.mark.asyncio
    async def test_files_known_job_returns_200(self, client, uploaded_job_id):
        resp = await client.get(f"/api/files/{uploaded_job_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_files_unknown_job_returns_404(self, client):
        resp = await client.get("/api/files/nonexistent-job-xyz")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_files_response_has_job_id(self, client, uploaded_job_id):
        resp = await client.get(f"/api/files/{uploaded_job_id}")
        data = resp.json()
        assert data["job_id"] == uploaded_job_id

    @pytest.mark.asyncio
    async def test_files_response_has_file_lists(self, client, uploaded_job_id):
        resp = await client.get(f"/api/files/{uploaded_job_id}")
        data = resp.json()
        assert "documents" in data
        assert "images" in data
        assert "spreadsheets" in data


# =============================================================================
# Profile endpoint
# =============================================================================

class TestProfileEndpoint:

    @pytest.mark.asyncio
    async def test_profile_missing_job_returns_404(self, client):
        resp = await client.get("/api/profile/nonexistent-job-xyz")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_profile_newly_uploaded_job_404(self, client):
        """A job that was just uploaded has no profile yet."""
        zip_bytes = _make_zip_bytes()
        up_resp = await client.post(
            "/api/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")},
        )
        job_id = up_resp.json()["job_id"]

        profile_resp = await client.get(f"/api/profile/{job_id}")
        assert profile_resp.status_code == 404


# =============================================================================
# Delete endpoint
# =============================================================================

class TestDeleteEndpoint:

    @pytest.mark.asyncio
    async def test_delete_job_returns_200(self, client):
        zip_bytes = _make_zip_bytes()
        up_resp = await client.post(
            "/api/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")},
        )
        job_id = up_resp.json()["job_id"]

        del_resp = await client.delete(f"/api/job/{job_id}")
        assert del_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_removes_job_from_status(self, client):
        zip_bytes = _make_zip_bytes()
        up_resp = await client.post(
            "/api/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")},
        )
        job_id = up_resp.json()["job_id"]

        await client.delete(f"/api/job/{job_id}")

        status_resp = await client.get(f"/api/status/{job_id}")
        assert status_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_job_returns_200(self, client):
        """Delete on a non-existent job should not fail (idempotent cleanup)."""
        resp = await client.delete("/api/job/does-not-exist-xyz")
        assert resp.status_code == 200


# =============================================================================
# Process endpoint
# =============================================================================

class TestProcessEndpoint:

    @pytest.mark.asyncio
    async def test_process_unknown_job_returns_404(self, client):
        resp = await client.post("/api/process/nonexistent-job-xyz")
        assert resp.status_code == 404


if __name__ == "__main__":
    import asyncio
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
