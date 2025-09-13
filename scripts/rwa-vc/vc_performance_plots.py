import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

def draw_latency_comparison_combined(asset_types, issuance_mean, issuance_p95, verification_mean, verification_p95, file_name):
    """Draw combined issuance and verification latency comparison"""
    fig, ax = plt.subplots(figsize=(20, 18))
    width = 0.35
    x_pos = np.arange(len(asset_types))
    
    # Calculate error bars (P95 - mean)
    issuance_error = [p95 - mean for p95, mean in zip(issuance_p95, issuance_mean)]
    verification_error = [p95 - mean for p95, mean in zip(verification_p95, verification_mean)]
    
    bars1 = ax.bar(x_pos - width/2, issuance_mean, width, 
                   yerr=issuance_error,
                   capsize=6, 
                   color='#6C74AF', 
                   edgecolor='k', 
                   linewidth=1.5,
                   error_kw={'linewidth': 2, 'markeredgewidth': 2},
                   label='Issuance ± P95')
    
    bars2 = ax.bar(x_pos + width/2, verification_mean, width, 
                   yerr=verification_error,
                   capsize=6, 
                   color='#98B1D9', 
                   edgecolor='k', 
                   linewidth=1.5,
                   error_kw={'linewidth': 2, 'markeredgewidth': 2},
                   label='Verification ± P95')
    
    ax.set_xlabel('Asset Type', fontsize=70)
    ax.set_ylabel('Latency (ms)', fontsize=70)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(asset_types, fontsize=60, rotation=45, ha='right')
    ax.legend(loc='upper right', prop={'size': 50})
    ax.set_ylim(0, max(issuance_p95) * 1.4)
    
    # Add value labels on bars
    for i, (bar, mean) in enumerate(zip(bars1, issuance_mean)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + issuance_error[i] + 0.1,
                f'{mean:.2f}',
                ha='center', va='bottom', fontsize=28, fontweight='bold')
    
    for i, (bar, mean) in enumerate(zip(bars2, verification_mean)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + verification_error[i] + 0.1,
                f'{mean:.2f}',
                ha='center', va='bottom', fontsize=28, fontweight='bold')
    
    plt.tick_params(labelsize=60)
    fig.tight_layout()
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == '__main__':
    # Data extracted from performance report
    asset_types = ['Vehicle', 'RE', 'Gold', 'Art', 'Bond', 'Fund', 'IP']
    
    # Issuance data (in ms)
    issuance_mean = [8.22, 8.35, 7.82, 8.23, 8.08, 8.17, 8.21]
    issuance_p95 = [9.18, 9.14, 8.67, 8.99, 9.14, 9.11, 9.06]
    
    # Verification data (in ms) 
    verification_mean = [1.09, 0.81, 0.99, 0.85, 1.01, 1.02, 0.93]
    verification_p95 = [1.42, 1.13, 1.31, 1.31, 1.26, 1.24, 1.25]
    
    # Generate plots
    draw_latency_comparison_combined(asset_types, issuance_mean, issuance_p95, 
                                   verification_mean, verification_p95,
                                   "vc_issuance_verification_latency_combined.pdf")
