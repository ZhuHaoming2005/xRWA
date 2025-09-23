from typing import Any, Dict, List, Tuple, Optional
from copy import deepcopy

from .crypto import (
	Eip712Domain,
	build_document_typed_data,
	build_section_typed_data,
	keccak256_json,
	recover_typed_data_signer,
)

SECTION_PATHS = [
	"/credentialSubject/identity",
	"/credentialSubject/compliance",
	"/credentialSubject/custody",
]


def _get_by_path(doc: Dict[str, Any], path: str) -> Any:
	parts = [p for p in path.split("/") if p]
	cur: Any = doc
	for p in parts:
		if isinstance(cur, dict) and p in cur:
			cur = cur[p]
		else:
			return None
	return cur


def _strip_eip712(vc: Dict[str, Any]) -> Dict[str, Any]:
	doc = deepcopy(vc)
	for path in SECTION_PATHS:
		section = _get_by_path(doc, path)
		if isinstance(section, dict):
			if "sProof" in section:
				section.pop("sProof", None)
	if isinstance(doc, dict):
		if "proof" in doc:
			doc.pop("proof", None)
	return doc


def _role_for_path(path: str) -> Optional[str]:
	if path.endswith("/identity"):
		return "identity"
	if path.endswith("/compliance"):
		return "compliance"
	if path.endswith("/custody"):
		return "custody"
	return None


def verify(vc: Dict[str, Any], expected_addresses: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
	"""Verify EIP-712 proofs on sections and document. Returns a list of results.
	If expected_addresses is provided, enforce recovered address == expected per role.
	Expected keys: identity, compliance, custody, document.
	"""
	results: List[Dict[str, Any]] = []

	# Verify sections (use existing sProof)
	clean = _strip_eip712(vc)
	for path in SECTION_PATHS:
		section = _get_by_path(vc, path)
		if not isinstance(section, dict):
			continue
		proof = section.get("sProof")
		if not isinstance(proof, dict):
			results.append({"path": path, "ok": False, "reason": "missing sProof"})
			continue

		section_clean = _get_by_path(clean, path) or {}
		computed_hash = keccak256_json(section_clean)

		domain_dict = proof.get("domain", {"name": "RWA-VC", "version": "1", "chainId": 1, "verifyingContract": "0x0000000000000000000000000000000000000000"})
		domain = Eip712Domain(
			name=domain_dict.get("name", "RWA-VC"),
			version=str(domain_dict.get("version", "1")),
			chainId=int(domain_dict.get("chainId", 1)),
			verifyingContract=domain_dict.get("verifyingContract", "0x0000000000000000000000000000000000000000"),
		)
		typed = build_section_typed_data(domain, path=path, section_hash_hex=computed_hash)

		signature = proof.get("proofValue", "")
		recovered = recover_typed_data_signer(typed, signature)

		expected_hash = proof.get("sectionHash")
		hash_ok = computed_hash == expected_hash

		role = _role_for_path(path)
		expected_from_keys = (expected_addresses or {}).get(role) if role else None
		expected_signer = proof.get("signer") or expected_from_keys
		addr_ok = True if not expected_signer else (recovered.lower() == str(expected_signer).lower())

		type_ok = proof.get("type") == "Eip712Signature2023"

		results.append({
			"path": path,
			"ok": bool(hash_ok and addr_ok and type_ok),
			"hash_ok": hash_ok,
			"addr_ok": addr_ok,
			"type_ok": type_ok,
			"recovered": recovered,
			"expected_signer": expected_signer,
			"role": role,
		})

	# Verify document using top-level proof
	proof_doc = vc.get("proof")
	if not isinstance(proof_doc, dict):
		results.append({"path": "/", "ok": False, "reason": "missing proof"})
		return results

	clean_doc = _strip_eip712(vc)
	computed_doc_hash = keccak256_json(clean_doc)

	domain_dict = proof_doc.get("domain", {"name": "RWA-VC", "version": "1", "chainId": 1, "verifyingContract": "0x0000000000000000000000000000000000000000"})
	domain = Eip712Domain(
		name=domain_dict.get("name", "RWA-VC"),
		version=str(domain_dict.get("version", "1")),
		chainId=int(domain_dict.get("chainId", 1)),
		verifyingContract=domain_dict.get("verifyingContract", "0x0000000000000000000000000000000000000000"),
	)
	typed_doc = build_document_typed_data(domain, document_hash_hex=computed_doc_hash)
	recovered_doc = recover_typed_data_signer(typed_doc, proof_doc.get("proofValue", ""))

	expected_doc = (expected_addresses or {}).get("document")
	expected_doc = proof_doc.get("signer") or expected_doc
	ok_doc = True
	if expected_doc:
		ok_doc = recovered_doc.lower() == str(expected_doc).lower()
	ok_doc = ok_doc and (proof_doc.get("type") == "Eip712Signature2023")

	results.append({"path": "/", "ok": ok_doc, "recovered": recovered_doc, "expected": expected_doc})

	return results
