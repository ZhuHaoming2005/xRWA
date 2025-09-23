"""
Enhanced Blockchain SPV (Simplified Payment Verification) Algorithm Performance Analysis
This code demonstrates the logarithmic time complexity of SPV verification
as the Merkle tree height increases.
"""

import hashlib
import time
import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from typing import List, Tuple, Optional
import math

# Configure matplotlib for better font rendering
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

class MerkleTree:
    """
    Implementation of Merkle Tree for SPV verification
    """
    
    def __init__(self, transactions: List[str]):
        """
        Initialize Merkle Tree with list of transactions
        
        Args:
            transactions: List of transaction strings
        """
        self.transactions = transactions
        self.tree = []
        self.build_tree()
        
    def hash_data(self, data: str) -> str:
        """
        Hash function using SHA-256
        
        Args:
            data: Input string to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data.encode()).hexdigest()
    
    def build_tree(self):
        """
        Build the complete Merkle tree from transactions
        """
        if not self.transactions:
            return
            
        # Start with transaction hashes as leaf nodes
        current_level = [self.hash_data(tx) for tx in self.transactions]
        self.tree = [current_level[:]]  # Store leaf level
        
        # Build tree bottom-up
        while len(current_level) > 1:
            next_level = []
            
            # Process pairs of nodes
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    # Pair exists
                    combined = current_level[i] + current_level[i + 1]
                    next_level.append(self.hash_data(combined))
                else:
                    # Odd number of nodes, duplicate the last one
                    combined = current_level[i] + current_level[i]
                    next_level.append(self.hash_data(combined))
            
            current_level = next_level
            self.tree.append(current_level[:])
        
        # Root is the last level
        self.root = current_level[0] if current_level else None
    
    def get_merkle_proof(self, tx_index: int) -> List[Tuple[str, str]]:
        """
        Generate Merkle proof for SPV verification
        
        Args:
            tx_index: Index of transaction to prove
            
        Returns:
            List of (hash, position) tuples forming the proof path
            position is 'left' or 'right'
        """
        if tx_index >= len(self.transactions):
            raise ValueError("Transaction index out of range")
        
        proof = []
        current_index = tx_index
        
        # Traverse from leaf to root
        for level in range(len(self.tree) - 1):
            current_level = self.tree[level]
            
            # Find sibling node
            if current_index % 2 == 0:
                # Current node is left child
                if current_index + 1 < len(current_level):
                    sibling_hash = current_level[current_index + 1]
                    proof.append((sibling_hash, 'right'))
                else:
                    # No sibling (odd number of nodes)
                    sibling_hash = current_level[current_index]
                    proof.append((sibling_hash, 'right'))
            else:
                # Current node is right child
                sibling_hash = current_level[current_index - 1]
                proof.append((sibling_hash, 'left'))
            
            # Move to parent level
            current_index = current_index // 2
        
        return proof
    
    def verify_spv_proof(self, tx_hash: str, tx_index: int, proof: List[Tuple[str, str]]) -> bool:
        """
        Verify SPV proof for a transaction
        
        Args:
            tx_hash: Hash of the transaction to verify
            tx_index: Index of the transaction
            proof: Merkle proof path
            
        Returns:
            True if proof is valid, False otherwise
        """
        current_hash = tx_hash
        
        # Reconstruct path to root using proof
        for sibling_hash, position in proof:
            if position == 'left':
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            
            current_hash = self.hash_data(combined)
        
        # Check if computed root matches actual root
        return current_hash == self.root
    
    def get_tree_height(self) -> int:
        """
        Get the height of the Merkle tree
        
        Returns:
            Height of the tree (number of levels)
        """
        return len(self.tree)

class SPVPerformanceAnalyzer:
    """
    Analyzer for measuring SPV verification performance
    """
    
    def __init__(self):
        self.results = []
    
    def generate_test_transactions(self, count: int) -> List[str]:
        """
        Generate random test transactions
        
        Args:
            count: Number of transactions to generate
            
        Returns:
            List of transaction strings
        """
        transactions = []
        for i in range(count):
            # Generate random transaction data
            tx_data = f"tx_{i}_{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=20))}"
            transactions.append(tx_data)
        return transactions
    
    def measure_verification_time(self, tree: MerkleTree, num_verifications: int = 100000, 
                                  warmup_iterations: int = 100) -> Tuple[float, float]:
        """
        Measure average SPV verification time with multiple runs for stability
        
        Args:
            tree: Merkle tree to test
            num_verifications: Number of verification tests to run per measurement
            warmup_iterations: Number of warmup iterations to reduce timing variability
            
        Returns:
            Tuple of (average verification time in microseconds, standard deviation)
        """
        num_transactions = len(tree.transactions)
        
        # Warmup phase to reduce timing variability
        for _ in range(warmup_iterations):
            tx_index = random.randint(0, num_transactions - 1)
            tx_hash = tree.hash_data(tree.transactions[tx_index])
            proof = tree.get_merkle_proof(tx_index)
            tree.verify_spv_proof(tx_hash, tx_index, proof)
        
        # Main measurement with multiple runs
        run_times = []
        num_runs = 5  # Multiple runs for statistical stability
        
        for run in range(num_runs):
            total_time = 0
            
            for _ in range(num_verifications):
                # Random transaction to verify
                tx_index = random.randint(0, num_transactions - 1)
                tx_hash = tree.hash_data(tree.transactions[tx_index])
                
                # Measure verification time
                start_time = time.perf_counter()
                
                # Get proof and verify
                proof = tree.get_merkle_proof(tx_index)
                tree.verify_spv_proof(tx_hash, tx_index, proof)
                
                end_time = time.perf_counter()
                total_time += (end_time - start_time)
            
            # Average time for this run in microseconds
            run_avg_time = (total_time / num_verifications) * 1_000_000
            run_times.append(run_avg_time)
        
        # Calculate overall statistics
        avg_time = np.mean(run_times)
        std_time = np.std(run_times)
        
        return avg_time, std_time
    
    def run_performance_analysis(self, tree_sizes: List[int]) -> List[Tuple[int, int, float, float]]:
        """
        Run performance analysis for different tree sizes
        
        Args:
            tree_sizes: List of transaction counts to test
            
        Returns:
            List of (transaction_count, tree_height, avg_verification_time, std_deviation) tuples
        """
        results = []
        
        print("Running Enhanced SPV Performance Analysis...")
        print("=" * 60)
        print("Increased iterations and multiple runs for statistical stability")
        print("=" * 60)
        
        for size in tree_sizes:
            print(f"Testing with {size} transactions...")
            
            # Generate test data
            transactions = self.generate_test_transactions(size)
            
            # Build Merkle tree
            tree = MerkleTree(transactions)
            tree_height = tree.get_tree_height()
            
            # Measure verification time with statistics
            avg_time, std_time = self.measure_verification_time(tree)
            
            results.append((size, tree_height, avg_time, std_time))
            
            print(f"  Tree height: {tree_height}")
            print(f"  Average verification time: {avg_time:.3f} ± {std_time:.3f} microseconds")
            print(f"  Coefficient of variation: {(std_time/avg_time)*100:.2f}%")
            print()
        
        return results

def create_visualization(results: List[Tuple[int, int, float, float]], file_name: str = 'spv_performance_analysis.pdf'):
    """
    Create enhanced visualization of SPV performance analysis with error bars
    
    Args:
        results: Performance analysis results with standard deviations
        file_name: Output file name for the plot
    """
    # Extract data
    tx_counts = [r[0] for r in results]
    tree_heights = [r[1] for r in results]
    verification_times = [r[2] for r in results]
    std_deviations = [r[3] for r in results]
    
    # Create figure with subplots
    fig, (ax1) = plt.subplots(1, 1, figsize=(18, 12))
    
    # Plot 1: Verification Time vs Transaction Count (Log scale)
    ax1.errorbar(tx_counts, verification_times, yerr=std_deviations, 
                 fmt='bo-', linewidth=5, markersize=16, capsize=10, label='Measured Time ± Std Dev')
    
    # Log fit for transaction count
    log_tx = np.log2(tx_counts)
    log_coeffs = np.polyfit(log_tx, verification_times, 1)
    fitted_log = log_coeffs[0] * log_tx + log_coeffs[1]
    ax1.plot(tx_counts, fitted_log, 'g--', linewidth=3, 
             label=f'Log fit: y = {log_coeffs[0]:.2f}×log₂(n) + {log_coeffs[1]:.2f}')
    
    ax1.set_xscale('log', base=2)
    ax1.set_xlabel('Number of Transactions (n)', fontsize=60)
    ax1.set_ylabel('Verification Time ($\\mu$s)', fontsize=60)
    ax1.grid(True, alpha=0.3)
    ax1.legend(prop={'size': 35})
    plt.tick_params(labelsize=50)
    
    
    plt.tight_layout()
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.show()
    

def main():
    """
    Main function to run enhanced SPV performance analysis with increased iterations
    """
    # Test with different transaction counts (powers of 2 for clear logarithmic relationship)
    tree_sizes = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192]
    
    # Create analyzer
    analyzer = SPVPerformanceAnalyzer()
    
    # Run analysis
    results = analyzer.run_performance_analysis(tree_sizes)
    
    # Create visualization
    create_visualization(results, 'spv_performance_analysis.pdf')

if __name__ == "__main__":
    main()
