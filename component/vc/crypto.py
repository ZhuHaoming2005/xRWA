import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_account.messages import encode_typed_data as _encode_typed_data  # eth-account >=0.10
from eth_utils import keccak, to_hex


# Enable eth-account local signing (no external provider)
Account.enable_unaudited_hdwallet_features()


def to_canonical_json(data: Any) -> str:
	"""Return canonical JSON string for hashing: sorted keys, compact separators.
	This ensures deterministic keccak256 input.
	"""
	return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def keccak256_json(data: Any) -> str:
	"""Compute keccak256(hash) of canonical JSON representation and return 0x-prefixed hex."""
	canonical = to_canonical_json(data).encode("utf-8")
	return to_hex(keccak(canonical))


@dataclass
class Eip712Domain:
	name: str = "RWA-VC"
	version: str = "1"
	chainId: int = 1
	verifyingContract: str = "0x0000000000000000000000000000000000000000"

	def as_dict(self) -> Dict[str, Any]:
		return {
			"name": self.name,
			"version": self.version,
			"chainId": self.chainId,
			"verifyingContract": self.verifyingContract,
		}


def build_section_typed_data(domain: Eip712Domain, path: str, section_hash_hex: str) -> Dict[str, Any]:
	"""Build EIP-712 typed data for a section hash proof."""
	return {
		"types": {
			"EIP712Domain": [
				{"name": "name", "type": "string"},
				{"name": "version", "type": "string"},
				{"name": "chainId", "type": "uint256"},
				{"name": "verifyingContract", "type": "address"},
			],
			"Section": [
				{"name": "path", "type": "string"},
				{"name": "sectionHash", "type": "bytes32"},
			],
		},
		"primaryType": "Section",
		"domain": domain.as_dict(),
		"message": {
			"path": path,
			"sectionHash": section_hash_hex,
		},
	}


def build_document_typed_data(domain: Eip712Domain, document_hash_hex: str) -> Dict[str, Any]:
	"""Build EIP-712 typed data for a document-level hash proof."""
	return {
		"types": {
			"EIP712Domain": [
				{"name": "name", "type": "string"},
				{"name": "version", "type": "string"},
				{"name": "chainId", "type": "uint256"},
				{"name": "verifyingContract", "type": "address"},
			],
			"Document": [
				{"name": "documentHash", "type": "bytes32"},
			],
		},
		"primaryType": "Document",
		"domain": domain.as_dict(),
		"message": {
			"documentHash": document_hash_hex,
		},
	}


def sign_typed_data(private_key_hex: str, typed_data: Dict[str, Any]) -> Tuple[str, str]:
	"""Sign EIP-712 typed data with a private key.
	Returns tuple of (signature_hex, signer_address).
	"""
	account: LocalAccount = Account.from_key(private_key_hex)
	encoded = _encode_typed_data(full_message=typed_data)
	signed = Account.sign_message(encoded, private_key=account.key)
	return to_hex(signed.signature), account.address


def recover_typed_data_signer(typed_data: Dict[str, Any], signature_hex: str) -> str:
	"""Recover signer address from EIP-712 signature and typed data."""
	encoded = _encode_typed_data(full_message=typed_data)
	recovered = Account.recover_message(encoded, signature=signature_hex)
	return recovered


def generate_private_key() -> str:
	"""Return a 0x-hex private key. """
	acct = Account.create()
	return to_hex(acct.key)


def private_key_to_address(private_key_hex: str) -> str:
	"""Derive checksummed address from a private key hex."""
	acct: LocalAccount = Account.from_key(private_key_hex)
	return acct.address
