#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RWA Verifiable Credential Issuer
"""

import json
import time
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import secrets
import base64
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.backends import default_backend
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SigningMetrics:
    """Signing performance metrics"""
    credential_size_bytes: int
    signing_time_ms: float
    hash_computation_time_ms: float
    signature_generation_time_ms: float
    signature_size_bytes: int
    total_processing_time_ms: float

@dataclass
class IssuanceMetrics:
    """Issuance performance metrics"""
    preparation_time_ms: float
    validation_time_ms: float
    signing_metrics: SigningMetrics
    serialization_time_ms: float
    total_issuance_time_ms: float
    credential_id: str
    timestamp: str

class RWAVCIssuer:
    """RWA Verifiable Credential Issuer"""
    
    def __init__(self, issuer_did: str = "did:web:test.issuer.example"):
        self.issuer_did = issuer_did
        self.signing_key_rsa = None
        self.signing_key_ed25519 = None
        self.verification_method = f"{issuer_did}#signing-key-1"
        self._initialize_keys()
        
    def _initialize_keys(self):
        """Initialize signing keys"""
        logger.info("Initializing signing keys...")
        
        # Generate RSA key pair
        self.signing_key_rsa = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Generate Ed25519 key pair
        self.signing_key_ed25519 = ed25519.Ed25519PrivateKey.generate()
        
        logger.info("Signing keys initialization completed")

    def _calculate_section_hash(self, section_data: Dict[str, Any]) -> str:
        """Calculate section hash"""
        start_time = time.perf_counter()
        
        # Normalize JSON and calculate hash
        canonical_json = json.dumps(section_data, sort_keys=True, separators=(',', ':'))
        hash_value = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        end_time = time.perf_counter()
        hash_time = (end_time - start_time) * 1000
        
        return f"0x{hash_value}", hash_time

    def _sign_with_rsa(self, data_hash: bytes) -> Tuple[str, float]:
        """Sign with RSA"""
        start_time = time.perf_counter()
        
        signature = self.signing_key_rsa.sign(
            data_hash,
            PSS(
                mgf=MGF1(hashes.SHA256()),
                salt_length=PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        end_time = time.perf_counter()
        signing_time = (end_time - start_time) * 1000
        
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        return f"0x{signature_b64[:64]}...", signing_time

    def _sign_with_ed25519(self, data: bytes) -> Tuple[str, float]:
        """Sign with Ed25519"""
        start_time = time.perf_counter()
        
        signature = self.signing_key_ed25519.sign(data)
        
        end_time = time.perf_counter()
        signing_time = (end_time - start_time) * 1000
        
        signature_hex = signature.hex()
        return f"0x{signature_hex[:64]}...", signing_time

    def _add_section_proof(self, section_data: Dict[str, Any], 
                          signature_type: str = "Eip712Signature2023") -> Tuple[Dict[str, Any], SigningMetrics]:
        """Add signature to section"""
        logger.debug(f"Adding {signature_type} signature to section...")
        
        start_processing = time.perf_counter()
        
        # Calculate section hash
        section_hash, hash_time = self._calculate_section_hash(section_data)
        
        # Generate signature
        data_to_sign = section_hash.encode('utf-8')
        
        if signature_type == "Eip712Signature2023":
            proof_value, signing_time = self._sign_with_rsa(hashlib.sha256(data_to_sign).digest())
        else:  # BbsBlsSignature2020
            proof_value, signing_time = self._sign_with_ed25519(data_to_sign)
        
        # Add section signature
        section_proof = {
            "type": signature_type,
            "issuer": self.issuer_did,
            "issued": datetime.now(timezone.utc).isoformat(),
            "expires": datetime.now(timezone.utc).replace(year=datetime.now().year + 2).isoformat(),
            "sectionHash": section_hash,
            "proofValue": proof_value
        }
        
        if signature_type == "BbsBlsSignature2020":
            section_proof.update({
                "verificationMethod": f"{self.issuer_did}#bbs-key-1",
                "proofPurpose": "assertionMethod"
            })
        
        section_data["sectionProof"] = section_proof
        
        end_processing = time.perf_counter()
        total_time = (end_processing - start_processing) * 1000
        
        # Calculate metrics
        section_json = json.dumps(section_data, separators=(',', ':'))
        signature_size = len(proof_value.encode('utf-8'))
        
        metrics = SigningMetrics(
            credential_size_bytes=len(section_json.encode('utf-8')),
            signing_time_ms=signing_time,
            hash_computation_time_ms=hash_time,
            signature_generation_time_ms=signing_time,
            signature_size_bytes=signature_size,
            total_processing_time_ms=total_time
        )
        
        return section_data, metrics

    def _validate_credential_structure(self, credential: Dict[str, Any]) -> bool:
        """Validate credential structure"""
        required_fields = ["@context", "type", "issuer", "issuanceDate", "credentialSubject"]
        
        for field in required_fields:
            if field not in credential:
                logger.error(f"Missing required field: {field}")
                return False
                
        # Validate types
        if "VerifiableCredential" not in credential["type"]:
            logger.error("Type must include VerifiableCredential")
            return False
            
        if "RWACompositeCredential" not in credential["type"]:
            logger.error("Type must include RWACompositeCredential")
            return False
            
        # Validate credentialSubject structure
        subject = credential["credentialSubject"]
        if "asset" not in subject:
            logger.error("credentialSubject missing asset field")
            return False
            
        return True

    def _prepare_credential_for_signing(self, credential_template: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare credential for signing"""
        credential = credential_template.copy()
        
        # Generate unique ID
        if "id" not in credential or not credential["id"]:
            credential["id"] = f"urn:uuid:{str(uuid.uuid4())}"
        
        # Set issuer
        credential["issuer"] = self.issuer_did
        
        # Set timestamp
        now = datetime.now(timezone.utc)
        credential["issuanceDate"] = now.isoformat()
        
        if "expirationDate" not in credential:
            credential["expirationDate"] = now.replace(year=now.year + 1).isoformat()
        
        # Set verification method
        credential["verificationMethod"] = self.verification_method
        
        return credential

    def issue_credential(self, credential_template: Dict[str, Any]) -> Tuple[Dict[str, Any], IssuanceMetrics]:
        """Issue RWA verifiable credential"""
        logger.info("Starting RWA verifiable credential issuance...")
        
        start_time = time.perf_counter()
        
        # 1. Preparation phase
        prep_start = time.perf_counter()
        credential = self._prepare_credential_for_signing(credential_template)
        prep_end = time.perf_counter()
        preparation_time = (prep_end - prep_start) * 1000
        
        # 2. Validation phase
        validation_start = time.perf_counter()
        if not self._validate_credential_structure(credential):
            raise ValueError("Credential structure validation failed")
        validation_end = time.perf_counter()
        validation_time = (validation_end - validation_start) * 1000
        
        # 3. Section signing phase
        signing_start = time.perf_counter()
        subject = credential["credentialSubject"]
        
        # Sign identity section
        if "identity" in subject:
            subject["identity"], identity_metrics = self._add_section_proof(
                subject["identity"], "Eip712Signature2023"
            )
        
        # Sign compliance section
        if "compliance" in subject:
            subject["compliance"], compliance_metrics = self._add_section_proof(
                subject["compliance"], "BbsBlsSignature2020"
            )
        
        # Sign custody section
        if "custody" in subject:
            subject["custody"], custody_metrics = self._add_section_proof(
                subject["custody"], "Eip712Signature2023"
            )
        
        # Top-level signature
        credential_hash, hash_time = self._calculate_section_hash(credential)
        proof_value, top_signing_time = self._sign_with_ed25519(credential_hash.encode('utf-8'))
        
        credential["proof"] = {
            "type": "BbsBlsSignature2020",
            "created": datetime.now(timezone.utc).isoformat(),
            "verificationMethod": f"{self.issuer_did}#bbs-key-1",
            "proofPurpose": "assertionMethod",
            "proofValue": proof_value
        }
        
        signing_end = time.perf_counter()
        signing_time = (signing_end - signing_start) * 1000
        
        # 4. Serialization phase
        serialization_start = time.perf_counter()
        credential_json = json.dumps(credential, indent=2, ensure_ascii=False)
        serialization_end = time.perf_counter()
        serialization_time = (serialization_end - serialization_start) * 1000
        
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000
        
        # Calculate comprehensive signing metrics
        overall_signing_metrics = SigningMetrics(
            credential_size_bytes=len(credential_json.encode('utf-8')),
            signing_time_ms=signing_time,
            hash_computation_time_ms=hash_time,
            signature_generation_time_ms=top_signing_time,
            signature_size_bytes=len(proof_value.encode('utf-8')),
            total_processing_time_ms=signing_time
        )
        
        # Create issuance metrics
        issuance_metrics = IssuanceMetrics(
            preparation_time_ms=preparation_time,
            validation_time_ms=validation_time,
            signing_metrics=overall_signing_metrics,
            serialization_time_ms=serialization_time,
            total_issuance_time_ms=total_time,
            credential_id=credential["id"],
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        logger.info(f"Credential issuance completed, total time: {total_time:.2f}ms")
        logger.info(f"Credential ID: {credential['id']}")
        logger.info(f"Credential size: {len(credential_json.encode('utf-8'))} bytes")
        
        return credential, issuance_metrics

    def batch_issue_credentials(self, credential_templates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[IssuanceMetrics]]:
        """Batch issue credentials"""
        logger.info(f"Starting batch issuance of {len(credential_templates)} credentials...")
        
        credentials = []
        metrics_list = []
        
        start_time = time.perf_counter()
        
        for i, template in enumerate(credential_templates):
            logger.info(f"Issuing credential {i+1}/{len(credential_templates)}")
            credential, metrics = self.issue_credential(template)
            credentials.append(credential)
            metrics_list.append(metrics)
        
        end_time = time.perf_counter()
        total_batch_time = (end_time - start_time) * 1000
        
        logger.info(f"Batch issuance completed, total time: {total_batch_time:.2f}ms")
        logger.info(f"Average time per credential: {total_batch_time/len(credential_templates):.2f}ms")
        
        return credentials, metrics_list

def load_credential_template(file_path: str) -> Dict[str, Any]:
    """Load credential template"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_issued_credential(credential: Dict[str, Any], output_path: str):
    """Save issued credential"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(credential, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Test code
    issuer = RWAVCIssuer("did:web:test.rwa.issuer.example")
    
    # Load example template
    try:
        template = load_credential_template("RWA-VC-example-vehicle.json")
        credential, metrics = issuer.issue_credential(template)
        
        print(f"Issuance successful!")
        print(f"Total time: {metrics.total_issuance_time_ms:.2f}ms")
        print(f"Credential size: {metrics.signing_metrics.credential_size_bytes} bytes")
        
        # Save result
        save_issued_credential(credential, "issued_vehicle_credential.json")
        
    except FileNotFoundError:
        print("Example file not found, please ensure RWA-VC-example-vehicle.json exists")
    except Exception as e:
        print(f"Issuance failed: {e}")