import json
import os
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from .crypto import (
	Eip712Domain,
	build_document_typed_data,
	build_section_typed_data,
	generate_private_key,
	keccak256_json,
	sign_typed_data,
)


SECTION_PATHS = [
	"/credentialSubject/identity",
	"/credentialSubject/compliance",
	"/credentialSubject/custody",
]


def _get_by_path(doc: Dict[str, Any], path: str) -> Any:
	"""Get nested value using a simple slash path like /a/b/c."""
	parts = [p for p in path.split("/") if p]
	cur: Any = doc
	for p in parts:
		if isinstance(cur, dict) and p in cur:
			cur = cur[p]
		else:
			return None
	return cur


def _update_section_proof(section: Dict[str, Any], section_hash: str, signature: str) -> None:
	"""Update existing sProof fields with real hash/signature without adding new fields."""
	proof = section.get("sProof")
	if isinstance(proof, dict):
		# Only modify values; keep existing keys
		if "type" in proof:
			proof["type"] = "Eip712Signature2023"
		if "sectionHash" in proof:
			proof["sectionHash"] = section_hash
		if "proofValue" in proof:
			proof["proofValue"] = signature


def _update_top_proof(doc: Dict[str, Any], signature: str) -> None:
	"""Update existing top-level proof (no new fields), writing EIP-712 signature into proofValue and type."""
	proof = doc.get("proof")
	if isinstance(proof, dict):
		if "type" in proof:
			proof["type"] = "Eip712Signature2023"
		if "proofValue" in proof:
			proof["proofValue"] = signature


def _strip_existing_eip712(vc: Dict[str, Any]) -> Dict[str, Any]:
	"""Return a copy of VC with any EIP-712 proofs removed to ensure hash determinism."""
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


def issue(
	vc: Dict[str, Any],
	keys_cfg: Dict[str, Any],
	verifying_contract: str = "0x0000000000000000000000000000000000000000",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
	"""Issue EIP-712 proofs for known sections and the overall document.
	Returns (issued_vc, proofs_metadata).
	"""
	issued = deepcopy(vc)

	# Prepare domain
	domain_cfg = keys_cfg.get("domain", {})
	domain = Eip712Domain(
		name=domain_cfg.get("name", "RWA-VC"),
		version=str(domain_cfg.get("version", "1")),
		chainId=int(domain_cfg.get("chainId", 1)),
		verifyingContract=verifying_contract,
	)

	# Resolve keys
	keys = keys_cfg.get("keys", {})
	priv_identity = keys.get("identity")
	priv_compliance = keys.get("compliance")
	priv_custody = keys.get("custody")
	priv_document = keys.get("document")

	proofs_meta: List[Dict[str, Any]] = []

	# Section proofs
	clean_for_section_hash = _strip_existing_eip712(issued)
	for path, priv in [
		(SECTION_PATHS[0], priv_identity),
		(SECTION_PATHS[1], priv_compliance),
		(SECTION_PATHS[2], priv_custody),
	]:
		section = _get_by_path(issued, path)
		if not isinstance(section, dict):
			continue

		# Hash the section from the clean doc (without EIP-712 proofs)
		section_clean = _get_by_path(clean_for_section_hash, path) or {}
		section_hash = keccak256_json(section_clean)

		typed = build_section_typed_data(domain, path=path, section_hash_hex=section_hash)
		signature, signer = sign_typed_data(priv, typed)

		_update_section_proof(section, section_hash, signature)
		proofs_meta.append({"path": path, "sectionHash": section_hash})

	# Document proof (hash the entire VC excluding proofs)
	clean_for_doc_hash = _strip_existing_eip712(issued)
	doc_hash = keccak256_json(clean_for_doc_hash)
	typed_doc = build_document_typed_data(domain, document_hash_hex=doc_hash)
	sig_doc, signer_doc = sign_typed_data(priv_document, typed_doc)

	# Update existing top-level proof; do not add new fields
	_update_top_proof(issued, sig_doc)
	proofs_meta.append({"path": "/", "documentHash": doc_hash})

	return issued, proofs_meta
