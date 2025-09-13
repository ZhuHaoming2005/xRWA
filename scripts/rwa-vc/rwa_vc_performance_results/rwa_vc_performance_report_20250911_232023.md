# RWA VC Performance Test Report

## Test Summary

- **Test Time**: 2025-09-11T15:20:23.626559+00:00
- **Test Configuration**:
  - Credential Count: 500
  - Iterations: 100
  - Concurrent Workers: 8
  - Credential Types: vehicle, realestate, gold, art, bond, fund, ip

## Key Performance Metrics

### Issuance Performance


#### VEHICLE Credential Issuance

- **Average Issuance Time**: 1.36 ms
- **Median**: 1.30 ms
- **95th Percentile**: 1.64 ms
- **Maximum Time**: 2.26 ms
- **Minimum Time**: 1.16 ms

- **Multi-threaded Throughput**: 634.7 credentials/second


#### REALESTATE Credential Issuance

- **Average Issuance Time**: 1.38 ms
- **Median**: 1.35 ms
- **95th Percentile**: 1.58 ms
- **Maximum Time**: 1.88 ms
- **Minimum Time**: 1.24 ms

- **Multi-threaded Throughput**: 624.7 credentials/second


#### GOLD Credential Issuance

- **Average Issuance Time**: 7.32 ms
- **Median**: 7.54 ms
- **95th Percentile**: 8.60 ms
- **Maximum Time**: 9.00 ms
- **Minimum Time**: 3.82 ms

- **Multi-threaded Throughput**: 124.1 credentials/second


#### ART Credential Issuance

- **Average Issuance Time**: 7.23 ms
- **Median**: 7.51 ms
- **95th Percentile**: 8.51 ms
- **Maximum Time**: 9.61 ms
- **Minimum Time**: 3.89 ms

- **Multi-threaded Throughput**: 121.6 credentials/second


#### BOND Credential Issuance

- **Average Issuance Time**: 7.53 ms
- **Median**: 7.67 ms
- **95th Percentile**: 8.79 ms
- **Maximum Time**: 9.44 ms
- **Minimum Time**: 3.96 ms

- **Multi-threaded Throughput**: 127.2 credentials/second


#### FUND Credential Issuance

- **Average Issuance Time**: 7.54 ms
- **Median**: 7.60 ms
- **95th Percentile**: 8.81 ms
- **Maximum Time**: 10.06 ms
- **Minimum Time**: 3.66 ms

- **Multi-threaded Throughput**: 124.6 credentials/second


#### IP Credential Issuance

- **Average Issuance Time**: 7.53 ms
- **Median**: 7.58 ms
- **95th Percentile**: 8.86 ms
- **Maximum Time**: 9.54 ms
- **Minimum Time**: 4.82 ms

- **Multi-threaded Throughput**: 122.0 credentials/second


#### Average Issuance Performance Across All Credential Types

- **Average Issuance Time**: 5.70 ms
- **Average P95 Time**: 6.68 ms
- **Average Concurrent Throughput**: 268.4 credentials/second

### Verification Performance


#### VEHICLE Credential Verification

- **Average Verification Time**: 0.96 ms
- **Median**: 0.99 ms
- **95th Percentile**: 1.18 ms
- **Verification Success Rate**: 100.0%

- **Multi-threaded Throughput**: 940.5 verifications/second


#### REALESTATE Credential Verification

- **Average Verification Time**: 0.86 ms
- **Median**: 0.84 ms
- **95th Percentile**: 1.23 ms
- **Verification Success Rate**: 100.0%

- **Multi-threaded Throughput**: 770.8 verifications/second


#### GOLD Credential Verification

- **Average Verification Time**: 1.07 ms
- **Median**: 1.10 ms
- **95th Percentile**: 1.24 ms
- **Verification Success Rate**: 100.0%

- **Multi-threaded Throughput**: 969.3 verifications/second


#### ART Credential Verification

- **Average Verification Time**: 1.02 ms
- **Median**: 1.07 ms
- **95th Percentile**: 1.26 ms
- **Verification Success Rate**: 100.0%

- **Multi-threaded Throughput**: 826.4 verifications/second


#### BOND Credential Verification

- **Average Verification Time**: 1.18 ms
- **Median**: 1.18 ms
- **95th Percentile**: 1.30 ms
- **Verification Success Rate**: 100.0%

- **Multi-threaded Throughput**: 978.0 verifications/second


#### FUND Credential Verification

- **Average Verification Time**: 0.84 ms
- **Median**: 0.79 ms
- **95th Percentile**: 1.13 ms
- **Verification Success Rate**: 100.0%

- **Multi-threaded Throughput**: 921.0 verifications/second


#### IP Credential Verification

- **Average Verification Time**: 1.00 ms
- **Median**: 1.05 ms
- **95th Percentile**: 1.24 ms
- **Verification Success Rate**: 100.0%

- **Multi-threaded Throughput**: 758.2 verifications/second


#### Average Verification Performance Across All Credential Types

- **Average Verification Time**: 0.99 ms
- **Average Verification Success Rate**: 100.0%
- **Average Concurrent Throughput**: 880.6 verifications/second

### Status List Performance


#### Status Query Performance

- **Average Query Time**: 0.001 ms
- **95th Percentile**: 0.001 ms
- **Maximum Query Time**: 0.018 ms


#### Production Load Test

- **Update Throughput**: 123006.1 updates/second
- **Query Throughput**: 1305653.5 queries/second

## Test Summary

- **Total Test Time**: 33.7 seconds

## Test Environment

- **Test Framework**: RWA VC Performance Test Suite
- **Report Generation Time**: 2025-09-11 23:20:23

## Conclusion

This performance test validates the RWA VC system's performance in production environments. The test covers the complete process of credential issuance, verification, and status management, providing important data support for system optimization and capacity planning.

