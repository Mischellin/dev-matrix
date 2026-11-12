"""Signing sub-API: create, fetch and verify document signatures."""

import hashlib

from .router import Request, Response, Router


class SigningService:
    def __init__(self) -> None:
        self._signatures: dict[str, dict[str, str]] = {}

    def sign(self, request: Request) -> Response:
        document_id = request.body["document_id"]
        signer = request.body["signer"]
        digest = hashlib.sha256(f"{document_id}:{signer}".encode()).hexdigest()
        signature_id = f"sig-{len(self._signatures) + 1}"
        record = {
            "signature_id": signature_id,
            "document_id": document_id,
            "signer": signer,
            "digest": digest,
        }
        self._signatures[signature_id] = record
        return Response(200, record)

    def get(self, request: Request) -> Response:
        record = self._signatures.get(request.params["signature_id"])
        if record is None:
            return Response(404, {"error": "unknown signature"})
        return Response(200, record)

    def verify(self, request: Request) -> Response:
        record = self._signatures.get(request.body.get("signature_id"))
        return Response(200, {"valid": record is not None})


def mount_signing(router: Router) -> None:
    service = SigningService()
    router.add("POST", "/signing/sign", service.sign)
    router.add("GET", "/signing/signatures/{signature_id}", service.get)
    router.add("POST", "/signing/verify", service.verify)
