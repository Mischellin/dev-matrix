"""Signing sub-API: create, fetch and verify document signatures."""

import hashlib

from .router import Request, Response, Router


class SigningService:
    def __init__(self) -> None:
        self._signatures: dict[str, dict[str, str]] = {}

    def sign(self, request: Request) -> Response:
        body = request.body
        if not isinstance(body, dict):
            return Response(400, {"error": "body must be an object"})
        document_id, signer = body.get("document_id"), body.get("signer")
        for value in (document_id, signer):
            if not isinstance(value, str) or not value.strip():
                return Response(422, {"error": "document_id and signer must be non-empty strings"})
        digest = hashlib.sha256(f"{document_id}:{signer}".encode()).hexdigest()
        signature_id = f"sig-{len(self._signatures) + 1}"
        record = {
            "signature_id": signature_id,
            "document_id": document_id,
            "signer": signer,
            "digest": digest,
        }
        self._signatures[signature_id] = record
        return Response(201, record)

    def get(self, request: Request) -> Response:
        record = self._signatures.get(request.params["signature_id"])
        if record is None:
            return Response(404, {"error": "unknown signature"})
        return Response(200, record)

    def verify(self, request: Request) -> Response:
        body = request.body
        if not isinstance(body, dict):
            return Response(400, {"error": "body must be an object"})
        signature_id = body.get("signature_id")
        if not isinstance(signature_id, str) or not signature_id:
            return Response(422, {"error": "signature_id must be a non-empty string"})
        if signature_id not in self._signatures:
            return Response(404, {"error": "unknown signature"})
        return Response(200, {"valid": True})


def mount_signing(router: Router) -> None:
    service = SigningService()
    router.add("POST", "/signing/sign", service.sign)
    router.add("GET", "/signing/signatures/{signature_id}", service.get)
    router.add("POST", "/signing/verify", service.verify)
