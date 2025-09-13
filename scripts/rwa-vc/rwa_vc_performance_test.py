# -*- coding: utf-8 -*-
"""
RWA Verifiable Credential Performance Test Suite
"""

import json
import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
import numpy as np
import logging
import sys

# Import custom modules
from rwa_vc_issuer import RWAVCIssuer, IssuanceMetrics
from rwa_vc_verifier import RWAVCVerifier, VerificationMetrics
from rwa_status_list_manager import StatusListManager

# Set font for Chinese characters
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestConfiguration:
    """Test configuration"""
    num_credentials: int
    num_iterations: int
    concurrent_workers: int
    credential_types: List[str]
    test_scenarios: List[str]
    output_directory: str

@dataclass
class PerformanceTestResults:
    """Performance test results"""
    test_name: str
    timestamp: str
    configuration: TestConfiguration
    issuance_results: Dict[str, Any]
    verification_results: Dict[str, Any]
    status_list_results: Dict[str, Any]
    summary_statistics: Dict[str, Any]

class RWAVCPerformanceTester:
    """RWA VC Performance Tester"""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.issuer = RWAVCIssuer("did:web:test.performance.issuer.example")
        self.verifier = RWAVCVerifier()
        self.status_manager = StatusListManager()
        
        # Create output directory
        self.output_dir = Path(config.output_directory)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load example credential templates
        self.credential_templates = self._load_credential_templates()
        
        logger.info(f"Performance tester initialized, config: {config.num_credentials} credentials, {config.num_iterations} iterations")
    
    def _load_credential_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load credential templates"""
        templates = {}
        
        template_files = {
            "vehicle": "RWA-VC-example-vehicle.json",
            "realestate": "RWA-VC-example-realestate.json", 
            "gold": "RWA-VC-example-gold.json",
            "art": "RWA-VC-example-art.json",
            "bond": "RWA-VC-example-bond.json",
            "fund": "RWA-VC-example-fund.json",
            "ip": "RWA-VC-example-ip.json"
        }
        
        for asset_type, filename in template_files.items():
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    templates[asset_type] = json.load(f)
                logger.info(f"Loaded template: {asset_type}")
            except FileNotFoundError:
                logger.warning(f"Template file not found: {filename}")
        
        if not templates:
            # If no template files found, use basic template
            templates["basic"] = self._create_basic_template()
            logger.info("Using basic template")
        
        return templates
    
    def _create_basic_template(self) -> Dict[str, Any]:
        """Create basic credential template"""
        return {
            "@context": [
                "https://www.w3.org/ns/credentials/v2",
                "https://schema.org/",
                "https://example.org/contexts/rwa-composite-v1.jsonld"
            ],
            "type": ["VerifiableCredential", "RWACompositeCredential"],
            "issuer": "did:web:test.performance.issuer.example",
            "credentialSubject": {
                "id": "did:ion:test123",
                "asset": {
                    "assetId": "did:ion:test123",
                    "assetType": "TestAsset",
                    "category": "Performance",
                    "tokenBinding": {
                        "standard": "ERC-721",
                        "chain": "eip155:1",
                        "contract": "0x1234567890123456789012345678901234567890",
                        "tokenId": "1001"
                    }
                },
                "identity": {
                    "schemaVersion": 1,
                    "identifiers": [
                        {
                            "identifierScheme": "Test",
                            "identifierValue": "TEST-001"
                        }
                    ],
                    "attributes": [
                        {"name": "testAttribute", "value": "testValue"}
                    ]
                }
            }
        }
    
    def test_issuance_performance(self, credential_type: str = "vehicle") -> Dict[str, Any]:
        """Test issuance performance"""
        logger.info(f"Starting {credential_type} credential issuance performance test...")
        
        if credential_type not in self.credential_templates:
            credential_type = list(self.credential_templates.keys())[0]
            logger.warning(f"Using default credential type: {credential_type}")
        
        template = self.credential_templates[credential_type]
        
        # Single-threaded test
        single_thread_results = self._test_single_thread_issuance(template)
        
        # Multi-threaded test
        multi_thread_results = self._test_multi_thread_issuance(template)
        
        # Batch test
        batch_results = self._test_batch_issuance(template)
        
        results = {
            "credential_type": credential_type,
            "single_thread": single_thread_results,
            "multi_thread": multi_thread_results,
            "batch": batch_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"{credential_type} credential issuance performance test completed")
        return results
    
    def _test_single_thread_issuance(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Single-threaded issuance test"""
        logger.info("Executing single-threaded issuance test...")
        
        times = []
        metrics_list = []
        
        for i in range(self.config.num_iterations):
            start_time = time.perf_counter()
            credential, metrics = self.issuer.issue_credential(template.copy())
            end_time = time.perf_counter()
            
            total_time = (end_time - start_time) * 1000
            times.append(total_time)
            metrics_list.append(metrics)
            
            if (i + 1) % 10 == 0:
                logger.info(f"Completed {i + 1}/{self.config.num_iterations} issuances")
        
        return self._calculate_statistics(times, metrics_list, "single_thread_issuance")
    
    def _test_multi_thread_issuance(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Multi-threaded issuance test"""
        logger.info(f"Executing multi-threaded issuance test, worker threads: {self.config.concurrent_workers}...")
        
        times = []
        metrics_list = []
        
        def issue_credential_task():
            start_time = time.perf_counter()
            credential, metrics = self.issuer.issue_credential(template.copy())
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, metrics
        
        start_total = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.config.concurrent_workers) as executor:
            futures = [executor.submit(issue_credential_task) for _ in range(self.config.num_iterations)]
            
            for i, future in enumerate(as_completed(futures)):
                time_taken, metrics = future.result()
                times.append(time_taken)
                metrics_list.append(metrics)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Completed {i + 1}/{self.config.num_iterations} multi-threaded issuances")
        
        end_total = time.perf_counter()
        total_concurrent_time = (end_total - start_total) * 1000
        
        results = self._calculate_statistics(times, metrics_list, "multi_thread_issuance")
        results["total_concurrent_time_ms"] = total_concurrent_time
        results["throughput_per_second"] = self.config.num_iterations / (total_concurrent_time / 1000)
        
        return results
    
    def _test_batch_issuance(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Batch issuance test"""
        logger.info("Executing batch issuance test...")
        
        templates = [template.copy() for _ in range(self.config.num_credentials)]
        
        start_time = time.perf_counter()
        credentials, metrics_list = self.issuer.batch_issue_credentials(templates)
        end_time = time.perf_counter()
        
        total_time = (end_time - start_time) * 1000
        avg_time_per_credential = total_time / len(credentials)
        
        individual_times = [m.total_issuance_time_ms for m in metrics_list]
        
        return {
            "total_batch_time_ms": total_time,
            "avg_time_per_credential_ms": avg_time_per_credential,
            "credentials_per_second": len(credentials) / (total_time / 1000),
            "individual_times_ms": individual_times,
            "statistics": self._basic_statistics(individual_times)
        }
    
    def test_verification_performance(self, credentials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test verification performance"""
        logger.info("Starting credential verification performance test...")
        
        if not credentials:
            logger.warning("No credentials provided for verification test")
            return {}
        
        # Single-threaded verification test
        single_thread_results = self._test_single_thread_verification(credentials)
        
        # Multi-threaded verification test
        multi_thread_results = self._test_multi_thread_verification(credentials)
        
        # Batch verification test
        batch_results = self._test_batch_verification(credentials)
        
        results = {
            "single_thread": single_thread_results,
            "multi_thread": multi_thread_results,
            "batch": batch_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Credential verification performance test completed")
        return results
    
    def _test_single_thread_verification(self, credentials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Single-threaded verification test"""
        logger.info("Executing single-threaded verification test...")
        
        times = []
        metrics_list = []
        success_count = 0
        
        test_credentials = credentials[:self.config.num_iterations]
        
        for i, credential in enumerate(test_credentials):
            start_time = time.perf_counter()
            result, metrics = self.verifier.verify_credential(credential)
            end_time = time.perf_counter()
            
            total_time = (end_time - start_time) * 1000
            times.append(total_time)
            metrics_list.append(metrics)
            
            if result.is_valid:
                success_count += 1
            
            if (i + 1) % 10 == 0:
                logger.info(f"Completed {i + 1}/{len(test_credentials)} verifications")
        
        results = self._calculate_statistics(times, metrics_list, "single_thread_verification")
        results["success_rate"] = success_count / len(test_credentials)
        
        return results
    
    def _test_multi_thread_verification(self, credentials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Multi-threaded verification test"""
        logger.info(f"Executing multi-threaded verification test, worker threads: {self.config.concurrent_workers}...")
        
        times = []
        metrics_list = []
        success_count = 0
        
        test_credentials = credentials[:self.config.num_iterations]
        
        def verify_credential_task(credential):
            start_time = time.perf_counter()
            result, metrics = self.verifier.verify_credential(credential)
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, metrics, result.is_valid
        
        start_total = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.config.concurrent_workers) as executor:
            futures = [executor.submit(verify_credential_task, cred) for cred in test_credentials]
            
            for i, future in enumerate(as_completed(futures)):
                time_taken, metrics, is_valid = future.result()
                times.append(time_taken)
                metrics_list.append(metrics)
                
                if is_valid:
                    success_count += 1
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Completed {i + 1}/{len(test_credentials)} multi-threaded verifications")
        
        end_total = time.perf_counter()
        total_concurrent_time = (end_total - start_total) * 1000
        
        results = self._calculate_statistics(times, metrics_list, "multi_thread_verification")
        results["total_concurrent_time_ms"] = total_concurrent_time
        results["throughput_per_second"] = len(test_credentials) / (total_concurrent_time / 1000)
        results["success_rate"] = success_count / len(test_credentials)
        
        return results
    
    def _test_batch_verification(self, credentials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch verification test"""
        logger.info("Executing batch verification test...")
        
        test_credentials = credentials[:self.config.num_credentials]
        
        start_time = time.perf_counter()
        results, metrics_list = self.verifier.batch_verify_credentials(test_credentials)
        end_time = time.perf_counter()
        
        total_time = (end_time - start_time) * 1000
        avg_time_per_credential = total_time / len(test_credentials)
        success_count = sum(1 for r in results if r.is_valid)
        
        individual_times = [m.total_verification_time_ms for m in metrics_list]
        
        return {
            "total_batch_time_ms": total_time,
            "avg_time_per_credential_ms": avg_time_per_credential,
            "credentials_per_second": len(test_credentials) / (total_time / 1000),
            "success_rate": success_count / len(test_credentials),
            "individual_times_ms": individual_times,
            "statistics": self._basic_statistics(individual_times)
        }
    
    def test_status_list_performance(self) -> Dict[str, Any]:
        """Test status list performance"""
        logger.info("Starting status list performance test...")
        
        # Create test status list
        test_list_id = "performance-test-list"
        status_list = self.status_manager.create_status_list(test_list_id, "revocation", 131072)
        
        # Single update performance test
        single_update_times = []
        for i in range(1000):
            update_time = status_list.update_status(i, "revoked", f"Test {i}")
            single_update_times.append(update_time)
        
        # Batch update performance test
        batch_updates = [(i, "suspended", f"Batch {i}") for i in range(1000, 11000)]
        batch_time = status_list.batch_update_status(batch_updates)
        
        # Query performance test
        query_times = []
        for i in range(1000):
            _, query_time = status_list.get_status(i)
            query_times.append(query_time)
        
        # Compression performance test
        start_compression = time.perf_counter()
        compressed_list, compression_ratio, compression_time = status_list.get_compressed_list()
        end_compression = time.perf_counter()
        
        # Production load test
        load_results = self.status_manager.simulate_production_load(test_list_id, 10000)
        
        results = {
            "single_update": {
                "times_ms": single_update_times,
                "statistics": self._basic_statistics(single_update_times)
            },
            "batch_update": {
                "total_time_ms": batch_time,
                "updates_count": len(batch_updates),
                "updates_per_second": len(batch_updates) / (batch_time / 1000)
            },
            "query": {
                "times_ms": query_times,
                "statistics": self._basic_statistics(query_times)
            },
            "compression": {
                "compression_time_ms": compression_time,
                "compression_ratio": compression_ratio,
                "compressed_size_bytes": len(compressed_list.encode('utf-8'))
            },
            "production_load": load_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Status list performance test completed")
        return results
    
    def _calculate_statistics(self, times: List[float], metrics_list: List[Any], test_type: str) -> Dict[str, Any]:
        """Calculate statistics"""
        stats = self._basic_statistics(times)
        
        # Add detailed performance metrics statistics
        if metrics_list:
            if hasattr(metrics_list[0], 'signing_metrics'):
                # Issuance metrics
                signing_times = [m.signing_metrics.total_processing_time_ms for m in metrics_list]
                credential_sizes = [m.signing_metrics.credential_size_bytes for m in metrics_list]
                
                stats.update({
                    "signing_time_statistics": self._basic_statistics(signing_times),
                    "credential_size_statistics": self._basic_statistics(credential_sizes)
                })
            
            elif hasattr(metrics_list[0], 'signature_verification_time_ms'):
                # Verification metrics
                sig_verify_times = [m.signature_verification_time_ms for m in metrics_list]
                status_check_times = [m.status_check_time_ms for m in metrics_list]
                
                stats.update({
                    "signature_verification_statistics": self._basic_statistics(sig_verify_times),
                    "status_check_statistics": self._basic_statistics(status_check_times)
                })
        
        return stats
    
    def _basic_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate basic statistics"""
        if not values:
            return {}
        
        return {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "p95": np.percentile(values, 95),
            "p99": np.percentile(values, 99),
            "count": len(values)
        }
    
    def run_comprehensive_test(self) -> PerformanceTestResults:
        """Run comprehensive performance test"""
        logger.info("Starting comprehensive performance test...")
        
        test_start_time = time.perf_counter()
        
        # 1. Issuance performance test
        logger.info("=" * 50)
        logger.info("Phase 1: Issuance Performance Test")
        logger.info("=" * 50)
        
        issuance_results = {}
        test_credentials = {}
        
        for cred_type in self.config.credential_types:
            if cred_type in self.credential_templates:
                issuance_result = self.test_issuance_performance(cred_type)
                issuance_results[cred_type] = issuance_result
                
                # Generate credentials for verification test
                templates = [self.credential_templates[cred_type].copy() 
                           for _ in range(min(self.config.num_credentials, 50))]
                credentials, _ = self.issuer.batch_issue_credentials(templates)
                test_credentials[cred_type] = credentials
        
        # 2. Verification performance test
        logger.info("=" * 50)
        logger.info("Phase 2: Verification Performance Test")
        logger.info("=" * 50)
        
        verification_results = {}
        for cred_type, credentials in test_credentials.items():
            verification_result = self.test_verification_performance(credentials)
            verification_results[cred_type] = verification_result
        
        # 3. Status list performance test
        logger.info("=" * 50)
        logger.info("Phase 3: Status List Performance Test")
        logger.info("=" * 50)
        
        status_list_results = self.test_status_list_performance()
        
        test_end_time = time.perf_counter()
        total_test_time = (test_end_time - test_start_time) * 1000
        
        # 4. Calculate summary statistics
        summary_stats = self._calculate_summary_statistics(
            issuance_results, verification_results, status_list_results
        )
        summary_stats["total_test_time_ms"] = total_test_time
        
        # Build test results
        test_results = PerformanceTestResults(
            test_name="RWA_VC_Comprehensive_Performance_Test",
            timestamp=datetime.now(timezone.utc).isoformat(),
            configuration=self.config,
            issuance_results=issuance_results,
            verification_results=verification_results,
            status_list_results=status_list_results,
            summary_statistics=summary_stats
        )
        
        logger.info(f"Comprehensive performance test completed, total time: {total_test_time/1000:.2f} seconds")
        return test_results
    
    def _calculate_summary_statistics(self, issuance_results: Dict, 
                                    verification_results: Dict, 
                                    status_results: Dict) -> Dict[str, Any]:
        """Calculate summary statistics"""
        summary = {}
        
        # Issuance summary
        if issuance_results:
            all_issuance_times = []
            for cred_type, results in issuance_results.items():
                if "single_thread" in results:
                    all_issuance_times.extend(
                        results["single_thread"].get("raw_times_ms", [])
                    )
            
            if all_issuance_times:
                summary["issuance_overall"] = self._basic_statistics(all_issuance_times)
        
        # Verification summary
        if verification_results:
            all_verification_times = []
            total_success_rate = 0
            count = 0
            
            for cred_type, results in verification_results.items():
                if "single_thread" in results:
                    all_verification_times.extend(
                        results["single_thread"].get("raw_times_ms", [])
                    )
                    total_success_rate += results["single_thread"].get("success_rate", 0)
                    count += 1
            
            if all_verification_times:
                summary["verification_overall"] = self._basic_statistics(all_verification_times)
                summary["overall_success_rate"] = total_success_rate / count if count > 0 else 0
        
        # Status list summary
        if status_results:
            summary["status_list_summary"] = {
                "query_performance": status_results.get("query", {}).get("statistics", {}),
                "update_performance": status_results.get("single_update", {}).get("statistics", {}),
                "production_load": status_results.get("production_load", {})
            }
        
        return summary
    
    def generate_performance_report(self, results: PerformanceTestResults) -> str:
        """Generate performance report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"rwa_vc_performance_report_{timestamp}.json"
        
        # Save detailed results
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(results), f, indent=2, ensure_ascii=False)
        
        # Generate Markdown report
        markdown_report = self._generate_markdown_report(results, timestamp)
        markdown_file = self.output_dir / f"rwa_vc_performance_report_{timestamp}.md"
        
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        logger.info(f"Performance report generated:")
        logger.info(f"  Detailed data: {report_file}")
        logger.info(f"  Markdown report: {markdown_file}")
        
        return str(markdown_file)
    
    def _generate_markdown_report(self, results: PerformanceTestResults, timestamp: str) -> str:
        """Generate Markdown report"""
        report = f"""# RWA VC Performance Test Report

## Test Summary

- **Test Time**: {results.timestamp}
- **Test Configuration**:
  - Credential Count: {results.configuration.num_credentials}
  - Iterations: {results.configuration.num_iterations}
  - Concurrent Workers: {results.configuration.concurrent_workers}
  - Credential Types: {', '.join(results.configuration.credential_types)}

## Key Performance Metrics

### Issuance Performance

"""
        
        # Add issuance performance details
        for cred_type, issuance_data in results.issuance_results.items():
            if "single_thread" in issuance_data:
                st_stats = issuance_data["single_thread"]
                report += f"""
#### {cred_type.upper()} Credential Issuance

- **Average Issuance Time**: {st_stats.get('mean', 0):.2f} ms
- **Median**: {st_stats.get('median', 0):.2f} ms
- **95th Percentile**: {st_stats.get('p95', 0):.2f} ms
- **Maximum Time**: {st_stats.get('max', 0):.2f} ms
- **Minimum Time**: {st_stats.get('min', 0):.2f} ms

"""
                
                if "multi_thread" in issuance_data:
                    mt_data = issuance_data["multi_thread"]
                    report += f"- **Multi-threaded Throughput**: {mt_data.get('throughput_per_second', 0):.1f} credentials/second\n\n"
        
        # Calculate and add issuance average results
        if results.issuance_results:
            all_issuance_means = []
            all_issuance_p95s = []
            all_issuance_throughputs = []
            
            for cred_type, issuance_data in results.issuance_results.items():
                if "single_thread" in issuance_data:
                    st_stats = issuance_data["single_thread"]
                    all_issuance_means.append(st_stats.get('mean', 0))
                    all_issuance_p95s.append(st_stats.get('p95', 0))
                    
                    if "multi_thread" in issuance_data:
                        mt_data = issuance_data["multi_thread"]
                        all_issuance_throughputs.append(mt_data.get('throughput_per_second', 0))
            
            if all_issuance_means:
                avg_mean = sum(all_issuance_means) / len(all_issuance_means)
                avg_p95 = sum(all_issuance_p95s) / len(all_issuance_p95s)
                
                report += f"""
#### Average Issuance Performance Across All Credential Types

- **Average Issuance Time**: {avg_mean:.2f} ms
- **Average P95 Time**: {avg_p95:.2f} ms
"""
                if all_issuance_throughputs:
                    avg_throughput = sum(all_issuance_throughputs) / len(all_issuance_throughputs)
                    report += f"- **Average Concurrent Throughput**: {avg_throughput:.1f} credentials/second\n\n"

        # Add verification performance details
        report += "### Verification Performance\n\n"
        
        for cred_type, verification_data in results.verification_results.items():
            if "single_thread" in verification_data:
                st_stats = verification_data["single_thread"]
                report += f"""
#### {cred_type.upper()} Credential Verification

- **Average Verification Time**: {st_stats.get('mean', 0):.2f} ms
- **Median**: {st_stats.get('median', 0):.2f} ms
- **95th Percentile**: {st_stats.get('p95', 0):.2f} ms
- **Verification Success Rate**: {st_stats.get('success_rate', 0)*100:.1f}%

"""
                
                if "multi_thread" in verification_data:
                    mt_data = verification_data["multi_thread"]
                    report += f"- **Multi-threaded Throughput**: {mt_data.get('throughput_per_second', 0):.1f} verifications/second\n\n"
        
        # Calculate and add verification average results
        if results.verification_results:
            all_verify_means = []
            all_verify_success_rates = []
            all_verify_throughputs = []
            
            for cred_type, verification_data in results.verification_results.items():
                if "single_thread" in verification_data:
                    st_stats = verification_data["single_thread"]
                    all_verify_means.append(st_stats.get('mean', 0))
                    all_verify_success_rates.append(st_stats.get('success_rate', 0))
                    
                    if "multi_thread" in verification_data:
                        mt_data = verification_data["multi_thread"]
                        all_verify_throughputs.append(mt_data.get('throughput_per_second', 0))
            
            if all_verify_means:
                avg_verify_mean = sum(all_verify_means) / len(all_verify_means)
                avg_success_rate = sum(all_verify_success_rates) / len(all_verify_success_rates)
                
                report += f"""
#### Average Verification Performance Across All Credential Types

- **Average Verification Time**: {avg_verify_mean:.2f} ms
- **Average Verification Success Rate**: {avg_success_rate*100:.1f}%
"""
                if all_verify_throughputs:
                    avg_verify_throughput = sum(all_verify_throughputs) / len(all_verify_throughputs)
                    report += f"- **Average Concurrent Throughput**: {avg_verify_throughput:.1f} verifications/second\n\n"
        
        # Add status list performance
        if results.status_list_results:
            report += "### Status List Performance\n\n"
            
            if "query" in results.status_list_results:
                query_stats = results.status_list_results["query"]["statistics"]
                report += f"""
#### Status Query Performance

- **Average Query Time**: {query_stats.get('mean', 0):.3f} ms
- **95th Percentile**: {query_stats.get('p95', 0):.3f} ms
- **Maximum Query Time**: {query_stats.get('max', 0):.3f} ms

"""
            
            if "production_load" in results.status_list_results:
                load_data = results.status_list_results["production_load"]
                report += f"""
#### Production Load Test

- **Update Throughput**: {load_data.get('updates_per_second', 0):.1f} updates/second
- **Query Throughput**: {load_data.get('queries_per_second', 0):.1f} queries/second

"""
        
        # Add summary
        if results.summary_statistics:
            report += "## Test Summary\n\n"
            
            total_time = results.summary_statistics.get("total_test_time_ms", 0)
            report += f"- **Total Test Time**: {total_time/1000:.1f} seconds\n"
            
            if "overall_success_rate" in results.summary_statistics:
                overall_rate = results.summary_statistics["overall_success_rate"]
                report += f"- **Overall Verification Success Rate**: {overall_rate*100:.1f}%\n"
        
        report += f"""
## Test Environment

- **Test Framework**: RWA VC Performance Test Suite
- **Report Generation Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Conclusion

This performance test validates the RWA VC system's performance in production environments. The test covers the complete process of credential issuance, verification, and status management, providing important data support for system optimization and capacity planning.

"""
        
        return report

def create_test_configuration(
    num_credentials: int = 100,
    num_iterations: int = 50,
    concurrent_workers: int = 4,
    credential_types: Optional[List[str]] = None,
    output_directory: str = "rwa_vc_test_results"
) -> TestConfiguration:
    """Create test configuration"""
    
    if credential_types is None:
        credential_types = ["vehicle", "realestate", "gold"]
    
    test_scenarios = [
        "single_thread_issuance",
        "multi_thread_issuance", 
        "batch_issuance",
        "single_thread_verification",
        "multi_thread_verification",
        "batch_verification",
        "status_list_performance"
    ]
    
    return TestConfiguration(
        num_credentials=num_credentials,
        num_iterations=num_iterations,
        concurrent_workers=concurrent_workers,
        credential_types=credential_types,
        test_scenarios=test_scenarios,
        output_directory=output_directory
    )

if __name__ == "__main__":
    # Create test configuration
    config = create_test_configuration(
        num_credentials=500,
        num_iterations=100,
        concurrent_workers=8,
        credential_types=['vehicle', 'realestate', 'gold', 'art', 'bond', 'fund', 'ip'],
        output_directory="rwa_vc_performance_results"
    )
    
    # Create performance tester
    tester = RWAVCPerformanceTester(config)
    
    # Run comprehensive test
    print("Starting RWA VC performance test...")
    results = tester.run_comprehensive_test()
    
    # Generate report
    report_file = tester.generate_performance_report(results)
    
    print(f"\nPerformance test completed!")
    print(f"Report generated: {report_file}")
    
    # Display key metrics
    if results.summary_statistics:
        if "issuance_overall" in results.summary_statistics:
            issuance_mean = results.summary_statistics["issuance_overall"].get("mean", 0)
            print(f"Average issuance time: {issuance_mean:.2f} ms")
        
        if "verification_overall" in results.summary_statistics:
            verification_mean = results.summary_statistics["verification_overall"].get("mean", 0)
            print(f"Average verification time: {verification_mean:.2f} ms")
        
        if "overall_success_rate" in results.summary_statistics:
            success_rate = results.summary_statistics["overall_success_rate"]
            print(f"Overall verification success rate: {success_rate*100:.1f}%")