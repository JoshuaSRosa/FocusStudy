"""POST /api/courses/{id}/pdf endpoint."""
import io
import os

import pytest

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def upload(client, headers, course_id, content=PDF, filename="handout.pdf", mimetype="application/pdf", field="file"):
    return client.post(
        f"/api/courses/{course_id}/pdf",
        data={field: (io.BytesIO(content), filename, mimetype)},
        headers=headers,
        content_type="multipart/form-data",
    )


@pytest.mark.req("FR-05", "BR-02")
def test_upload_valid_pdf_stores_file_and_metadata(app, client, auth, create_course, db):
    c = create_course(auth)
    r = upload(client, auth, c["id"], filename="../../etc/Handout 1.pdf")
    assert r.status_code == 201
    pdf = r.get_json()["pdf"]
    assert pdf["mime"] == "application/pdf" and pdf["size_bytes"] == len(PDF)
    assert pdf["original_name"] == "etc_Handout_1.pdf"  # no path traversal
    assert pdf["course_id"] == c["id"]

    with db.cursor() as cur:
        cur.execute("SELECT stored_name FROM pdfs WHERE id = %s", (pdf["id"],))
        stored = cur.fetchone()[0]
    path = os.path.join(app.config["UPLOAD_DIR"], "1", stored)
    with open(path, "rb") as f:
        assert f.read() == PDF


@pytest.mark.req("BR-02", "NFR-02")
@pytest.mark.parametrize(
    "content,mimetype",
    [
        (b"this is plain text", "application/pdf"),  # client lies about the type
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "application/pdf"),
        (PDF, "image/png"),  # PDF content but wrong declared type
        (PDF, "application/octet-stream"),
    ],
    ids=["text-as-pdf", "png-as-pdf", "pdf-as-png", "pdf-as-octet-stream"],
)
def test_upload_rejects_non_pdf_with_415(app, client, auth, create_course, db, content, mimetype):
    c = create_course(auth)
    r = upload(client, auth, c["id"], content=content, mimetype=mimetype)
    assert r.status_code == 415 and r.get_json()["status"] == "error"
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pdfs")
        assert cur.fetchone()[0] == 0
    folder = os.path.join(app.config["UPLOAD_DIR"], "1")
    assert not os.path.isdir(folder) or os.listdir(folder) == []


@pytest.mark.req("FR-05", "NFR-02")
def test_upload_without_file_or_empty_returns_400(client, auth, create_course):
    c = create_course(auth)
    assert upload(client, auth, c["id"], field="other").status_code == 400
    assert upload(client, auth, c["id"], content=b"").status_code == 400


@pytest.mark.req("FR-05", "NFR-01")
def test_upload_to_missing_or_another_users_course_returns_404(client, auth, auth_b, create_course):
    c = create_course(auth)
    assert upload(client, auth_b, c["id"]).status_code == 404
    assert upload(client, auth, 999).status_code == 404


@pytest.mark.req("FR-05", "NFR-02")
def test_upload_over_limit_returns_413(app, client, auth, create_course):
    app.config["MAX_CONTENT_LENGTH"] = 1024
    c = create_course(auth)
    big = PDF[:-7] + b"\x00" * 4096 + b"%%EOF\n"
    r = upload(client, auth, c["id"], content=big)
    assert r.status_code == 413 and r.get_json()["status"] == "error"


@pytest.mark.req("FR-05", "FR-04")
def test_delete_course_removes_pdfs_from_disk(app, client, auth, create_course):
    c = create_course(auth)
    upload(client, auth, c["id"])
    folder = os.path.join(app.config["UPLOAD_DIR"], "1")
    assert len(os.listdir(folder)) == 1
    client.delete(f"/api/courses/{c['id']}", headers=auth)
    assert os.listdir(folder) == []
