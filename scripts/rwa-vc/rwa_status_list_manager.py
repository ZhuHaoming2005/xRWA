#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RWA StatusList2021 Status List Manager
"""

import json
import time
import base64
import gzip
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import bitarray
import threading
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StatusListMetrics:
    """Status list performance metrics"""
    list_size_entries: int
    list_size_bytes: int
    compression_ratio: float
    update_time_ms: float
    query_time_ms: float
    batch_update_time_ms: float
    timestamp: str

@dataclass
class StatusEntry:
    """Status entry"""
    index: int
    status: str  # "valid", "revoked", "suspended"
    updated_at: str
    reason: Optional[str] = None

class StatusList2021:
    """StatusList2021 implementation"""
    
    def __init__(self, list_id: str, purpose: str = "revocation", size: int = 131072):
        """
        Initialize status list
        
        Args:
            list_id: Unique identifier for status list
            purpose: Purpose ("revocation" or "suspension")
            size: List size (must be power of 2)
        """
        self.list_id = list_id
        self.purpose = purpose
        self.size = size
        self.issuer = "did:web:status.rwa.issuer.example"
        self.created = datetime.now(timezone.utc).isoformat()
        self.updated = self.created
        
        # Use bitarray for efficient status storage
        self.status_bits = bitarray.bitarray(size)
        self.status_bits.setall(0)  # Initialize all as valid (0)
        
        # For recording detailed status information
        self.detailed_status: Dict[int, StatusEntry] = {}
        
        # Thread lock
        self._lock = threading.RLock()
        
        logger.info(f"Created status list {list_id}, size: {size}, purpose: {purpose}")
    
    def update_status(self, index: int, status: str, reason: Optional[str] = None) -> float:
        """Update single status"""
        start_time = time.perf_counter()
        
        with self._lock:
            if index >= self.size or index < 0:
                raise ValueError(f"Index out of range: {index}")
            
            # Update bit array
            if status == "revoked" or status == "suspended":
                self.status_bits[index] = 1
            else:  # valid
                self.status_bits[index] = 0
            
            # Update detailed status
            self.detailed_status[index] = StatusEntry(
                index=index,
                status=status,
                updated_at=datetime.now(timezone.utc).isoformat(),
                reason=reason
            )
            
            self.updated = datetime.now(timezone.utc).isoformat()
        
        end_time = time.perf_counter()
        update_time = (end_time - start_time) * 1000
        
        logger.debug(f"Updated status [{index}] -> {status}, time: {update_time:.3f}ms")
        return update_time
    
    def batch_update_status(self, updates: List[Tuple[int, str, Optional[str]]]) -> float:
        """Batch update status"""
        start_time = time.perf_counter()
        
        with self._lock:
            for index, status, reason in updates:
                if index >= self.size or index < 0:
                    logger.warning(f"Skipping invalid index: {index}")
                    continue
                
                # Update bit array
                if status == "revoked" or status == "suspended":
                    self.status_bits[index] = 1
                else:  # valid
                    self.status_bits[index] = 0
                
                # Update detailed status
                self.detailed_status[index] = StatusEntry(
                    index=index,
                    status=status,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                    reason=reason
                )
            
            self.updated = datetime.now(timezone.utc).isoformat()
        
        end_time = time.perf_counter()
        batch_time = (end_time - start_time) * 1000
        
        logger.info(f"Batch updated {len(updates)} statuses, time: {batch_time:.2f}ms")
        return batch_time
    
    def get_status(self, index: int) -> Tuple[str, float]:
        """Get status"""
        start_time = time.perf_counter()
        
        with self._lock:
            if index >= self.size or index < 0:
                raise ValueError(f"Index out of range: {index}")
            
            # Read from bit array
            bit_value = self.status_bits[index]
            
            # If detailed status information exists, use detailed status
            if index in self.detailed_status:
                status = self.detailed_status[index].status
            else:
                status = "revoked" if bit_value else "valid"
        
        end_time = time.perf_counter()
        query_time = (end_time - start_time) * 1000
        
        return status, query_time
    
    def get_compressed_list(self) -> Tuple[str, float, float]:
        """Get compressed status list"""
        start_time = time.perf_counter()
        
        with self._lock:
            # Convert to byte array
            byte_data = self.status_bits.tobytes()
            
            # Compress
            compressed_data = gzip.compress(byte_data)
            
            # Base64 encode
            encoded_data = base64.b64encode(compressed_data).decode('utf-8')
        
        end_time = time.perf_counter()
        compression_time = (end_time - start_time) * 1000
        
        # Calculate compression ratio
        original_size = len(byte_data)
        compressed_size = len(compressed_data)
        compression_ratio = compressed_size / original_size if original_size > 0 else 0
        
        logger.debug(f"Status list compression completed, compression ratio: {compression_ratio:.3f}, time: {compression_time:.2f}ms")
        
        return encoded_data, compression_ratio, compression_time
    
    def to_status_list_credential(self) -> Dict[str, Any]:
        """Convert to StatusList2021 credential format"""
        encoded_list, compression_ratio, _ = self.get_compressed_list()
        
        credential = {
            "@context": [
                "https://www.w3.org/ns/credentials/v2",
                "https://w3id.org/security/v1",
                "https://w3id.org/vc/status-list/2021/v1"
            ],
            "type": ["VerifiableCredential", "StatusList2021Credential"],
            "id": f"https://status.rwa.issuer.example/lists/{self.list_id}",
            "issuer": self.issuer,
            "issuanceDate": self.created,
            "credentialSubject": {
                "id": f"https://status.rwa.issuer.example/lists/{self.list_id}#list",
                "type": "StatusList2021",
                "statusPurpose": self.purpose,
                "encodedList": encoded_list
            },
            "proof": {
                "type": "Ed25519Signature2020",
                "created": self.updated,
                "verificationMethod": f"{self.issuer}#status-key-1",
                "proofPurpose": "assertionMethod",
                "proofValue": f"z{base64.b64encode(f'mock_signature_{self.list_id}'.encode()).decode()}"
            }
        }
        
        return credential
    
    def get_metrics(self) -> StatusListMetrics:
        """Get performance metrics"""
        encoded_list, compression_ratio, compression_time = self.get_compressed_list()
        
        # Simulate query time
        _, query_time = self.get_status(0)
        
        # Simulate batch update time
        batch_updates = [(i, "valid", None) for i in range(min(100, self.size))]
        batch_time = self.batch_update_status(batch_updates)
        
        return StatusListMetrics(
            list_size_entries=self.size,
            list_size_bytes=len(encoded_list.encode('utf-8')),
            compression_ratio=compression_ratio,
            update_time_ms=0.0,  # Single update time returned by update_status
            query_time_ms=query_time,
            batch_update_time_ms=batch_time,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

class StatusListManager:
    """Status list manager"""
    
    def __init__(self):
        self.status_lists: Dict[str, StatusList2021] = {}
        self._lock = threading.RLock()
        self._initialize_default_lists()
    
    def _initialize_default_lists(self):
        """Initialize default status lists"""
        default_lists = [
            ("identity-2025-01", "revocation"),
            ("compliance-2025-01", "suspension"),
            ("custody-2025-01", "revocation"),
            ("vehicle-registry-2025-03", "revocation"),
            ("housing-registry-2025-07", "revocation"),
            ("precious-metals-2025-01", "revocation"),
        ]
        
        for list_id, purpose in default_lists:
            self.create_status_list(list_id, purpose)
    
    def create_status_list(self, list_id: str, purpose: str = "revocation", size: int = 131072) -> StatusList2021:
        """Create new status list"""
        with self._lock:
            if list_id in self.status_lists:
                logger.warning(f"Status list {list_id} already exists")
                return self.status_lists[list_id]
            
            status_list = StatusList2021(list_id, purpose, size)
            self.status_lists[list_id] = status_list
            
            logger.info(f"Created status list: {list_id}")
            return status_list
    
    def get_status_list(self, list_id: str) -> Optional[StatusList2021]:
        """Get status list"""
        return self.status_lists.get(list_id)
    
    def update_credential_status(self, list_id: str, index: int, status: str, reason: Optional[str] = None) -> float:
        """Update credential status"""
        status_list = self.get_status_list(list_id)
        if not status_list:
            raise ValueError(f"Status list does not exist: {list_id}")
        
        return status_list.update_status(index, status, reason)
    
    def check_credential_status(self, list_id: str, index: int) -> Tuple[str, float]:
        """Check credential status"""
        status_list = self.get_status_list(list_id)
        if not status_list:
            return "unknown", 0.0
        
        return status_list.get_status(index)
    
    def batch_revoke_credentials(self, list_id: str, indices: List[int], reason: str = "Security breach") -> float:
        """Batch revoke credentials"""
        status_list = self.get_status_list(list_id)
        if not status_list:
            raise ValueError(f"Status list does not exist: {list_id}")
        
        updates = [(index, "revoked", reason) for index in indices]
        return status_list.batch_update_status(updates)
    
    def get_status_list_credential(self, list_id: str) -> Optional[Dict[str, Any]]:
        """Get status list credential"""
        status_list = self.get_status_list(list_id)
        if not status_list:
            return None
        
        return status_list.to_status_list_credential()
    
    def get_all_metrics(self) -> Dict[str, StatusListMetrics]:
        """Get performance metrics for all status lists"""
        metrics = {}
        
        for list_id, status_list in self.status_lists.items():
            metrics[list_id] = status_list.get_metrics()
        
        return metrics
    
    def simulate_production_load(self, list_id: str, num_updates: int = 10000) -> Dict[str, float]:
        """Simulate production environment load"""
        logger.info(f"Starting production environment load simulation, update count: {num_updates}")
        
        status_list = self.get_status_list(list_id)
        if not status_list:
            raise ValueError(f"Status list does not exist: {list_id}")
        
        start_time = time.perf_counter()
        
        # Generate random updates
        import random
        updates = []
        for i in range(num_updates):
            index = random.randint(0, status_list.size - 1)
            status = random.choice(["valid", "revoked", "suspended"])
            reason = f"Batch update {i}" if status != "valid" else None
            updates.append((index, status, reason))
        
        # Execute batch update
        batch_time = status_list.batch_update_status(updates)
        
        # Execute query test
        query_times = []
        for _ in range(1000):
            index = random.randint(0, status_list.size - 1)
            _, query_time = status_list.get_status(index)
            query_times.append(query_time)
        
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000
        
        avg_query_time = sum(query_times) / len(query_times)
        
        results = {
            "total_time_ms": total_time,
            "batch_update_time_ms": batch_time,
            "avg_query_time_ms": avg_query_time,
            "updates_per_second": num_updates / (total_time / 1000),
            "queries_per_second": 1000 / (sum(query_times) / 1000)
        }
        
        logger.info(f"Load test completed: {results}")
        return results

def save_metrics_report(metrics: Dict[str, StatusListMetrics], file_path: str):
    """Save performance metrics report"""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_lists": {}
    }
    
    for list_id, metric in metrics.items():
        report["status_lists"][list_id] = asdict(metric)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Status list performance report saved to: {file_path}")

if __name__ == "__main__":
    # Test code
    manager = StatusListManager()
    
    # Create test status list
    test_list = manager.create_status_list("test-list", "revocation", 1024)
    
    # Test single update
    update_time = test_list.update_status(100, "revoked", "Test revocation")
    print(f"Single update time: {update_time:.3f}ms")
    
    # Test query
    status, query_time = test_list.get_status(100)
    print(f"Query result: {status}, time: {query_time:.3f}ms")
    
    # Test batch update
    batch_updates = [(i, "suspended", f"Batch test {i}") for i in range(10)]
    batch_time = test_list.batch_update_status(batch_updates)
    print(f"Batch update time: {batch_time:.2f}ms")
    
    # Get performance metrics
    metrics = test_list.get_metrics()
    print(f"Status list size: {metrics.list_size_entries} entries")
    print(f"Compressed size: {metrics.list_size_bytes} bytes")
    print(f"Compression ratio: {metrics.compression_ratio:.3f}")
    
    # Simulate production load
    load_results = manager.simulate_production_load("test-list", 1000)
    print(f"Production load test results: {load_results}")
    
    # Save report
    all_metrics = manager.get_all_metrics()
    save_metrics_report(all_metrics, "status_list_metrics_report.json")